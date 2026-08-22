"""O laço que faz a caixa funcionar sozinha: chega, lê, decide, age.

Uma trava importante mora aqui. No iCloud, um endereço de domínio próprio é
apelido: `claude@nspx.dev` cai na mesma caixa de `miguel@nspx.dev`, e a senha
de aplicativo abre a caixa inteira. Por isso o escopo padrão é `alias`: o
agente só olha mensagem endereçada a ele. Não é garantia criptográfica — é uma
trava no software, e ela fica registrada em cada varredura.
"""

import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from . import approval, brain, guardrails, mailer, memory, notify, reader
from .paths import HOME, ensure_home

SEEN_FILE = HOME / "processed.jsonl"
DEFAULT_WATCH = {
    # alias = só o que foi endereçado ao agente; all = a caixa toda
    "scope": "alias",
    "interval": 300,
    # abaixo disto, nem uma resposta pronta sai sozinha: vai para a fila
    "min_confidence": 0.75,
    "enabled": False,
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def settings(account: Dict[str, Any]) -> Dict[str, Any]:
    valores = dict(DEFAULT_WATCH)
    valores.update(account.get("watch") or {})
    return valores


def _seen_ids() -> set:
    if not SEEN_FILE.exists():
        return set()
    vistos = set()
    with SEEN_FILE.open(encoding="utf-8") as fh:
        for linha in fh:
            try:
                vistos.add(json.loads(linha).get("message_id"))
            except json.JSONDecodeError:
                continue
    vistos.discard(None)
    return vistos


def _record(entrada: Dict[str, Any]) -> Dict[str, Any]:
    ensure_home()
    entrada["ts"] = _now()
    with SEEN_FILE.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entrada, ensure_ascii=False) + "\n")
    try:
        SEEN_FILE.chmod(0o600)
    except OSError:
        pass
    return entrada


def processed(limit: Optional[int] = None) -> List[Dict[str, Any]]:
    if not SEEN_FILE.exists():
        return []
    itens = []
    with SEEN_FILE.open(encoding="utf-8") as fh:
        for linha in fh:
            try:
                itens.append(json.loads(linha))
            except json.JSONDecodeError:
                continue
    itens.reverse()
    return itens[:limit] if limit else itens


def _in_scope(msg: Dict[str, Any], account: Dict[str, Any], scope: str) -> bool:
    if scope == "all":
        return True
    endereco = account["address"].lower()
    campos = (msg.get("to") or "") + " " + (msg.get("cc") or "")
    return endereco in campos.lower()


def scan_once(account: Dict[str, Any], limit: int = 40,
              dry_run: bool = False) -> List[Dict[str, Any]]:
    """Uma passada: lê o que chegou, decide, e age. Devolve o que fez.

    A varredura NÃO se guia por "não lida". O dono abre a mensagem no celular
    e ela vira lida — e o agente nunca mais a veria. Quem diz o que já foi
    tratado é o registro em processed.jsonl, que é do agente e de mais ninguém.
    """
    opcoes = settings(account)
    vistos = _seen_ids()
    resultados = []

    mensagens = reader.inbox(account, limit=limit, unread_only=False)
    for resumo in mensagens:
        if resumo.get("message_id") in vistos:
            continue
        from .guardrails import endereco as _endereco
        if _endereco(resumo.get("from", "")) == _endereco(account["address"]):
            resultados.append(_record({
                "message_id": resumo.get("message_id"), "uid": resumo["uid"],
                "from": resumo["from"], "subject": resumo["subject"],
                "action": "ignore",
                "reason": "mensagem enviada pelo próprio agente",
            }))
            continue
        if not _in_scope(resumo, account, opcoes["scope"]):
            resultados.append(_record({
                "message_id": resumo.get("message_id"), "uid": resumo["uid"],
                "from": resumo["from"], "subject": resumo["subject"],
                "action": "out-of-scope",
                "reason": f"não é endereçada a {account['address']}",
            }))
            continue

        # o corpo só é lido depois do filtro de escopo, e sem marcar como lida:
        # o dono continua vendo como não lida no cliente dele
        completa = reader.read(account, resumo["uid"], mark_read=False)

        # a mensagem é examinada antes de chegar ao modelo: o que parece
        # instrução disfarçada nunca vira resposta automática
        suspeitas = guardrails.detectar_injecao(
            (completa.get("body") or "") + " " + (completa.get("subject") or ""))

        try:
            decisao = brain.decide(account, completa)
        except brain.BrainError as exc:
            resultados.append(_record({
                "message_id": resumo.get("message_id"), "uid": resumo["uid"],
                "from": resumo["from"], "subject": resumo["subject"],
                "action": "error", "reason": str(exc)[:300]}))
            continue

        if suspeitas:
            decisao = {**decisao, "action": "escalate",
                       "reason": ("Esta mensagem traz texto que tenta dar ordens ao agente. "
                                  "Não respondi nada. Trechos: " + " | ".join(suspeitas[:2])),
                       "injection": suspeitas,
                       # o que a IA teria feito fica registrado, para o dono ver
                       "blocked_action": decisao.get("action"),
                       "blocked_body": decisao.get("reply_body")}
        else:
            decisao, avisos = guardrails.conferir_decisao(decisao, completa, account)
            if avisos:
                decisao["injection"] = avisos

        for fato in (decisao.get("learned") or []) if not decisao.get("injection") else []:
            rotulo, valor = fato.get("label"), fato.get("value")
            if rotulo and valor:
                memory.remember(rotulo, valor, category=fato.get("category") or "outro",
                                source=f"e-mail de {resumo['from'][:60]}")

        entrada = {
            "message_id": resumo.get("message_id"), "uid": resumo["uid"],
            "from": resumo["from"], "subject": resumo["subject"],
            "action": decisao["action"], "reason": decisao.get("reason"),
            "confidence": decisao.get("confidence"), "backend": decisao.get("backend"),
            "learned": [f.get("label") for f in (decisao.get("learned") or [])],
            "injection": decisao.get("injection"),
            "blocked_action": decisao.get("blocked_action"),
        }
        if dry_run:
            entrada["dry_run"] = True
            resultados.append(entrada)
            continue

        if decisao["action"] == "reply":
            corpo = decisao.get("reply_body") or ""
            assunto = decisao.get("reply_subject") or f"Re: {completa['subject']}"
            baixa_confianca = float(decisao.get("confidence") or 0) < float(opcoes["min_confidence"])
            resultado = mailer.send(
                account, completa["from"], assunto, corpo,
                in_reply_to=completa.get("message_id"),
                agent="mailforai-watch",
                reason=(decisao.get("reason") or "") +
                       (" [confiança baixa: mandei para a fila]" if baixa_confianca else ""),
                # confiança baixa nunca sai sozinha, mesmo em modo automático
                _force_queue=baixa_confianca)
            entrada["result"] = resultado.get("status")
            entrada["request_id"] = resultado.get("id")
        elif decisao["action"] == "ask":
            pergunta = approval.ask(
                account["name"], decisao.get("question") or "?",
                context=decisao.get("question_context") or
                        f"Veio de {resumo['from']} — assunto: {resumo['subject']}",
                agent="mailforai-watch")
            notify.pending_question(pergunta)
            entrada["question_id"] = pergunta["id"]
        elif decisao["action"] == "escalate":
            titulo = (f"⚠︎ Mensagem suspeita de {resumo['from']}: {resumo['subject']}"
                      if decisao.get("injection")
                      else f"Olha esta mensagem de {resumo['from']}: {resumo['subject']}")
            pergunta = approval.ask(
                account["name"], titulo,
                context=(decisao.get("reason") or "") + "\n\n" + (completa.get("body") or "")[:1200],
                options=["eu cuido disso", "responda você"],
                agent="mailforai-watch")
            notify.pending_question(pergunta)
            entrada["question_id"] = pergunta["id"]

        resultados.append(_record(entrada))

    notify.refresh_waiting()
    return resultados


def run(account: Dict[str, Any], interval: Optional[int] = None,
        once: bool = False, dry_run: bool = False, log=print) -> None:
    espera = int(interval or settings(account)["interval"])
    silencios = 0
    while True:
        try:
            feitos = scan_once(account, dry_run=dry_run)
            if feitos:
                silencios = 0
                for item in feitos:
                    log(f"{_now()} [{item['action']}] {item['subject']} — {item['from'][:40]}")
            else:
                # varredura vazia é o caso comum; repetir a mesma linha a cada
                # ciclo enche o registro e esconde o que importa
                silencios += 1
                if silencios == 1 or silencios % 20 == 0:
                    log(f"{_now()} nada novo (varredura {silencios})")
        except Exception as exc:
            log(f"{_now()} erro na varredura: {exc}")
        if once:
            return
        time.sleep(espera)
