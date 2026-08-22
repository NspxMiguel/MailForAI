"""Quem lê o e-mail que chegou e decide o que fazer com ele.

O MailForAI não traz modelo próprio: ele conversa com um que já está na
máquina ou numa API. O padrão é o `claude` da linha de comando, porque quem
usa isto já o tem instalado e autenticado — nada de pedir mais uma chave.

A decisão volta estruturada, e é ela que o resto do programa obedece:

    reply      há resposta pronta; segue o modo da caixa (envia ou enfileira)
    ask        falta um dado do dono; abre uma pergunta e não responde nada
    ignore     nada a fazer (propaganda, aviso automático, confirmação)
    escalate   assunto que não é da alçada do agente; avisa o dono
"""

import json
import os
import re
import shutil
import subprocess
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from . import memory

ACTIONS = ("reply", "ask", "ignore", "escalate")
DEFAULT_BACKEND = "claude-cli"
TIMEOUT = 120


class BrainError(RuntimeError):
    pass


# ---------------------------------------------------------------- prompt


def build_prompt(account: Dict[str, Any], message: Dict[str, Any],
                 thread: Optional[List[Dict[str, Any]]] = None) -> str:
    from . import identity

    historico = ""
    if thread:
        historico = "\n\nMensagens anteriores desta conversa (mais antiga primeiro):\n" + "\n".join(
            f"--- de {m.get('from')} em {m.get('date')} ---\n{(m.get('body') or '')[:1500]}"
            for m in thread)

    return f"""Você é o assistente de e-mail de {account['identity'].get('owner_name') or 'o dono desta caixa'}.
Escreve a partir de {account['address']} e se apresenta assim: {identity.display_name(account)}.

O que você sabe sobre o dono (use isto em vez de perguntar de novo):
{memory.as_prompt()}

Chegou esta mensagem:
--- de: {message.get('from')}
--- para: {message.get('to')}
--- assunto: {message.get('subject')}
--- data: {message.get('date')}

{(message.get('body') or '')[:6000]}{historico}

Decida uma ação e responda SÓ com um objeto JSON, sem cercas de código:

{{
  "action": "reply" | "ask" | "ignore" | "escalate",
  "reason": "uma frase dizendo por quê",
  "confidence": 0.0 a 1.0,
  "reply_subject": "assunto da resposta, se action=reply",
  "reply_body": "texto da resposta, se action=reply",
  "question": "o que perguntar ao dono, se action=ask",
  "question_context": "o que você já sabe, se action=ask",
  "learned": [{{"label": "nome do dado", "value": "valor", "category": "conta|aparelho|compra|pessoal|preferência|outro"}}]
}}

Regras:
- "reply" só quando você consegue responder inteiro com o que sabe. Se falta um
  dado do dono (número de série, ID de conta, número de pedido), use "ask".
- "ignore" para propaganda, newsletter, aviso automático e confirmação que não
  pede nada. Não responda essas.
- "escalate" quando envolve dinheiro, dado bancário, cancelamento, jurídico, ou
  qualquer coisa que mude a vida do dono. Não responda: avise.
- Escreva a resposta no idioma da mensagem recebida.
- Não invente dado nenhum. Sem o dado, é "ask".
- Não assine: a assinatura é aplicada depois, automaticamente.
- Em "learned", coloque dados novos e reaproveitáveis sobre o dono que vieram
  nesta mensagem (número de protocolo, número de pedido). Nunca ponha senha,
  código de verificação ou token — isso não se guarda.
"""


# ---------------------------------------------------------------- backends


def _claude_cli(prompt: str, model: Optional[str] = None) -> str:
    binario = shutil.which("claude")
    if not binario:
        raise BrainError("o comando 'claude' não está instalado — "
                         "escolha outro cérebro com 'mailforai brain <backend>'")
    args = [binario, "-p", prompt]
    if model:
        args += ["--model", model]
    # Numa pasta com CLAUDE.md o CLI carrega as regras daquele projeto e
    # responde sobre ele, não sobre o e-mail: já devolveu relatório de teste no
    # lugar do JSON. O cérebro roda numa pasta vazia, sem contexto herdado.
    import tempfile
    with tempfile.TemporaryDirectory(prefix="mailforai-brain-") as neutro:
        proc = subprocess.run(args, capture_output=True, timeout=TIMEOUT, cwd=neutro)
        if proc.returncode != 0:
            raise BrainError(f"claude falhou: {proc.stderr.decode()[:400]}")
        return proc.stdout.decode()


def _http_json(url: str, payload: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
    dados = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=dados, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resposta:
            return json.loads(resposta.read().decode())
    except urllib.error.HTTPError as exc:
        raise BrainError(f"{url} devolveu {exc.code}: {exc.read()[:300].decode(errors='replace')}")
    except urllib.error.URLError as exc:
        raise BrainError(f"não consegui falar com {url}: {exc.reason}")


def _anthropic(prompt: str, model: Optional[str] = None) -> str:
    chave = _secret("ANTHROPIC_API_KEY")
    dados = _http_json(
        "https://api.anthropic.com/v1/messages",
        {"model": model or "claude-sonnet-5", "max_tokens": 2000,
         "messages": [{"role": "user", "content": prompt}]},
        {"content-type": "application/json", "x-api-key": chave,
         "anthropic-version": "2023-06-01"})
    return "".join(bloco.get("text", "") for bloco in dados.get("content", []))


def _groq(prompt: str, model: Optional[str] = None) -> str:
    chave = _secret("GROQ_API_KEY")
    dados = _http_json(
        "https://api.groq.com/openai/v1/chat/completions",
        {"model": model or "llama-3.3-70b-versatile", "max_tokens": 2000,
         "messages": [{"role": "user", "content": prompt}]},
        # o Groq recusa requisição sem User-Agent com 403
        {"content-type": "application/json", "authorization": f"Bearer {chave}",
         "user-agent": "MailForAI"})
    return dados["choices"][0]["message"]["content"]


def _gemini(prompt: str, model: Optional[str] = None) -> str:
    chave = _secret("GEMINI_API_KEY")
    nome = model or "gemini-2.0-flash"
    dados = _http_json(
        f"https://generativelanguage.googleapis.com/v1beta/models/{nome}:generateContent?key={chave}",
        {"contents": [{"parts": [{"text": prompt}]}]},
        {"content-type": "application/json"})
    partes = dados["candidates"][0]["content"]["parts"]
    return "".join(p.get("text", "") for p in partes)


BACKENDS = {
    "claude-cli": _claude_cli,
    "anthropic": _anthropic,
    "groq": _groq,
    "gemini": _gemini,
}


def _secret(nome: str) -> str:
    """Chave de API: ambiente primeiro, depois o chaveiro do sistema."""
    valor = os.environ.get(nome)
    if valor:
        return valor
    import platform
    if platform.system() == "Darwin" and shutil.which("security"):
        for servico in ("claude-autonomous", "mailforai"):
            proc = subprocess.run(
                ["security", "find-generic-password", "-s", servico, "-a", nome, "-w"],
                capture_output=True)
            if proc.returncode == 0:
                return proc.stdout.decode().strip()
    raise BrainError(f"{nome} não encontrada. Exporte a variável ou grave no chaveiro.")


# ---------------------------------------------------------------- decisão


def _extract_json(texto: str) -> Dict[str, Any]:
    """O modelo às vezes embrulha o JSON em prosa ou em cerca de código."""
    texto = texto.strip()
    cerca = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", texto, re.S)
    if cerca:
        texto = cerca.group(1)
    inicio, fim = texto.find("{"), texto.rfind("}")
    if inicio == -1 or fim <= inicio:
        raise BrainError(f"o modelo não devolveu JSON: {texto[:200]}")
    return json.loads(texto[inicio:fim + 1])


def decide(account: Dict[str, Any], message: Dict[str, Any],
           thread: Optional[List[Dict[str, Any]]] = None,
           backend: Optional[str] = None, model: Optional[str] = None) -> Dict[str, Any]:
    escolhido = backend or (account.get("brain") or {}).get("backend") or DEFAULT_BACKEND
    if escolhido not in BACKENDS:
        raise BrainError(f"cérebro '{escolhido}' não existe. Opções: {', '.join(BACKENDS)}")
    modelo = model or (account.get("brain") or {}).get("model")
    pedido = build_prompt(account, message, thread)
    try:
        decisao = _extract_json(BACKENDS[escolhido](pedido, modelo))
    except (BrainError, json.JSONDecodeError):
        # uma segunda tentativa, dizendo em letras maiores o que se espera:
        # modelo conversador às vezes explica antes de obedecer ao formato
        reforco = pedido + ("\n\nRESPONDA APENAS COM O OBJETO JSON. "
                            "Nada antes, nada depois, sem cercas de código.")
        decisao = _extract_json(BACKENDS[escolhido](reforco, modelo))

    if decisao.get("action") not in ACTIONS:
        raise BrainError(f"ação inválida: {decisao.get('action')}")
    try:
        decisao["confidence"] = float(decisao.get("confidence") or 0)
    except (TypeError, ValueError):
        decisao["confidence"] = 0.0
    decisao["backend"] = escolhido
    return decisao
