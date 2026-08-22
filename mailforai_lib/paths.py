"""Onde o MailForAI guarda config e histórico."""

import os
from pathlib import Path

HOME = Path(os.environ.get("MAILFORAI_HOME") or (Path.home() / ".mailforai"))
CONFIG_FILE = HOME / "config.json"
HISTORY_FILE = HOME / "history.jsonl"
ATTACH_DIR = HOME / "attachments"


def ensure_home() -> Path:
    HOME.mkdir(parents=True, exist_ok=True)
    # a config pode conter endereços e nomes de servidor: só o dono lê
    try:
        HOME.chmod(0o700)
    except OSError:
        pass
    return HOME
