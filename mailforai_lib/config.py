"""Leitura e escrita do ~/.mailforai/config.json."""

import json
from typing import Any, Dict, Optional

from . import providers
from .paths import CONFIG_FILE, ensure_home

DEFAULT_GUARD = {
    # lista vazia = pode escrever para qualquer um. Com itens, só o que casar.
    # aceita endereço exato ou domínio inteiro ("*@nspx.dev").
    "allowlist": [],
    # nunca escrever para estes, mesmo que a allowlist permita
    "blocklist": [],
    # teto de mensagens por janela de 24h — a trava contra loop de IA
    "daily_limit": 25,
    # anexos que a IA pode mandar, em MB
    "max_attachment_mb": 10,
}


class ConfigError(RuntimeError):
    pass


def load() -> Dict[str, Any]:
    if not CONFIG_FILE.exists():
        return {"accounts": {}, "default_account": None}
    with CONFIG_FILE.open(encoding="utf-8") as fh:
        return json.load(fh)


def save(cfg: Dict[str, Any]) -> None:
    ensure_home()
    tmp = CONFIG_FILE.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(cfg, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    tmp.replace(CONFIG_FILE)
    try:
        CONFIG_FILE.chmod(0o600)
    except OSError:
        pass


def get_account(name: Optional[str] = None) -> Dict[str, Any]:
    cfg = load()
    name = name or cfg.get("default_account")
    if not name:
        raise ConfigError("nenhuma conta configurada — rode 'mailforai setup'")
    if name not in cfg.get("accounts", {}):
        conhecidas = ", ".join(cfg.get("accounts", {})) or "nenhuma"
        raise ConfigError(f"conta '{name}' não existe (configuradas: {conhecidas})")
    account = dict(cfg["accounts"][name])
    account["name"] = name
    guard = dict(DEFAULT_GUARD)
    guard.update(account.get("guard") or {})
    account["guard"] = guard
    return account


def build_account(
    name: str,
    address: str,
    provider: str,
    username: Optional[str] = None,
    display_name: Optional[str] = None,
    smtp_host: Optional[str] = None,
    smtp_port: Optional[int] = None,
    imap_host: Optional[str] = None,
    imap_port: Optional[int] = None,
) -> Dict[str, Any]:
    preset = providers.PROVIDERS.get(provider)
    if preset is None:
        raise ConfigError(f"provedor '{provider}' desconhecido")
    smtp = dict(preset["smtp"])
    imap = dict(preset["imap"])
    if smtp_host:
        smtp["host"] = smtp_host
    if smtp_port:
        smtp["port"] = int(smtp_port)
    if imap_host:
        imap["host"] = imap_host
    if imap_port:
        imap["port"] = int(imap_port)
    if not smtp["host"]:
        raise ConfigError("o provedor 'custom' exige --smtp-host")
    return {
        "address": address,
        "display_name": display_name or name,
        "provider": provider,
        "username": username or address,
        "smtp": smtp,
        "imap": imap,
        "guard": dict(DEFAULT_GUARD),
    }


def add_account(name: str, account: Dict[str, Any], make_default: bool = True) -> None:
    cfg = load()
    cfg.setdefault("accounts", {})[name] = account
    if make_default or not cfg.get("default_account"):
        cfg["default_account"] = name
    save(cfg)
