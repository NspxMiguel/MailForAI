"""Leitura por IMAP: caixa de entrada e corpo de uma mensagem."""

import email
import email.message
import email.utils
import imaplib
import re
from email.header import decode_header, make_header
from typing import Any, Dict, List, Optional

from . import keyring

# o corpo que a IA lê é cortado para não estourar o contexto dela com
# assinatura, aviso legal e histórico de thread repetido
MAX_BODY_CHARS = 20000


class ReadError(RuntimeError):
    pass


def _decode(value: Optional[str]) -> str:
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except Exception:
        return value


def _connect(account: Dict[str, Any]) -> imaplib.IMAP4:
    imap_cfg = account.get("imap") or {}
    if not imap_cfg.get("host"):
        raise ReadError(f"a conta '{account['name']}' não tem IMAP configurado")
    password = keyring.get_secret(account["name"])
    try:
        if imap_cfg.get("ssl", True):
            conn = imaplib.IMAP4_SSL(imap_cfg["host"], imap_cfg.get("port", 993))
        else:
            conn = imaplib.IMAP4(imap_cfg["host"], imap_cfg.get("port", 143))
            # sem SSL, STARTTLS é o padrão certo — mas um servidor local de
            # teste não tem TLS nenhum, e exigir derrubava a conexão
            if imap_cfg.get("starttls", True):
                conn.starttls()
        conn.login(account.get("username") or account["address"], password)
    except imaplib.IMAP4.error as exc:
        raise ReadError(f"IMAP recusou a conexão: {exc}") from exc
    return conn


def _plain_body(msg: email.message.Message) -> str:
    """Prefere text/plain; cai para o HTML sem tags quando só há HTML."""
    html_fallback = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_disposition() == "attachment":
                continue
            ctype = part.get_content_type()
            if ctype == "text/plain":
                return _payload_text(part)
            if ctype == "text/html" and not html_fallback:
                html_fallback = _payload_text(part)
    else:
        if msg.get_content_type() == "text/html":
            html_fallback = _payload_text(msg)
        else:
            return _payload_text(msg)
    return re.sub(r"<[^>]+>", " ", html_fallback) if html_fallback else ""


def _payload_text(part: email.message.Message) -> str:
    payload = part.get_payload(decode=True)
    if payload is None:
        return ""
    charset = part.get_content_charset() or "utf-8"
    try:
        return payload.decode(charset, errors="replace")
    except LookupError:
        return payload.decode("utf-8", errors="replace")


def _summarize(uid: str, msg: email.message.Message, flags: str = "") -> Dict[str, Any]:
    date = _decode(msg.get("Date"))
    try:
        iso = email.utils.parsedate_to_datetime(date).isoformat()
    except (TypeError, ValueError):
        iso = date
    return {
        "uid": uid,
        "from": _decode(msg.get("From")),
        "to": _decode(msg.get("To")),
        "cc": _decode(msg.get("Cc")),
        "subject": _decode(msg.get("Subject")),
        "date": iso,
        "message_id": (msg.get("Message-ID") or "").strip(),
        "unread": "\\Seen" not in flags,
        "has_attachments": any(
            p.get_content_disposition() == "attachment" for p in msg.walk()
        ) if msg.is_multipart() else False,
    }


def inbox(account: Dict[str, Any], limit: int = 15, unread_only: bool = False,
          mailbox: str = "INBOX") -> List[Dict[str, Any]]:
    conn = _connect(account)
    try:
        conn.select(mailbox, readonly=True)
        criteria = "UNSEEN" if unread_only else "ALL"
        typ, data = conn.search(None, criteria)
        if typ != "OK":
            raise ReadError(f"busca IMAP falhou: {typ}")
        uids = data[0].split()[-limit:]
        out = []
        for uid in reversed(uids):
            # BODY.PEEK não marca como lida: listar não é ler
            typ, fetched = conn.fetch(uid, "(FLAGS BODY.PEEK[HEADER])")
            if typ != "OK" or not fetched or not isinstance(fetched[0], tuple):
                continue
            flags = fetched[0][0].decode(errors="replace")
            msg = email.message_from_bytes(fetched[0][1])
            out.append(_summarize(uid.decode(), msg, flags))
        return out
    finally:
        try:
            conn.logout()
        except Exception:
            pass


def read(account: Dict[str, Any], uid: str, mailbox: str = "INBOX",
         mark_read: bool = True) -> Dict[str, Any]:
    conn = _connect(account)
    try:
        conn.select(mailbox, readonly=not mark_read)
        typ, fetched = conn.fetch(str(uid).encode(), "(FLAGS BODY.PEEK[])")
        if typ != "OK" or not fetched or not isinstance(fetched[0], tuple):
            raise ReadError(f"mensagem {uid} não encontrada em {mailbox}")
        flags = fetched[0][0].decode(errors="replace")
        msg = email.message_from_bytes(fetched[0][1])
        summary = _summarize(str(uid), msg, flags)
        body = _plain_body(msg).strip()
        summary["truncated"] = len(body) > MAX_BODY_CHARS
        summary["body"] = body[:MAX_BODY_CHARS]
        summary["attachments"] = [
            p.get_filename() for p in msg.walk()
            if p.get_content_disposition() == "attachment"
        ] if msg.is_multipart() else []
        if mark_read:
            conn.store(str(uid).encode(), "+FLAGS", "\\Seen")
        return summary
    finally:
        try:
            conn.logout()
        except Exception:
            pass


def check(account: Dict[str, Any]) -> Dict[str, Any]:
    """Testa login SMTP e IMAP — o 'doctor' da conta."""
    import smtplib
    import ssl

    result = {"smtp": None, "imap": None}
    password = keyring.get_secret(account["name"])
    user = account.get("username") or account["address"]

    smtp_cfg = account["smtp"]
    try:
        context = ssl.create_default_context()
        if smtp_cfg.get("ssl"):
            server = smtplib.SMTP_SSL(smtp_cfg["host"], smtp_cfg["port"], context=context, timeout=20)
        else:
            server = smtplib.SMTP(smtp_cfg["host"], smtp_cfg["port"], timeout=20)
        with server:
            server.ehlo()
            if smtp_cfg.get("starttls"):
                server.starttls(context=context)
                server.ehlo()
            server.login(user, password)
        result["smtp"] = "ok"
    except Exception as exc:
        result["smtp"] = f"erro: {exc}"

    try:
        conn = _connect(account)
        conn.select("INBOX", readonly=True)
        conn.logout()
        result["imap"] = "ok"
    except Exception as exc:
        result["imap"] = f"erro: {exc}"
    return result
