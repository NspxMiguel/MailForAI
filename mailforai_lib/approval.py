"""Fila de aprovação: o que a IA quer mandar e o que ela precisa saber.

Dois modos por conta:

    auto     a IA envia na hora — a coleira do guard.py continua valendo
    confirm  a IA cria um pedido e nada sai até alguém aprovar

O arquivo é append-only, um evento por linha, e o estado de um pedido é a
última linha que fala dele. Aprovação é decisão que se audita depois: reescrever
a linha original apagaria quem decidiu o quê e quando.

Perguntas moram na mesma ideia. Suporte pede número de série, a IA não inventa:
abre uma pergunta, o dono responde, e a resposta volta para a IA na próxima vez
que ela olhar.
"""

import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .paths import HOME, ensure_home

OUTBOX_FILE = HOME / "outbox.jsonl"
QUESTIONS_FILE = HOME / "questions.jsonl"

MODES = ("auto", "confirm")
DEFAULT_APPROVAL = {"mode": "confirm"}


class ApprovalError(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _append(path, entry: Dict[str, Any]) -> Dict[str, Any]:
    ensure_home()
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return entry


def _collapse(path) -> List[Dict[str, Any]]:
    """Reduz o log de eventos ao estado atual de cada id, mais novo primeiro."""
    if not path.exists():
        return []
    por_id: Dict[str, Dict[str, Any]] = {}
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                evento = json.loads(line)
            except json.JSONDecodeError:
                continue
            anterior = por_id.get(evento.get("id"))
            if anterior:
                anterior.update(evento)
            else:
                por_id[evento["id"]] = evento
    itens = list(por_id.values())
    itens.sort(key=lambda e: e.get("epoch") or 0, reverse=True)
    return itens


def mode(account: Dict[str, Any]) -> str:
    escolhido = (account.get("approval") or {}).get("mode") or DEFAULT_APPROVAL["mode"]
    return escolhido if escolhido in MODES else "confirm"


# ---------------------------------------------------------------- envios


def queue_send(account: Dict[str, Any], to: List[str], subject: str, body: str,
               cc: Optional[List[str]] = None, bcc: Optional[List[str]] = None,
               attachments: Optional[List[str]] = None, in_reply_to: Optional[str] = None,
               agent: Optional[str] = None, reason: Optional[str] = None) -> Dict[str, Any]:
    pedido = {
        "id": uuid.uuid4().hex[:8],
        "kind": "send",
        "created": _now(),
        "epoch": time.time(),
        "account": account["name"],
        "status": "pending",
        "to": to, "cc": cc or [], "bcc": bcc or [],
        "subject": subject, "body": body,
        "attachments": attachments or [],
        "in_reply_to": in_reply_to,
        "agent": agent or "unknown",
        # por que a IA quer mandar isso: é o que o dono lê antes de decidir
        "reason": reason or "",
        "decided_at": None, "decided_by": None, "note": None, "result": None,
    }
    return _append(OUTBOX_FILE, pedido)


def outbox(status: Optional[str] = None, account: Optional[str] = None,
           limit: Optional[int] = None) -> List[Dict[str, Any]]:
    itens = _collapse(OUTBOX_FILE)
    if status:
        itens = [i for i in itens if i.get("status") == status]
    if account:
        itens = [i for i in itens if i.get("account") == account]
    return itens[:limit] if limit else itens


def get_request(request_id: str) -> Dict[str, Any]:
    for item in _collapse(OUTBOX_FILE):
        if item["id"] == request_id or item["id"].startswith(request_id):
            return item
    raise ApprovalError(f"pedido '{request_id}' não existe")


def pending_count(account: Optional[str] = None) -> int:
    return len(outbox(status="pending", account=account))


def _decide(request_id: str, status: str, by: str, note: Optional[str] = None,
            result: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    pedido = get_request(request_id)
    if pedido["status"] != "pending" and status in ("approved", "rejected"):
        raise ApprovalError(
            f"pedido {pedido['id']} já está '{pedido['status']}' — só pendente se decide")
    evento = {"id": pedido["id"], "status": status, "decided_at": _now(),
              "decided_by": by, "note": note, "epoch": pedido.get("epoch")}
    if result is not None:
        evento["result"] = result
    _append(OUTBOX_FILE, evento)
    pedido.update(evento)
    return pedido


def approve(request_id: str, by: str = "dono", edits: Optional[Dict[str, Any]] = None,
            send_now: bool = True) -> Dict[str, Any]:
    """Aprova e (por padrão) envia na hora. `edits` corrige o texto antes de sair."""
    from . import mailer

    pedido = get_request(request_id)
    if pedido["status"] != "pending":
        raise ApprovalError(f"pedido {pedido['id']} já está '{pedido['status']}'")
    if edits:
        permitido = {"to", "cc", "bcc", "subject", "body"}
        mudanca = {k: v for k, v in edits.items() if k in permitido and v is not None}
        if mudanca:
            mudanca["id"] = pedido["id"]
            mudanca["edited_at"] = _now()
            _append(OUTBOX_FILE, mudanca)
            pedido.update(mudanca)
    if not send_now:
        return _decide(request_id, "approved", by)

    from . import config
    account = config.get_account(pedido["account"])
    try:
        resultado = mailer.send(
            account, pedido["to"], pedido["subject"], pedido["body"],
            cc=pedido.get("cc"), bcc=pedido.get("bcc"),
            attachments=pedido.get("attachments"), in_reply_to=pedido.get("in_reply_to"),
            agent=pedido.get("agent"), _skip_queue=True,
        )
    except Exception as exc:
        return _decide(request_id, "failed", by, note=str(exc))
    return _decide(request_id, "sent", by, result=resultado)


def reject(request_id: str, by: str = "dono", note: Optional[str] = None) -> Dict[str, Any]:
    return _decide(request_id, "rejected", by, note=note)


# ---------------------------------------------------------------- perguntas


def ask(account_name: str, question: str, context: str = "", options: Optional[List[str]] = None,
        agent: Optional[str] = None, request_id: Optional[str] = None) -> Dict[str, Any]:
    pergunta = {
        "id": uuid.uuid4().hex[:8],
        "created": _now(),
        "epoch": time.time(),
        "account": account_name,
        "status": "open",
        "question": question,
        # o que a IA já sabe, para o dono não ter que reconstruir a conversa
        "context": context,
        "options": options or [],
        "agent": agent or "unknown",
        # a pergunta pode nascer de um envio parado na fila
        "request_id": request_id,
        "answer": None, "answered_at": None,
    }
    return _append(QUESTIONS_FILE, pergunta)


def questions(status: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    itens = _collapse(QUESTIONS_FILE)
    if status:
        itens = [i for i in itens if i.get("status") == status]
    return itens[:limit] if limit else itens


def get_question(question_id: str) -> Dict[str, Any]:
    for item in _collapse(QUESTIONS_FILE):
        if item["id"] == question_id or item["id"].startswith(question_id):
            return item
    raise ApprovalError(f"pergunta '{question_id}' não existe")


def answer(question_id: str, texto: str) -> Dict[str, Any]:
    pergunta = get_question(question_id)
    if pergunta["status"] != "open":
        raise ApprovalError(f"pergunta {pergunta['id']} já foi respondida")
    evento = {"id": pergunta["id"], "status": "answered", "answer": texto,
              "answered_at": _now(), "epoch": pergunta.get("epoch")}
    _append(QUESTIONS_FILE, evento)
    pergunta.update(evento)
    return pergunta


def dismiss_question(question_id: str) -> Dict[str, Any]:
    pergunta = get_question(question_id)
    _append(QUESTIONS_FILE, {"id": pergunta["id"], "status": "dismissed",
                             "answered_at": _now(), "epoch": pergunta.get("epoch")})
    pergunta["status"] = "dismissed"
    return pergunta


def waiting_count() -> Dict[str, int]:
    """O que está parado esperando o dono — o número que o app e o hook mostram."""
    return {"emails": pending_count(), "questions": len(questions(status="open"))}
