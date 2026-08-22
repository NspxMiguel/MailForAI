"""O que o agente aprende sobre o dono, para não perguntar duas vezes.

Suporte da Sony pede o número de série. Da próxima vez, o agente já sabe.
Cada fato guarda de onde veio e quando — informação de suporte envelhece, e
saber a origem é o que permite corrigir depois.

Um arquivo JSON, legível a olho nu: é memória sobre uma pessoa, ela tem que
poder abrir, ler e apagar sem ferramenta nenhuma.
"""

import json
import re
import unicodedata
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .paths import HOME, ensure_home

MEMORY_FILE = HOME / "memory.json"

# categorias soltas de propósito: servem para agrupar na tela, não para validar
CATEGORIES = ("conta", "aparelho", "compra", "pessoal", "preferência", "outro")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _slug(texto: str) -> str:
    # sem tirar o acento, "número de série" vira "n-mero-de-s-rie"
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    limpo = re.sub(r"[^a-z0-9]+", "-", sem_acento.lower()).strip("-")
    return limpo[:60] or "fato"


def load() -> Dict[str, Any]:
    if not MEMORY_FILE.exists():
        return {"facts": [], "notes": ""}
    try:
        dados = json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"facts": [], "notes": ""}
    dados.setdefault("facts", [])
    dados.setdefault("notes", "")
    return dados


def save(dados: Dict[str, Any]) -> None:
    ensure_home()
    tmp = MEMORY_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(MEMORY_FILE)
    try:
        MEMORY_FILE.chmod(0o600)
    except OSError:
        pass


def remember(label: str, value: str, category: str = "outro",
             source: str = "", sensitive: bool = False) -> Dict[str, Any]:
    """Grava um fato. Mesmo rótulo sobrescreve — dado de conta muda."""
    dados = load()
    chave = _slug(label)
    fato = {
        "key": chave,
        "label": label.strip(),
        "value": value.strip(),
        "category": category if category in CATEGORIES else "outro",
        # de onde veio: resposta do dono, e-mail recebido, digitado no app
        "source": source,
        # marcado à mão: o app avisa antes de mandar num e-mail
        "sensitive": sensitive,
        "updated": _now(),
        "epoch": time.time(),
    }
    dados["facts"] = [f for f in dados["facts"] if f.get("key") != chave] + [fato]
    save(dados)
    return fato


def forget(key: str) -> bool:
    dados = load()
    antes = len(dados["facts"])
    dados["facts"] = [f for f in dados["facts"] if f.get("key") != key and
                      not f.get("key", "").startswith(key)]
    save(dados)
    return len(dados["facts"]) < antes


def facts(category: Optional[str] = None) -> List[Dict[str, Any]]:
    itens = load()["facts"]
    if category:
        itens = [f for f in itens if f.get("category") == category]
    return sorted(itens, key=lambda f: f.get("epoch") or 0, reverse=True)


def set_notes(texto: str) -> None:
    dados = load()
    dados["notes"] = texto
    save(dados)


def as_prompt(include_sensitive: bool = True) -> str:
    """A memória como texto, do jeito que entra no pedido ao modelo."""
    dados = load()
    linhas = []
    for fato in sorted(dados["facts"], key=lambda f: f.get("category") or ""):
        if fato.get("sensitive") and not include_sensitive:
            continue
        linhas.append(f"- {fato['label']}: {fato['value']}"
                      + (f"  (fonte: {fato['source']})" if fato.get("source") else ""))
    bloco = "\n".join(linhas) if linhas else "(nada aprendido ainda)"
    if dados.get("notes"):
        bloco += f"\n\nObservações do dono:\n{dados['notes']}"
    return bloco


def learn_from_answer(pergunta: str, resposta: str) -> Optional[Dict[str, Any]]:
    """Transforma uma resposta do dono em fato.

    A pergunta vira o rótulo, limpa do que é conversa: "Qual é o seu Social
    Club ID?" vira "Social Club ID". Sem isso a memória fica cheia de frases
    interrogativas que não servem de chave.
    """
    resposta = (resposta or "").strip()
    if not resposta or resposta.startswith("("):
        return None
    rotulo = pergunta.strip().rstrip("?").strip()
    for prefixo in ("qual é o seu ", "qual é a sua ", "qual o seu ", "qual a sua ",
                    "qual é o ", "qual é a ", "me diz o ", "me diz a ",
                    "what is your ", "what's your ", "what is the "):
        if rotulo.lower().startswith(prefixo):
            rotulo = rotulo[len(prefixo):]
            break
    rotulo = rotulo[:1].upper() + rotulo[1:] if rotulo else pergunta
    # respostas longas são texto de conversa, não um dado para reusar
    if len(resposta) > 200:
        return None
    return remember(rotulo, resposta, source="resposta do dono")
