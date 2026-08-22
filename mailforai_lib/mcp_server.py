"""Servidor MCP (stdio) — o jeito de qualquer IA plugar a caixa.

JSON-RPC 2.0, uma mensagem por linha, stdin/stdout. Sem dependência: o
protocolo é simples o bastante para caber na stdlib, e assim o servidor roda
em qualquer máquina que tenha python3.
"""

import json
import sys
import traceback
from typing import Any, Dict

from . import __version__, config, guard, history, keyring, mailer, reader

PROTOCOL_VERSION = "2025-06-18"

TOOLS = [
    {
        "name": "send_email",
        "description": (
            "Envia um e-mail a partir da caixa da IA. Respeita a allowlist e o teto "
            "diário configurados pelo dono; um envio recusado devolve o motivo e "
            "fica registrado no histórico."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "destinatários, separados por vírgula"},
                "subject": {"type": "string"},
                "body": {"type": "string", "description": "texto puro"},
                "cc": {"type": "string"},
                "attachments": {"type": "array", "items": {"type": "string"},
                                "description": "caminhos de arquivo locais"},
                "account": {"type": "string", "description": "conta a usar; omita para a padrão"},
            },
            "required": ["to", "subject", "body"],
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
        return {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": TOOLS}}
    if method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments") or {}
        try:
            text = _call_tool(name, arguments)
            is_error = False
        except (guard.GuardError, mailer.SendError, reader.ReadError,
                keyring.KeyringError, config.ConfigError) as exc:
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


def run() -> None:
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
