"""Servidor MCP (stdio) — o jeito de qualquer IA plugar a caixa.

JSON-RPC 2.0, uma mensagem por linha, stdin/stdout. Sem dependência: o
protocolo é simples o bastante para caber na stdlib, e assim o servidor roda
em qualquer máquina que tenha python3.
"""

import json
import sys
import traceback
from typing import Any, Dict

from . import (__version__, approval, config, guard, history, identity, keyring,
               mailer, notify, reader)

PROTOCOL_VERSION = "2025-06-18"

TOOLS = [
    {
        "name": "send_email",
        "description": (
            "Envia um e-mail a partir da caixa da IA. Respeita a allowlist e o teto "
            "diário configurados pelo dono; um envio recusado devolve o motivo e "
            "fica registrado no histórico. O remetente e a assinatura são aplicados "
            "pela identidade da caixa — não escreva assinatura no corpo, e consulte "
            "mailbox_info antes de se apresentar no texto."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "destinatários, separados por vírgula"},
                "subject": {"type": "string"},
                "body": {"type": "string", "description": "texto puro"},
                "cc": {"type": "string"},
                "reason": {"type": "string",
                           "description": "por que esta mensagem precisa sair; o dono lê "
                                          "isto antes de aprovar, quando a caixa exige "
                                          "aprovação"},
                "attachments": {"type": "array", "items": {"type": "string"},
                                "description": "caminhos de arquivo locais"},
                "account": {"type": "string", "description": "conta a usar; omita para a padrão"},
            },
            "required": ["to", "subject", "body"],
        },
    },
    {
        "name": "mailbox_info",
        "description": "Como esta caixa se apresenta e o que ela permite: endereço, "
                       "modo de identidade, assinatura aplicada, allowlist, teto diário "
                       "e quanto do teto já foi usado nas últimas 24h. Consulte antes de "
                       "escrever a primeira mensagem de uma conversa.",
        "inputSchema": {
            "type": "object",
            "properties": {"account": {"type": "string"}},
        },
    },
    {
        "name": "list_inbox",
        "description": "Lista as mensagens recebidas (remetente, assunto, data, UID). "
                       "Não marca nada como lido.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 15},
                "unread_only": {"type": "boolean", "default": False},
                "account": {"type": "string"},
            },
        },
    },
    {
        "name": "read_email",
        "description": "Lê o corpo de uma mensagem pelo UID que o list_inbox devolveu.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "uid": {"type": "string"},
                "account": {"type": "string"},
                "mark_read": {"type": "boolean", "default": True},
            },
            "required": ["uid"],
        },
    },
    {
        "name": "reply_email",
        "description": "Responde uma mensagem recebida, mantendo o cabeçalho de thread.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "uid": {"type": "string"},
                "body": {"type": "string"},
                "account": {"type": "string"},
            },
            "required": ["uid", "body"],
        },
    },
    {
        "name": "ask_owner",
        "description": (
            "Registra uma pergunta para o dono e devolve na hora — não espera. Use "
            "quando faltar um dado que só ele tem (número de série, ID de conta, "
            "número de pedido) em vez de inventar ou de mandar o e-mail incompleto. "
            "Ele é avisado, e a resposta aparece em check_answers."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "question": {"type": "string"},
                "context": {"type": "string",
                            "description": "o que você já sabe, para ele não reconstruir a conversa"},
                "options": {"type": "array", "items": {"type": "string"}},
                "request_id": {"type": "string",
                               "description": "id do envio parado que depende desta resposta"},
                "account": {"type": "string"},
            },
            "required": ["question"],
        },
    },
    {
        "name": "check_answers",
        "description": "Perguntas que você fez e o que o dono já respondeu. Consulte antes "
                       "de perguntar de novo e antes de retomar um envio que dependia de "
                       "uma resposta.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "only_answered": {"type": "boolean", "default": False},
                "limit": {"type": "integer", "default": 20},
            },
        },
    },
    {
        "name": "sent_history",
        "description": "O que já foi enviado desta caixa, incluindo falhas e envios "
                       "recusados pela política. Consulte antes de reenviar algo.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 20},
                "account": {"type": "string"},
            },
        },
    },
]


OWNER_TOOLS = [
    {
        "name": "list_pending",
        "description": "O que está parado esperando decisão do dono: e-mails na fila e "
                       "perguntas abertas. Mostre ao usuário e pergunte o que ele quer fazer.",
        "inputSchema": {"type": "object", "properties": {
            "limit": {"type": "integer", "default": 20}}},
    },
    {
        "name": "approve_email",
        "description": (
            "Aprova e envia um e-mail da fila. Só chame quando o usuário disser "
            "explicitamente que aprova aquele pedido — a decisão é dele, você só "
            "registra. Aceita correções de assunto, corpo e destinatário."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "subject": {"type": "string"},
                "body": {"type": "string"},
                "to": {"type": "string"},
            },
            "required": ["id"],
        },
    },
    {
        "name": "reject_email",
        "description": "Recusa um e-mail da fila. Só com a recusa explícita do usuário. "
                       "O motivo volta para quem pediu o envio.",
        "inputSchema": {
            "type": "object",
            "properties": {"id": {"type": "string"}, "note": {"type": "string"}},
            "required": ["id"],
        },
    },
    {
        "name": "answer_question",
        "description": "Grava a resposta do dono a uma pergunta da IA. Use o texto que "
                       "ele deu, sem completar o que ele não disse.",
        "inputSchema": {
            "type": "object",
            "properties": {"id": {"type": "string"}, "answer": {"type": "string"}},
            "required": ["id", "answer"],
        },
    },
]

# ligado por `mailforai mcp --owner`: quem liga isto aceita que a IA registre a
# decisão dele. O registro guarda que a decisão veio pelo chat, e não do app.
OWNER_MODE = False


def _account(params: Dict[str, Any]) -> Dict[str, Any]:
    return config.get_account(params.get("account"))


def _call_tool(name: str, params: Dict[str, Any]) -> str:
    if name == "send_email":
        account = _account(params)
        result = mailer.send(
            account, params["to"], params["subject"], params["body"],
            cc=params.get("cc"), attachments=params.get("attachments"),
            agent=params.get("_agent") or "mcp",
        )
        return json.dumps(result, ensure_ascii=False)
    if name == "mailbox_info":
        account = _account(params)
        guarda = account["guard"]
        return json.dumps({
            "address": account["address"],
            "from": f"{identity.display_name(account)} <{account['address']}>",
            "identity_mode": account["identity"]["mode"],
            "signature_applied": identity.signature(account),
            "announces_itself_as_automated": bool(identity.headers(account)),
            "allowlist": guarda.get("allowlist") or "qualquer destinatário",
            "blocklist": guarda.get("blocklist") or [],
            "daily_limit": guarda.get("daily_limit"),
            "sent_last_24h": len(history.sent_since(account["name"], hours=24)),
        }, ensure_ascii=False)
    if name == "list_inbox":
        account = _account(params)
        return json.dumps(reader.inbox(account, limit=int(params.get("limit", 15)),
                                       unread_only=bool(params.get("unread_only"))),
                          ensure_ascii=False)
    if name == "read_email":
        account = _account(params)
        return json.dumps(reader.read(account, params["uid"],
                                      mark_read=params.get("mark_read", True)),
                          ensure_ascii=False)
    if name == "reply_email":
        account = _account(params)
        original = reader.read(account, params["uid"], mark_read=False)
        import email.utils
        _, sender = email.utils.parseaddr(original["from"])
        subject = original["subject"]
        if not subject.lower().startswith("re:"):
            subject = f"Re: {subject}"
        result = mailer.send(account, sender, subject, params["body"],
                             in_reply_to=original["message_id"], agent="mcp")
        return json.dumps(result, ensure_ascii=False)
    if name == "ask_owner":
        account = _account(params)
        pergunta = approval.ask(account["name"], params["question"],
                                context=params.get("context", ""),
                                options=params.get("options"), agent="mcp",
                                request_id=params.get("request_id"))
        notify.pending_question(pergunta)
        return json.dumps({"id": pergunta["id"], "status": "open",
                           "message": "Pergunta registrada e o dono foi avisado. "
                                      "Consulte check_answers mais tarde."}, ensure_ascii=False)
    if name == "check_answers":
        itens = approval.questions(status="answered" if params.get("only_answered") else None,
                                   limit=int(params.get("limit", 20)))
        return json.dumps(itens, ensure_ascii=False)
    if name == "list_pending":
        return json.dumps({
            "emails": approval.outbox(status="pending", limit=int(params.get("limit", 20))),
            "questions": approval.questions(status="open"),
        }, ensure_ascii=False)
    if name == "approve_email":
        pedido = approval.approve(params["id"], by="chat",
                                  edits={k: params.get(k) for k in ("subject", "body", "to")})
        notify.refresh_waiting()
        return json.dumps(pedido, ensure_ascii=False)
    if name == "reject_email":
        pedido = approval.reject(params["id"], by="chat", note=params.get("note"))
        notify.refresh_waiting()
        return json.dumps(pedido, ensure_ascii=False)
    if name == "answer_question":
        pergunta = approval.answer(params["id"], params["answer"])
        notify.refresh_waiting()
        return json.dumps(pergunta, ensure_ascii=False)
    if name == "sent_history":
        account_name = params.get("account") or config.load().get("default_account")
        return json.dumps(history.read_all(account_name, limit=int(params.get("limit", 20))),
                          ensure_ascii=False)
    raise ValueError(f"ferramenta desconhecida: {name}")


def _handle(message: Dict[str, Any]) -> Dict[str, Any]:
    method = message.get("method")
    msg_id = message.get("id")
    params = message.get("params") or {}

    if method == "initialize":
        return {
            "jsonrpc": "2.0", "id": msg_id,
            "result": {
                "protocolVersion": params.get("protocolVersion") or PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "mailforai", "version": __version__},
            },
        }
    if method == "tools/list":
        ferramentas = TOOLS + (OWNER_TOOLS if OWNER_MODE else [])
        return {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": ferramentas}}
    if method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments") or {}
        try:
            text = _call_tool(name, arguments)
            is_error = False
        except (guard.GuardError, mailer.SendError, reader.ReadError,
                keyring.KeyringError, config.ConfigError, approval.ApprovalError) as exc:
            text, is_error = str(exc), True
        except Exception as exc:  # nunca derrubar a sessão da IA por um erro de ferramenta
            text, is_error = f"{type(exc).__name__}: {exc}", True
        return {"jsonrpc": "2.0", "id": msg_id,
                "result": {"content": [{"type": "text", "text": text}], "isError": is_error}}
    if method == "ping":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {}}
    if msg_id is None:
        return {}  # notificação: nada a responder
    return {"jsonrpc": "2.0", "id": msg_id,
            "error": {"code": -32601, "message": f"método não suportado: {method}"}}


def run(owner: bool = False) -> None:
    global OWNER_MODE
    OWNER_MODE = owner
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            continue
        try:
            response = _handle(message)
        except Exception:
            traceback.print_exc(file=sys.stderr)
            response = {"jsonrpc": "2.0", "id": message.get("id"),
                        "error": {"code": -32603, "message": "erro interno"}}
        if response:
            sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            sys.stdout.flush()
