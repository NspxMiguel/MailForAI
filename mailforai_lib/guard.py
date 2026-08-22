"""As travas entre a IA e a caixa de correio.

Uma IA com SMTP na mão pode errar de três jeitos caros: escrever para quem
não devia, escrever demais, e escrever de novo a mesma coisa em loop. Cada
regra aqui existe para um desses.
"""

from typing import Iterable, List

from .history import sent_since


class GuardError(RuntimeError):
    """Envio recusado por política — não é falha de rede nem de senha."""


def _matches(pattern: str, address: str) -> bool:
    pattern = pattern.strip().lower()
    address = address.strip().lower()
    if pattern.startswith("*@"):
        return address.endswith("@" + pattern[2:])
    if pattern.startswith("@"):
        return address.endswith(pattern)
    return pattern == address


def check_recipients(recipients: Iterable[str], guard: dict) -> None:
    allowlist: List[str] = guard.get("allowlist") or []
    blocklist: List[str] = guard.get("blocklist") or []
    for address in recipients:
        for pattern in blocklist:
            if _matches(pattern, address):
                raise GuardError(f"{address} está na blocklist da conta")
        if allowlist and not any(_matches(p, address) for p in allowlist):
            raise GuardError(
                f"{address} não está na allowlist da conta. "
                "Libere com 'mailforai allow <endereço-ou-*@dominio>'."
            )


def check_rate(account_name: str, guard: dict) -> None:
    limit = int(guard.get("daily_limit") or 0)
    if limit <= 0:
        return
    used = len(sent_since(account_name, hours=24))
    if used >= limit:
        raise GuardError(
            f"limite de {limit} mensagens em 24h já foi atingido "
            f"({used} enviadas). Ajuste com 'mailforai limit <n>'."
        )


def check_attachments(paths: Iterable[str], guard: dict) -> None:
    import os
    cap = float(guard.get("max_attachment_mb") or 0)
    if cap <= 0:
        return
    for path in paths:
        size_mb = os.path.getsize(path) / (1024 * 1024)
        if size_mb > cap:
            raise GuardError(
                f"anexo {os.path.basename(path)} tem {size_mb:.1f} MB, "
                f"acima do teto de {cap:g} MB da conta"
            )


def preflight(account: dict, recipients: Iterable[str], attachments: Iterable[str] = ()) -> None:
    guard = account["guard"]
    recipients = list(recipients)
    if not recipients:
        raise GuardError("nenhum destinatário")
    check_recipients(recipients, guard)
    check_rate(account["name"], guard)
    check_attachments(list(attachments), guard)
