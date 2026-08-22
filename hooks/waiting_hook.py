#!/usr/bin/env python3
"""Hook do Claude Code: lembra que tem e-mail parado esperando decisão.

Roda em toda sessão, em qualquer projeto — é o ponto. O dono pediu suporte
para um jogo às onze da noite, a IA escreveu o ticket, e três dias depois ele
lembra que nunca aprovou. Uma linha no começo de cada mensagem resolve isso.

Quando não há nada parado, não imprime nada: hook calado não gasta token.
"""

import json
import os
import sys
import time
from pathlib import Path

HOME = Path(os.environ.get("MAILFORAI_HOME") or (Path.home() / ".mailforai"))
WAITING = HOME / "waiting.json"
STATE = HOME / "hook-state.json"

# a linha curta sai em toda mensagem; o lembrete com os assuntos, de tempos em
# tempos, para não repetir o mesmo parágrafo a cada prompt
INTERVALO_DETALHE = 15 * 60


def ler_json(caminho, padrao):
    try:
        return json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return padrao


def detalhes():
    """Assunto e destinatário do que está parado, lidos direto da fila."""
    outbox = HOME / "outbox.jsonl"
    if not outbox.exists():
        return []
    por_id = {}
    try:
        with outbox.open(encoding="utf-8") as fh:
            for linha in fh:
                linha = linha.strip()
                if not linha:
                    continue
                try:
                    evento = json.loads(linha)
                except json.JSONDecodeError:
                    continue
                por_id.setdefault(evento["id"], {}).update(evento)
    except OSError:
        return []
    return [i for i in por_id.values() if i.get("status") == "pending"]


def main() -> int:
    # o payload do hook chega no stdin; nada aqui depende dele, mas deixar sem
    # ler faz o processo do outro lado tomar EPIPE ao escrever
    try:
        sys.stdin.read()
    except Exception:
        pass

    dados = ler_json(WAITING, {})
    emails = int(dados.get("emails") or 0)
    perguntas = int(dados.get("questions") or 0)
    if not emails and not perguntas:
        return 0

    partes = []
    if emails:
        partes.append(f"{emails} e-mail{'s' if emails > 1 else ''} esperando aprovação")
    if perguntas:
        partes.append(f"{perguntas} pergunta{'s' if perguntas > 1 else ''} aberta"
                      f"{'s' if perguntas > 1 else ''}")
    linha = f"[MailForAI] {' e '.join(partes)}."

    estado = ler_json(STATE, {})
    agora = time.time()
    if agora - float(estado.get("last_detail") or 0) > INTERVALO_DETALHE:
        pendentes = detalhes()[:3]
        if pendentes:
            linha += " Parados: " + "; ".join(
                f"{p.get('subject') or '(sem assunto)'} → {', '.join(p.get('to') or [])} [{p['id']}]"
                for p in pendentes)
        linha += (" Diga ao usuário e pergunte se ele aprova; use as ferramentas "
                  "list_pending/approve_email/reject_email do MailForAI, ou "
                  "'mailforai pending'. Nunca aprove sem ele dizer que aprova.")
        try:
            HOME.mkdir(parents=True, exist_ok=True)
            STATE.write_text(json.dumps({"last_detail": agora}), encoding="utf-8")
        except OSError:
            pass

    print(linha)
    return 0


if __name__ == "__main__":
    sys.exit(main())
