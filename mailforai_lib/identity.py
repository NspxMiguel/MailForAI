"""Como a IA se apresenta para quem recebe o e-mail.

Três posturas, porque as situações são de fato diferentes: pedir suporte
técnico, escrever em nome do dono, ou ser o dono. Quem escolhe é o dono da
caixa — é a identidade dele que está em jogo, não a minha.

    ia          "Sou o assistente de IA de Miguel." Diz o que é, sem rodeio.
    assistente  "Escrevo em nome de Miguel." Não esconde que não é o Miguel,
                não entra no mérito de ser software.
    dono        Assina como o próprio dono, sem menção a assistente.

O padrão é `ia`: é o único que não deixa dúvida do outro lado, e um padrão
que engana por omissão seria escolha minha, não dele.
"""

from typing import Any, Dict

from .i18n import T

MODES = ("ia", "assistente", "dono")

DEFAULT_IDENTITY = {
    "mode": "ia",
    # nome de quem é dono da caixa; entra na apresentação e na assinatura
    "owner_name": "",
    # como a IA se chama, quando o modo permite que ela tenha nome
    "agent_name": "",
    # assinatura fixa; vazio deixa o modo escrever a dele
    "signature": "",
}


def resolve(account: Dict[str, Any]) -> Dict[str, Any]:
    identity = dict(DEFAULT_IDENTITY)
    identity.update(account.get("identity") or {})
    if identity["mode"] not in MODES:
        identity["mode"] = "ia"
    if not identity["agent_name"]:
        identity["agent_name"] = account.get("display_name") or account["name"]
    return identity


def display_name(account: Dict[str, Any]) -> str:
    """O nome que aparece no campo De: do cliente de e-mail de quem recebe."""
    identity = resolve(account)
    dono = identity["owner_name"]
    agente = identity["agent_name"]
    if identity["mode"] == "dono":
        return dono or agente
    if identity["mode"] == "assistente":
        rotulo = T("assistente de ", "assistant to ")
        return f"{agente} · {rotulo}{dono}" if dono else f"{agente} · " + T("assistente", "assistant")
    return (f"{agente} (" + T("IA de ", "AI of ") + f"{dono})") if dono else f"{agente} (" + T("IA", "AI") + ")"


def signature(account: Dict[str, Any]) -> str:
    identity = resolve(account)
    if identity["signature"]:
        return identity["signature"]
    dono = identity["owner_name"]
    agente = identity["agent_name"]
    if identity["mode"] == "dono":
        return dono or ""
    if identity["mode"] == "assistente":
        return f"{agente}, " + T("assistente de ", "assistant to ") + dono if dono else agente
    linha = (f"{agente}, " + T("assistente de IA de ", "AI assistant to ") + dono) if dono else \
        f"{agente}, " + T("assistente de IA", "AI assistant")
    return linha + T("\nEsta mensagem foi escrita por um agente automatizado.",
                     "\nThis message was written by an automated agent.")


def sign(body: str, account: Dict[str, Any]) -> str:
    """Cola a assinatura no fim do corpo, se ainda não estiver lá."""
    assinatura = signature(account)
    if not assinatura or assinatura.split("\n")[0] in body:
        return body
    return f"{body.rstrip()}\n\n--\n{assinatura}\n"


def headers(account: Dict[str, Any]) -> Dict[str, str]:
    """Cabeçalhos que dizem, no protocolo, que do outro lado tem um agente.

    No modo `dono` eles saem: manter `Auto-Submitted` numa mensagem que se
    apresenta como pessoa seria dizer uma coisa no corpo e outra no cabeçalho.
    Fora isso eles ficam, e `Auto-Submitted` tem efeito prático — servidores
    usam esse cabeçalho para não responder automaticamente a robôs.
    """
    if resolve(account)["mode"] == "dono":
        return {}
    return {"X-Mailer": "MailForAI", "Auto-Submitted": "auto-generated"}
