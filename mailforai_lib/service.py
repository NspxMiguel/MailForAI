"""Roda o vigia como serviço do sistema, sem depender de app aberto.

Um assistente que só funciona enquanto a janela está aberta não é assistente.
No macOS isso é um LaunchAgent: sobe no login, o sistema reinicia se cair, e
segue trabalhando com a tela bloqueada.
"""

import os
import plistlib
import subprocess
from pathlib import Path
from typing import Any, Dict

ROTULO = "dev.nspx.mailforai.watch"
PLIST = Path.home() / "Library" / "LaunchAgents" / f"{ROTULO}.plist"
LOG_DIR = Path.home() / ".mailforai" / "logs"


# ~/Documents, ~/Desktop e ~/Downloads são protegidos pelo macOS: um serviço de
# background não consegue nem abrir arquivo lá dentro ("Operation not
# permitted"), e o vigia morre em laço sem explicar por quê.
PASTAS_PROTEGIDAS = ("/Documents/", "/Desktop/", "/Downloads/")


def _binario() -> str:
    """O binário que o serviço vai chamar, preferindo um que ele consiga abrir."""
    proprio = Path(__file__).resolve().parent.parent / "bin" / "mailforai"
    candidatos = [
        Path("/Applications/MailForAI.app/Contents/Resources/mailforai/bin/mailforai"),
        Path("/opt/homebrew/bin/mailforai"),
        Path("/usr/local/bin/mailforai"),
        proprio,
    ]
    for candidato in candidatos:
        if candidato.exists() and not protegido(str(candidato.resolve())):
            return str(candidato)
    return str(proprio)


def protegido(caminho: str) -> bool:
    return any(pasta in caminho for pasta in PASTAS_PROTEGIDAS)


def instalado() -> bool:
    return PLIST.exists()


def rodando() -> bool:
    proc = subprocess.run(["launchctl", "list"], capture_output=True)
    return ROTULO in proc.stdout.decode()


def status() -> Dict[str, Any]:
    binario = _binario()
    return {"installed": instalado(), "running": rodando(),
            "plist": str(PLIST), "log": str(LOG_DIR / "watch.log"),
            "binary": binario,
            "protected_path": protegido(str(Path(binario).resolve()))}


def instalar(intervalo: int = 300, conta: str = None) -> Dict[str, Any]:
    binario = _binario()
    if protegido(str(Path(binario).resolve())):
        return {"ok": False,
                "error": ("o único MailForAI encontrado está em uma pasta protegida pelo macOS "
                          f"({binario}); instale o app com "
                          "'brew install --cask nspxmiguel/tap/mailforai' para o serviço poder "
                          "rodar em segundo plano"),
                **status()}
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    PLIST.parent.mkdir(parents=True, exist_ok=True)

    argumentos = ["/usr/bin/python3", binario, "watch", "--interval", str(intervalo)]
    if conta:
        argumentos += ["--account", conta]

    conteudo = {
        "Label": ROTULO,
        "ProgramArguments": argumentos,
        "RunAtLoad": True,
        # o sistema reergue o processo se ele morrer — é isso que faz o "24h"
        "KeepAlive": True,
        "ThrottleInterval": 60,
        "StandardOutPath": str(LOG_DIR / "watch.log"),
        "StandardErrorPath": str(LOG_DIR / "watch.err"),
        "EnvironmentVariables": {
            # o serviço nasce com PATH mínimo, e o cérebro precisa achar o
            # comando `claude`; sem isto ele funciona no terminal e falha aqui
            "PATH": os.environ.get(
                "PATH", "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"),
            "HOME": str(Path.home()),
        },
    }
    if os.environ.get("MAILFORAI_HOME"):
        conteudo["EnvironmentVariables"]["MAILFORAI_HOME"] = os.environ["MAILFORAI_HOME"]

    with PLIST.open("wb") as fh:
        plistlib.dump(conteudo, fh)

    subprocess.run(["launchctl", "unload", str(PLIST)], capture_output=True)
    carga = subprocess.run(["launchctl", "load", str(PLIST)], capture_output=True)
    if carga.returncode != 0:
        return {"ok": False, "error": carga.stderr.decode()[:300], **status()}
    return {"ok": True, **status()}


def desinstalar() -> Dict[str, Any]:
    if PLIST.exists():
        subprocess.run(["launchctl", "unload", str(PLIST)], capture_output=True)
        PLIST.unlink()
    return {"ok": True, **status()}
