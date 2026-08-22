"""Histórico append-only do que a IA mandou.

Uma linha JSON por evento, nunca reescrita. É o registro que o dono da caixa
abre para saber o que foi enviado em nome dele — inclusive o que falhou e o
que a política recusou.
"""

import json
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from .paths import HISTORY_FILE, ensure_home


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def record(
    account: str,
    status: str,
    to: List[str],
    subject: str,
    body: str,
    cc: Optional[List[str]] = None,
    bcc: Optional[List[str]] = None,
    attachments: Optional[List[str]] = None,
    message_id: Optional[str] = None,
    in_reply_to: Optional[str] = None,
    error: Optional[str] = None,
    agent: Optional[str] = None,
) -> Dict[str, Any]:
    """Grava um evento de envio. status: sent | failed | blocked."""
    ensure_home()
    entry = {
        "id": uuid.uuid4().hex[:12],
        "ts": _now_iso(),
        "epoch": time.time(),
        "account": account,
        "direction": "outgoing",
        "status": status,
        "to": to,
        "cc": cc or [],
        "bcc": bcc or [],
        "subject": subject,
        "body": body,
        "attachments": [a.split("/")[-1] for a in (attachments or [])],
        "message_id": message_id,
        "in_reply_to": in_reply_to,
        "error": error,
        # quem pediu o envio: útil quando mais de uma IA usa a mesma caixa
        "agent": agent or "unknown",
    }
    with HISTORY_FILE.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    try:
        HISTORY_FILE.chmod(0o600)
    except OSError:
        pass
    return entry


def read_all(account: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    if not HISTORY_FILE.exists():
        return []
    entries = []
    with HISTORY_FILE.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue  # linha truncada não derruba a leitura do resto
            if account and entry.get("account") != account:
                continue
            entries.append(entry)
    entries.reverse()  # mais recente primeiro
    return entries[:limit] if limit else entries


def sent_since(account: str, hours: int = 24) -> List[Dict[str, Any]]:
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).timestamp()
    return [
        e for e in read_all(account)
        if e.get("status") == "sent" and float(e.get("epoch") or 0) >= cutoff
    ]


def stats(account: Optional[str] = None) -> Dict[str, Any]:
    entries = read_all(account)
    by_status: Dict[str, int] = {}
    for entry in entries:
        by_status[entry.get("status", "?")] = by_status.get(entry.get("status", "?"), 0) + 1
    return {
        "total": len(entries),
        "by_status": by_status,
        "last": entries[0]["ts"] if entries else None,
    }
