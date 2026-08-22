"""Avisa o dono que tem coisa parada esperando ele.

Três canais, e cada um cobre um jeito de esquecer: a notificação do sistema
para quem está no Mac, o app na barra de menus para quem olha a tela, e o
arquivo `waiting.json` — que o hook do Claude Code lê para encher o saco em
qualquer sessão, mesmo em outro projeto.
"""

import json
import platform
import shutil
import subprocess
from typing import Optional

from .paths import HOME, ensure_home

WAITING_FILE = HOME / "waiting.json"


def refresh_waiting() -> dict:
    """Reescreve o resumo do que está parado. Barato de ler, e sempre atual."""
    from . import approval
    ensure_home()
    dados = approval.waiting_count()
    dados["updated"] = approval._now()
    tmp = WAITING_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
    tmp.replace(WAITING_FILE)
    return dados


def read_waiting() -> dict:
    try:
        return json.loads(WAITING_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"emails": 0, "questions": 0}


def system(title: str, message: str, subtitle: Optional[str] = None) -> bool:
    """Notificação nativa. Falhar aqui não pode derrubar um envio."""
    try:
        if platform.system() == "Darwin":
            if shutil.which("terminal-notifier"):
                args = ["terminal-notifier", "-title", title, "-message", message,
                        "-sound", "Ping", "-group", "mailforai"]
                if subtitle:
                    args += ["-subtitle", subtitle]
                subprocess.run(args, capture_output=True, timeout=5)
                return True
            # osascript não aceita aspas soltas no texto: escapar antes de montar
            def esc(texto: str) -> str:
                return texto.replace("\\", "\\\\").replace('"', '\\"')
            script = (f'display notification "{esc(message)}" with title "{esc(title)}"'
                      + (f' subtitle "{esc(subtitle)}"' if subtitle else "")
                      + ' sound name "Ping"')
            subprocess.run(["osascript", "-e", script], capture_output=True, timeout=5)
            return True
        if shutil.which("notify-send"):
            subprocess.run(["notify-send", title, message], capture_output=True, timeout=5)
            return True
    except Exception:
        return False
    return False


def pending_email(pedido: dict) -> None:
    refresh_waiting()
    destinos = ", ".join(pedido.get("to") or [])
    system("MailForAI — e-mail esperando aprovação",
           f"{pedido.get('subject') or '(sem assunto)'} → {destinos}",
           subtitle=f"id {pedido['id']}")


def pending_question(pergunta: dict) -> None:
    refresh_waiting()
    system("MailForAI — a IA precisa de uma informação",
           pergunta.get("question") or "", subtitle=f"id {pergunta['id']}")
