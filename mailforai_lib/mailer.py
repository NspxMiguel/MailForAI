"""Envio por SMTP."""

import mimetypes
import os
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr, make_msgid
from typing import Any, Dict, List, Optional

from . import guard, history, identity, keyring


class SendError(RuntimeError):
    pass


def _split(value) -> List[str]:
    if not value:
        return []
    if isinstance(value, str):
        return [p.strip() for p in value.replace(";", ",").split(",") if p.strip()]
    return [str(p).strip() for p in value if str(p).strip()]


def build_message(
    account: Dict[str, Any],
    to: List[str],
    subject: str,
    body: str,
    cc: Optional[List[str]] = None,
    bcc: Optional[List[str]] = None,
    attachments: Optional[List[str]] = None,
    in_reply_to: Optional[str] = None,
    references: Optional[str] = None,
    html: Optional[str] = None,
) -> EmailMessage:
    msg = EmailMessage()
    # o nome no De: vem da identidade escolhida pelo dono, não do apelido da conta
    msg["From"] = formataddr((identity.display_name(account), account["address"]))
    msg["To"] = ", ".join(to)
    if cc:
        msg["Cc"] = ", ".join(cc)
    msg["Subject"] = subject
    msg["Message-ID"] = make_msgid(domain=account["address"].rsplit("@", 1)[-1])
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
        msg["References"] = references or in_reply_to
    for chave, valor in identity.headers(account).items():
        msg[chave] = valor
    msg.set_content(identity.sign(body, account))
    if html:
        msg.add_alternative(html, subtype="html")
    for path in attachments or []:
        ctype, encoding = mimetypes.guess_type(path)
        if ctype is None or encoding is not None:
            ctype = "application/octet-stream"
        maintype, subtype = ctype.split("/", 1)
        with open(path, "rb") as fh:
            msg.add_attachment(
                fh.read(), maintype=maintype, subtype=subtype,
                filename=os.path.basename(path),
            )
    return msg


def send(
    account: Dict[str, Any],
    to,
    subject: str,
    body: str,
    cc=None,
    bcc=None,
    attachments: Optional[List[str]] = None,
    in_reply_to: Optional[str] = None,
    references: Optional[str] = None,
    html: Optional[str] = None,
    agent: Optional[str] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Aplica a política, envia, e grava o resultado no histórico dos dois jeitos."""
    to, cc, bcc = _split(to), _split(cc), _split(bcc)
    attachments = attachments or []
    recipients = to + cc + bcc

    try:
        guard.preflight(account, recipients, attachments)
    except guard.GuardError as exc:
        history.record(account["name"], "blocked", to, subject, body,
                       cc=cc, bcc=bcc, attachments=attachments,
                       error=str(exc), agent=agent)
        raise

    msg = build_message(account, to, subject, body, cc, bcc, attachments,
                        in_reply_to, references, html)

    if dry_run:
        return {"status": "dry-run", "message_id": msg["Message-ID"],
                "to": to, "subject": subject, "bytes": len(bytes(msg))}

    smtp_cfg = account["smtp"]
    password = keyring.get_secret(account["name"])
    context = ssl.create_default_context()
    try:
        if smtp_cfg.get("ssl"):
            server = smtplib.SMTP_SSL(smtp_cfg["host"], smtp_cfg["port"],
                                      context=context, timeout=30)
        else:
            server = smtplib.SMTP(smtp_cfg["host"], smtp_cfg["port"], timeout=30)
        with server:
            server.ehlo()
            if smtp_cfg.get("starttls"):
                server.starttls(context=context)
                server.ehlo()
            server.login(account.get("username") or account["address"], password)
            server.send_message(msg, to_addrs=recipients)
    except smtplib.SMTPAuthenticationError as exc:
        error = (f"o servidor recusou a senha ({exc.smtp_code}). "
                 "Em iCloud, Gmail e Outlook o login precisa ser uma senha de "
                 "aplicativo, e o usuário costuma ser a conta principal, não o alias.")
        history.record(account["name"], "failed", to, subject, body, cc=cc, bcc=bcc,
                       attachments=attachments, error=error, agent=agent)
        raise SendError(error) from exc
    except Exception as exc:
        history.record(account["name"], "failed", to, subject, body, cc=cc, bcc=bcc,
                       attachments=attachments, error=str(exc), agent=agent)
        raise SendError(str(exc)) from exc

    entry = history.record(account["name"], "sent", to, subject, body, cc=cc, bcc=bcc,
                           attachments=attachments, message_id=msg["Message-ID"],
                           in_reply_to=in_reply_to, agent=agent)
    return {"status": "sent", "id": entry["id"], "message_id": msg["Message-ID"],
            "to": to, "subject": subject}
