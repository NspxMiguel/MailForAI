"""Descobre por que o login não passou — e conserta quando dá.

Errar aqui é a regra, não a exceção, e por dois motivos que se repetem em
todo provedor:

  1. o usuário do IMAP/SMTP não é o endereço que a pessoa quer usar. No iCloud
     é o Apple ID; num domínio próprio o alias nunca autentica;
  2. a senha de aplicativo é mostrada em blocos (`abcd-efgh-ijkl-mnop`) e cada
     provedor espera um formato — com hífen, sem hífen, sem espaço.

Em vez de mandar a pessoa adivinhar, testa-se a combinação e grava-se a que
funciona.
"""

import smtplib
import ssl
from typing import Any, Dict, List, Optional, Tuple

from . import config, keyring


def password_variants(senha: str) -> List[str]:
    """Formatos plausíveis da mesma senha, sem repetir."""
    bruta = senha.strip()
    candidatas = [bruta,
                  bruta.replace(" ", ""),
                  bruta.replace("-", ""),
                  bruta.replace(" ", "").replace("-", "")]
    vistas, saida = set(), []
    for item in candidatas:
        if item and item not in vistas:
            vistas.add(item)
            saida.append(item)
    return saida


def username_candidates(account: Dict[str, Any], extra: Optional[List[str]] = None) -> List[str]:
    candidatos = []
    for valor in ([account.get("username"), account.get("address")] + list(extra or [])):
        if valor and valor not in candidatos:
            candidatos.append(valor)
    return candidatos


def try_login(account: Dict[str, Any], username: str, password: str) -> Tuple[bool, str]:
    """Só o SMTP: é o mais rápido e recusa pelo mesmo motivo que o IMAP."""
    cfg = account["smtp"]
    contexto = ssl.create_default_context()
    try:
        if cfg.get("ssl"):
            servidor = smtplib.SMTP_SSL(cfg["host"], cfg["port"], context=contexto, timeout=20)
        else:
            servidor = smtplib.SMTP(cfg["host"], cfg["port"], timeout=20)
        with servidor:
            servidor.ehlo()
            if cfg.get("starttls"):
                servidor.starttls(context=contexto)
                servidor.ehlo()
            servidor.login(username, password)
        return True, "ok"
    except smtplib.SMTPAuthenticationError as exc:
        return False, f"{exc.smtp_code} {exc.smtp_error.decode(errors='replace')[:120]}"
    except Exception as exc:
        return False, str(exc)[:160]


def autofix(account: Dict[str, Any], extra_usernames: Optional[List[str]] = None,
            password: Optional[str] = None, save: bool = True) -> Dict[str, Any]:
    """Testa usuário × formato de senha e grava o par que autenticar."""
    senha = password or keyring.get_secret(account["name"])
    tentativas = []
    for usuario in username_candidates(account, extra_usernames):
        for variante in password_variants(senha):
            ok, detalhe = try_login(account, usuario, variante)
            tentativas.append({"username": usuario,
                               "password_format": _rotulo(senha, variante),
                               "ok": ok, "detail": detalhe})
            if ok:
                if save:
                    cfg = config.load()
                    cfg["accounts"][account["name"]]["username"] = usuario
                    config.save(cfg)
                    if variante != senha:
                        keyring.set_secret(account["name"], variante)
                return {"fixed": True, "username": usuario,
                        "password_format": _rotulo(senha, variante), "attempts": tentativas}
            # erro que não é de credencial (rede, DNS) não melhora tentando de novo
            if "Authentication" not in detalhe and "535" not in detalhe and "auth" not in detalhe.lower():
                return {"fixed": False, "attempts": tentativas, "stop_reason": detalhe}
    return {"fixed": False, "attempts": tentativas}


def _rotulo(original: str, usada: str) -> str:
    if usada == original.strip():
        return "como colada"
    if usada == original.replace(" ", ""):
        return "sem espaços"
    if usada == original.replace("-", ""):
        return "sem hífens"
    return "sem espaços nem hífens"
