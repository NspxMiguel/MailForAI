"""Linha de comando do MailForAI."""

import argparse
import getpass
import json
import sys
from pathlib import Path
from typing import Any, Dict

from . import (__version__, approval, config, crypto, guard, history, identity,
               keyring, mailer, notify, providers, reader)
from .i18n import T, language, set_language
from .paths import CONFIG_FILE, HISTORY_FILE, ensure_home


def _out(data: Any, as_json: bool) -> None:
    if as_json:
        print(json.dumps(data, ensure_ascii=False, indent=2))


def _fail(message: str) -> int:
    print(T("erro: ", "error: ") + message, file=sys.stderr)
    return 1


# ---------------------------------------------------------------- setup


def cmd_setup(args) -> int:
    ensure_home()
    print(T("MailForAI — configurar uma caixa para a IA usar\n", "MailForAI — set up a mailbox for the AI\n"))
    address = args.address or input("Endereço da IA (ex.: claude@seudominio.dev): ").strip()
    if "@" not in address:
        return _fail(T("isso não é um endereço de e-mail", "that is not an email address"))

    provider = args.provider
    if not provider:
        chute = providers.guess(address)
        print("\nProvedores:")
        for key, preset in providers.PROVIDERS.items():
            marca = " (chute pelo domínio)" if key == chute else ""
            print(f"  {key:9} {preset['label']}{marca}")
        provider = input(f"\nProvedor [{chute}]: ").strip() or chute
    if provider not in providers.PROVIDERS:
        return _fail(f"provedor '{provider}' desconhecido")

    preset = providers.PROVIDERS[provider]
    username = args.username
    if not username:
        print(f"\nUsuário de login — {preset['username_hint']}")
        username = input(f"Usuário [{address}]: ").strip() or address

    smtp_host = args.smtp_host
    imap_host = args.imap_host
    if provider == "custom" and not smtp_host:
        smtp_host = input("Host SMTP: ").strip()
        imap_host = input("Host IMAP: ").strip()

    name = args.name or address.split("@")[0]
    account = config.build_account(
        name=name, address=address, provider=provider, username=username,
        display_name=args.display_name, smtp_host=smtp_host, imap_host=imap_host,
    )
    print("\nComo a IA se apresenta para quem recebe:")
    print("  ia          diz que é um assistente de IA — o padrão, e o único sem ambiguidade")
    print("  assistente  escreve em nome do dono, sem entrar no mérito de ser software")
    print("  dono        assina como o próprio dono; quem recebe pensa estar falando com ele")
    modo = (args.identity or input("Modo [ia]: ").strip() or "ia")
    if modo not in identity.MODES:
        return _fail(f"modo '{modo}' não existe")
    dono = args.owner_name or input("Nome do dono da caixa (ex.: Miguel): ").strip()
    account["identity"] = dict(identity.DEFAULT_IDENTITY)
    account["identity"].update({"mode": modo, "owner_name": dono,
                                "agent_name": account["display_name"]})

    config.add_account(name, account)
    print(f"\nConta '{name}' gravada em {CONFIG_FILE}")
    completa = config.get_account(name)
    print(f"As mensagens sairão como: {identity.display_name(completa)} <{address}>")

    print(f"\nSenha — {preset['secret_hint']}")
    print("Ela vai para o chaveiro do sistema. Não fica em arquivo nenhum.")
    secret = getpass.getpass("Senha (não aparece na tela): ")
    if secret:
        backend = keyring.set_secret(name, secret)
        print(f"Senha guardada no {backend}.")
        print("\nTestando login...")
        return cmd_doctor(argparse.Namespace(account=name, json=False))
    print(f"\nSem senha ainda. Grave depois com: mailforai secret {name}")
    return 0


def cmd_secret(args) -> int:
    account = config.get_account(args.account)
    if args.stdin:
        # `pbpaste | mailforai secret conta --stdin` leva a senha da área de
        # transferência direto para o chaveiro, sem passar por tela nem histórico
        # de shell — é o caminho quando outra pessoa (ou um agente) está olhando.
        secret = sys.stdin.read().strip()
    else:
        secret = getpass.getpass(f"Senha da conta '{account['name']}' (não aparece na tela): ")
    if not secret:
        return _fail("senha vazia")
    backend = keyring.set_secret(account["name"], secret)
    print(f"guardada no {backend}")
    return 0


def cmd_accounts(args) -> int:
    cfg = config.load()
    accounts = cfg.get("accounts", {})
    if not accounts:
        print(T("nenhuma conta — rode 'mailforai setup'", "no mailbox yet — run 'mailforai setup'"))
        return 0
    if args.json:
        _out({"default": cfg.get("default_account"), "accounts": accounts}, True)
        return 0
    for name, account in accounts.items():
        marca = T(" (padrão)", " (default)") if name == cfg.get("default_account") else ""
        senha = T("senha ok", "password ok") if keyring.has_secret(name) else T("SEM SENHA", "NO PASSWORD")
        guarda = account.get("guard") or {}
        lista = guarda.get("allowlist") or []
        alvo = ", ".join(lista) if lista else T("qualquer destinatário", "anyone")
        print(f"{name}{marca}\n  {account['address']} via {account.get('provider')} — {senha}"
              f"\n  " + T("pode escrever para: ", "may write to: ") + alvo
              + f"\n  " + T("teto: ", "cap: ") + f"{guarda.get('daily_limit', '-')}"
              + T(" msgs/24h", " msgs/24h"))
    return 0


def cmd_doctor(args) -> int:
    account = config.get_account(args.account)
    try:
        result = reader.check(account)
    except keyring.KeyringError as exc:
        return _fail(str(exc))
    if args.json:
        _out(result, True)
    else:
        for protocolo in ("smtp", "imap"):
            print(f"{protocolo.upper():5} {result[protocolo]}")
    return 0 if result["smtp"] == "ok" and result["imap"] == "ok" else 1


# ---------------------------------------------------------------- enviar / ler


def cmd_send(args) -> int:
    account = config.get_account(args.account)
    body = args.body
    if body == "-" or (body is None and not sys.stdin.isatty()):
        body = sys.stdin.read()
    if not body:
        return _fail(T("corpo vazio — use --body ou mande pela entrada padrão",
                       "empty body — use --body or pipe it through stdin"))
    try:
        result = mailer.send(
            account, args.to, args.subject, body, cc=args.cc, bcc=args.bcc,
            attachments=args.attach, in_reply_to=args.in_reply_to,
            agent=args.agent, dry_run=args.dry_run, reason=args.reason,
        )
    except (guard.GuardError, mailer.SendError, keyring.KeyringError) as exc:
        return _fail(str(exc))
    if args.json:
        _out(result, True)
    elif result["status"] == "pending":
        print(T("na fila", "queued") + f" ({result['id']}): {result['subject']} → {', '.join(result['to'])}")
        print(T("nada sai até você aprovar — 'mailforai pending' mostra a fila",
                "nothing goes out until you approve — 'mailforai pending' shows the queue"))
    else:
        print(f"{result['status']}: {result['subject']} → {', '.join(result['to'])}")
    return 0


def cmd_inbox(args) -> int:
    account = config.get_account(args.account)
    try:
        messages = reader.inbox(account, limit=args.limit, unread_only=args.unread,
                                mailbox=args.mailbox)
    except (reader.ReadError, keyring.KeyringError) as exc:
        return _fail(str(exc))
    if args.json:
        _out(messages, True)
        return 0
    if not messages:
        print(T("caixa vazia", "empty inbox") if not args.unread else T("nada não lido", "nothing unread"))
    for msg in messages:
        marca = "●" if msg["unread"] else " "
        print(f"{marca} [{msg['uid']}] {msg['date'][:16]}  {msg['from'][:38]}\n    {msg['subject']}")
    return 0


def cmd_read(args) -> int:
    account = config.get_account(args.account)
    try:
        msg = reader.read(account, args.uid, mailbox=args.mailbox, mark_read=not args.keep_unread)
    except (reader.ReadError, keyring.KeyringError) as exc:
        return _fail(str(exc))
    if args.json:
        _out(msg, True)
        return 0
    print(f"De:      {msg['from']}\nPara:    {msg['to']}\nData:    {msg['date']}\n"
          f"Assunto: {msg['subject']}\n{'-' * 60}\n{msg['body']}")
    if msg.get("truncated"):
        print(f"\n[corpo cortado em {reader.MAX_BODY_CHARS} caracteres]")
    return 0


def cmd_reply(args) -> int:
    account = config.get_account(args.account)
    try:
        original = reader.read(account, args.uid, mailbox=args.mailbox, mark_read=False)
    except (reader.ReadError, keyring.KeyringError) as exc:
        return _fail(str(exc))
    body = args.body
    if body == "-" or (body is None and not sys.stdin.isatty()):
        body = sys.stdin.read()
    if not body:
        return _fail("corpo vazio")
    import email.utils
    _, sender = email.utils.parseaddr(original["from"])
    subject = original["subject"]
    if not subject.lower().startswith("re:"):
        subject = f"Re: {subject}"
    try:
        result = mailer.send(account, sender, subject, body,
                             in_reply_to=original["message_id"], agent=args.agent,
                             dry_run=args.dry_run)
    except (guard.GuardError, mailer.SendError) as exc:
        return _fail(str(exc))
    if args.json:
        _out(result, True)
    else:
        print(f"{result['status']}: resposta para {sender}")
    return 0


# ---------------------------------------------------------------- histórico


def cmd_history(args) -> int:
    account = None if args.all else (args.account or config.load().get("default_account"))
    entries = history.read_all(account=account, limit=args.limit)
    if args.json:
        _out(entries, True)
        return 0
    if not entries:
        print(T("nada enviado ainda", "nothing sent yet"))
    for entry in entries:
        simbolo = {"sent": "→", "failed": "✗", "blocked": "⊘"}.get(entry["status"], "?")
        print(f"{simbolo} {entry['ts'][:16]}  {', '.join(entry['to'])[:40]}"
              f"\n    {entry['subject']}  [{entry['agent']}]")
        if entry.get("error"):
            print(f"    {entry['error']}")
    return 0


def cmd_stats(args) -> int:
    data = history.stats(args.account)
    _out(data, True) if args.json else print(
        f"total {data['total']} — {data['by_status']} — último {data['last']}")
    return 0


def cmd_publish(args) -> int:
    from pathlib import Path
    entries = history.read_all(account=None if args.all else args.account)
    # o corpo inteiro pesa e não acrescenta na listagem: o site mostra um trecho
    for entry in entries:
        if len(entry.get("body") or "") > 4000:
            entry["body"] = entry["body"][:4000] + "\n[...]"
    payload = {"generated": history._now_iso(), "count": len(entries), "entries": entries}
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "history.enc.json"
    passphrase = args.passphrase or getpass.getpass("Senha para abrir o histórico no site: ")
    if not args.passphrase:
        if passphrase != getpass.getpass("Repita a senha: "):
            return _fail("as senhas não batem")
    try:
        target.write_text(crypto.encrypt_json(payload, passphrase), encoding="utf-8")
    except crypto.CryptoError as exc:
        return _fail(str(exc))
    print(f"{len(entries)} mensagens cifradas em {target}")
    print("O arquivo pode ir para um repositório público: sem a senha é ruído.")
    return 0


# ---------------------------------------------------------------- política


def _update_guard(account_name, mutate) -> int:
    cfg = config.load()
    name = account_name or cfg.get("default_account")
    if not name or name not in cfg.get("accounts", {}):
        return _fail(T("conta não encontrada", "mailbox not found"))
    account = cfg["accounts"][name]
    account.setdefault("guard", dict(config.DEFAULT_GUARD))
    mutate(account["guard"])
    config.save(cfg)
    print(json.dumps(account["guard"], ensure_ascii=False, indent=2))
    return 0


def cmd_allow(args) -> int:
    def mutate(g):
        lista = g.setdefault("allowlist", [])
        for pattern in args.pattern:
            if pattern not in lista:
                lista.append(pattern)
    return _update_guard(args.account, mutate)


def cmd_block(args) -> int:
    def mutate(g):
        lista = g.setdefault("blocklist", [])
        for pattern in args.pattern:
            if pattern not in lista:
                lista.append(pattern)
    return _update_guard(args.account, mutate)


def cmd_limit(args) -> int:
    return _update_guard(args.account, lambda g: g.__setitem__("daily_limit", args.n))


def cmd_identity(args) -> int:
    cfg = config.load()
    name = args.account or cfg.get("default_account")
    if not name or name not in cfg.get("accounts", {}):
        return _fail("conta não encontrada")
    conta = cfg["accounts"][name]
    ident = conta.setdefault("identity", dict(identity.DEFAULT_IDENTITY))
    mudou = False
    if args.mode:
        ident["mode"] = args.mode
        mudou = True
    for campo, valor in (("owner_name", args.owner_name), ("agent_name", args.agent_name),
                         ("signature", args.signature)):
        if valor is not None:
            ident[campo] = valor
            mudou = True
    if mudou:
        config.save(cfg)

    conta_completa = config.get_account(name)
    resumo = {
        "mode": ident["mode"],
        "from": f"{identity.display_name(conta_completa)} <{conta['address']}>",
        "signature": identity.signature(conta_completa),
        "headers": identity.headers(conta_completa),
    }
    if args.json:
        _out(resumo, True)
        return 0
    print(f"modo: {resumo['mode']}\n"
          f"De:   {resumo['from']}\n"
          f"assinatura:\n  " + resumo["signature"].replace("\n", "\n  "))
    print("cabeçalhos: " + (", ".join(f"{k}: {v}" for k, v in resumo["headers"].items())
                            or "nenhum — a mensagem não se anuncia como automática"))
    if resumo["mode"] == "dono":
        print("\naviso: neste modo quem recebe acredita estar falando com a pessoa.")
    return 0


def _mostrar_pedido(pedido: Dict[str, Any], completo: bool = False) -> None:
    print(f"[{pedido['id']}] {pedido['subject'] or '(sem assunto)'}")
    print(f"       para: {', '.join(pedido['to'])}")
    if pedido.get("cc"):
        print(f"       cc:   {', '.join(pedido['cc'])}")
    print(f"       quem: {pedido['agent']}   quando: {pedido['created'][:16]}")
    if pedido.get("reason"):
        print(f"       motivo: {pedido['reason']}")
    corpo = pedido.get("body") or ""
    if not completo and len(corpo) > 400:
        corpo = corpo[:400] + "\n       [...]"
    print("       " + corpo.replace("\n", "\n       "))


def cmd_pending(args) -> int:
    pedidos = approval.outbox(status=None if args.all else "pending",
                              account=None if args.all_accounts else args.account,
                              limit=args.limit)
    perguntas = approval.questions(status="open")
    if args.json:
        _out({"pending": pedidos, "questions": perguntas}, True)
        return 0
    if not pedidos and not perguntas:
        print(T("nada esperando você", "nothing waiting on you"))
        return 0
    for pedido in pedidos:
        marca = {"pending": "?", "sent": "→", "rejected": "⊘", "failed": "✗"}.get(pedido["status"], " ")
        print(f"{marca} ", end="")
        _mostrar_pedido(pedido, completo=args.full)
        print()
    if pedidos and any(p["status"] == "pending" for p in pedidos):
        print(T("aprovar: mailforai approve <id>    recusar: mailforai reject <id>",
                "approve: mailforai approve <id>    reject: mailforai reject <id>"))
    for pergunta in perguntas:
        print(f"\n? [{pergunta['id']}] {pergunta['question']}")
        if pergunta.get("context"):
            print(f"       contexto: {pergunta['context']}")
        if pergunta.get("options"):
            print(f"       opções: {', '.join(pergunta['options'])}")
        print(f"       responder: mailforai answer {pergunta['id']} \"...\"")
    return 0


def cmd_approve(args) -> int:
    edits = {"subject": args.subject, "body": args.body, "to": mailer._split(args.to) or None}
    try:
        pedido = approval.approve(args.id, by=args.by, edits=edits)
    except (approval.ApprovalError, config.ConfigError) as exc:
        return _fail(str(exc))
    notify.refresh_waiting()
    if args.json:
        _out(pedido, True)
        return 0
    if pedido["status"] == "sent":
        print(T("enviado: ", "sent: ") + f"{pedido['subject']} → {', '.join(pedido['to'])}")
    else:
        print(f"{pedido['status']}: {pedido.get('note') or ''}")
    return 0 if pedido["status"] == "sent" else 1


def cmd_reject(args) -> int:
    try:
        pedido = approval.reject(args.id, by=args.by, note=args.note)
    except approval.ApprovalError as exc:
        return _fail(str(exc))
    notify.refresh_waiting()
    _out(pedido, True) if args.json else print(T("recusado: ", "rejected: ") + str(pedido["subject"]))
    return 0


def cmd_ask(args) -> int:
    conta = config.get_account(args.account)
    pergunta = approval.ask(conta["name"], args.question, context=args.context or "",
                            options=args.option, agent=args.agent, request_id=args.request)
    notify.pending_question(pergunta)
    _out(pergunta, True) if args.json else print(
        f"pergunta {pergunta['id']} registrada — o dono responde com "
        f"'mailforai answer {pergunta['id']} \"...\"'")
    return 0


def cmd_answer(args) -> int:
    try:
        pergunta = approval.answer(args.id, args.text)
    except approval.ApprovalError as exc:
        return _fail(str(exc))
    notify.refresh_waiting()
    _out(pergunta, True) if args.json else print(T("respondido: ", "answered: ") + pergunta["question"])
    return 0


def cmd_questions(args) -> int:
    itens = approval.questions(status=None if args.all else "open", limit=args.limit)
    if args.json:
        _out(itens, True)
        return 0
    if not itens:
        print(T("nenhuma pergunta aberta", "no open questions"))
    for pergunta in itens:
        marca = {"open": "?", "answered": "✓", "dismissed": "⊘"}.get(pergunta["status"], " ")
        print(f"{marca} [{pergunta['id']}] {pergunta['question']}")
        if pergunta.get("answer"):
            print(f"       → {pergunta['answer']}")
    return 0


def cmd_mode(args) -> int:
    cfg = config.load()
    name = args.account or cfg.get("default_account")
    if not name or name not in cfg.get("accounts", {}):
        return _fail("conta não encontrada")
    if args.mode:
        cfg["accounts"][name].setdefault("approval", {})["mode"] = args.mode
        config.save(cfg)
    atual = approval.mode(config.get_account(name))
    if args.json:
        _out({"account": name, "mode": atual}, True)
        return 0
    print(T(f"conta '{name}': modo {atual}", f"mailbox '{name}': mode {atual}"))
    print(T("  auto     a IA envia sozinha, respeitando allowlist e teto",
            "  auto     the AI sends on its own, within allowlist and cap")
          if atual == "auto" else
          T("  confirm  a IA cria um pedido e nada sai até você aprovar",
            "  confirm  the AI queues a request and nothing goes out until you approve"))
    return 0


def cmd_serve(args) -> int:
    from .webserver import serve
    serve(port=args.port, account=args.account, open_browser=not args.no_open)
    return 0


def cmd_lang(args) -> int:
    cfg = config.load()
    if args.code:
        cfg["language"] = args.code
        config.save(cfg)
        set_language(args.code)
    elif args.system:
        cfg.pop("language", None)
        config.save(cfg)
        set_language(None)
    atual = language()
    if args.json:
        _out({"language": atual, "saved": cfg.get("language")}, True)
        return 0
    print(T(f"idioma: {atual}", f"language: {atual}"))
    return 0


def cmd_hook(args) -> int:
    """Instala (ou tira) o lembrete no Claude Code, valendo para todo projeto."""
    import os
    settings = Path(os.path.expanduser("~/.claude/settings.json"))
    script = Path(__file__).resolve().parent.parent / "hooks" / "waiting_hook.py"
    comando = f"python3 {script}"

    if not settings.parent.exists():
        return _fail("~/.claude não existe — o Claude Code não está instalado aqui")
    dados = {}
    if settings.exists():
        try:
            dados = json.loads(settings.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return _fail(f"{settings} não é um JSON válido — não vou mexer nele")

    hooks = dados.setdefault("hooks", {})
    mudou = False
    for evento in ("UserPromptSubmit", "SessionStart"):
        grupos = hooks.setdefault(evento, [])
        ja_tem = any(comando in json.dumps(g) or "waiting_hook.py" in json.dumps(g)
                     for g in grupos)
        if args.remove:
            restantes = [g for g in grupos if "waiting_hook.py" not in json.dumps(g)]
            if len(restantes) != len(grupos):
                hooks[evento] = restantes
                mudou = True
        elif not ja_tem:
            grupos.append({"hooks": [{"type": "command", "command": comando, "timeout": 5}]})
            mudou = True

    if mudou:
        # backup antes de escrever: settings.json é do usuário, não do app
        if settings.exists():
            settings.with_suffix(".json.mailforai-bak").write_text(
                settings.read_text(encoding="utf-8"), encoding="utf-8")
        settings.write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")
    if args.remove:
        print("lembrete removido" if mudou else "não havia lembrete instalado")
    else:
        print(f"lembrete {'instalado' if mudou else 'já estava instalado'} em {settings}")
        print("Toda sessão do Claude Code, em qualquer projeto, avisa o que está parado.")
    return 0


def cmd_mcp(args) -> int:
    from .mcp_server import run
    run(owner=args.owner)
    return 0


# ---------------------------------------------------------------- parser


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mailforai",
        description="Uma caixa de e-mail que uma IA pode usar sozinha, "
                    "com trava de destinatário e histórico auditável.")
    parser.add_argument("--version", action="version", version=f"mailforai {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    def add(name, func, help_text):
        p = sub.add_parser(name, help=help_text)
        p.set_defaults(func=func)
        p.add_argument("--account", "-a", help="conta a usar (padrão: a default)")
        p.add_argument("--json", action="store_true", help="saída em JSON")
        return p

    p = add("setup", cmd_setup, "configurar uma conta (interativo)")
    p.add_argument("--address")
    p.add_argument("--name")
    p.add_argument("--provider", choices=list(providers.PROVIDERS))
    p.add_argument("--username")
    p.add_argument("--display-name")
    p.add_argument("--smtp-host")
    p.add_argument("--imap-host")
    p.add_argument("--identity", choices=list(identity.MODES))
    p.add_argument("--owner-name")

    p = add("secret", cmd_secret, "gravar/trocar a senha da conta no chaveiro")
    p.add_argument("--stdin", action="store_true",
                   help="ler a senha da entrada padrão (ex.: pbpaste | mailforai secret conta --stdin)")
    add("accounts", cmd_accounts, "listar as contas configuradas")
    add("doctor", cmd_doctor, "testar login SMTP e IMAP")

    p = add("send", cmd_send, "enviar uma mensagem")
    p.add_argument("--to", "-t", required=True, help="destinatários separados por vírgula")
    p.add_argument("--subject", "-s", required=True)
    p.add_argument("--body", "-b", help="texto, ou '-' para ler da entrada padrão")
    p.add_argument("--cc")
    p.add_argument("--bcc")
    p.add_argument("--attach", action="append", metavar="ARQUIVO")
    p.add_argument("--in-reply-to")
    p.add_argument("--agent", help="quem pediu o envio (vai para o histórico)")
    p.add_argument("--reason", help="por que mandar isso — o dono lê antes de aprovar")
    p.add_argument("--dry-run", action="store_true", help="valida e monta, mas não envia")

    p = add("inbox", cmd_inbox, "listar a caixa de entrada")
    p.add_argument("--limit", "-n", type=int, default=15)
    p.add_argument("--unread", action="store_true")
    p.add_argument("--mailbox", default="INBOX")

    p = add("read", cmd_read, "ler uma mensagem pelo UID")
    p.add_argument("uid")
    p.add_argument("--mailbox", default="INBOX")
    p.add_argument("--keep-unread", action="store_true")

    p = add("reply", cmd_reply, "responder uma mensagem pelo UID")
    p.add_argument("uid")
    p.add_argument("--body", "-b")
    p.add_argument("--mailbox", default="INBOX")
    p.add_argument("--agent")
    p.add_argument("--dry-run", action="store_true")

    p = add("history", cmd_history, "o que a IA já mandou")
    p.add_argument("--limit", "-n", type=int, default=20)
    p.add_argument("--all", action="store_true", help="todas as contas")

    add("stats", cmd_stats, "resumo do histórico")

    p = add("publish", cmd_publish, "gerar o histórico cifrado para o site")
    p.add_argument("--out", default="docs/data")
    p.add_argument("--all", action="store_true")
    p.add_argument("--passphrase", help="evite: fica no histórico do shell")

    p = add("allow", cmd_allow, "liberar destinatário ('*@dominio.com' vale)")
    p.add_argument("pattern", nargs="+")

    p = add("block", cmd_block, "bloquear destinatário")
    p.add_argument("pattern", nargs="+")

    p = add("limit", cmd_limit, "teto de mensagens por 24h (0 = sem teto)")
    p.add_argument("n", type=int)

    p = add("pending", cmd_pending, "o que está esperando sua aprovação")
    p.add_argument("--limit", "-n", type=int, default=20)
    p.add_argument("--all", action="store_true", help="inclui já decididos")
    p.add_argument("--all-accounts", action="store_true")
    p.add_argument("--full", action="store_true", help="corpo inteiro, sem cortar")

    p = add("approve", cmd_approve, "aprovar e enviar um pedido da fila")
    p.add_argument("id")
    p.add_argument("--subject", help="corrigir o assunto antes de enviar")
    p.add_argument("--body", help="corrigir o corpo antes de enviar")
    p.add_argument("--to", help="corrigir o destinatário antes de enviar")
    p.add_argument("--by", default="dono", help="quem aprovou (vai para o registro)")

    p = add("reject", cmd_reject, "recusar um pedido da fila")
    p.add_argument("id")
    p.add_argument("--note", help="o motivo, que a IA lê depois")
    p.add_argument("--by", default="dono")

    p = add("ask", cmd_ask, "a IA registra uma pergunta para o dono")
    p.add_argument("question")
    p.add_argument("--context", help="o que a IA já sabe")
    p.add_argument("--option", action="append", help="resposta sugerida (repetível)")
    p.add_argument("--request", help="id do envio que depende desta resposta")
    p.add_argument("--agent")

    p = add("answer", cmd_answer, "responder uma pergunta da IA")
    p.add_argument("id")
    p.add_argument("text")

    p = add("questions", cmd_questions, "perguntas da IA")
    p.add_argument("--all", action="store_true")
    p.add_argument("--limit", "-n", type=int, default=20)

    p = add("mode", cmd_mode, "enviar sozinha (auto) ou pedir aprovação (confirm)")
    p.add_argument("mode", nargs="?", choices=list(approval.MODES))

    p = add("identity", cmd_identity, "como a IA se apresenta (ia | assistente | dono)")
    p.add_argument("mode", nargs="?", choices=list(identity.MODES),
                   help="omita para só ver a identidade atual")
    p.add_argument("--owner-name", help="nome do dono da caixa")
    p.add_argument("--agent-name", help="nome da IA")
    p.add_argument("--signature", help="assinatura fixa; vazio deixa o modo escolher")

    p = add("serve", cmd_serve, "abrir o histórico no navegador (localhost)")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--no-open", action="store_true")

    p = add("lang", cmd_lang, "idioma do CLI (pt | en)")
    p.add_argument("code", nargs="?", choices=["pt", "en"])
    p.add_argument("--system", action="store_true", help="voltar a seguir o sistema")

    p = add("hook", cmd_hook, "lembrar no Claude Code, em qualquer projeto, o que está parado")
    p.add_argument("--remove", action="store_true", help="desinstalar o lembrete")

    p = add("mcp", cmd_mcp, "rodar como servidor MCP (stdio) para a IA plugar")
    p.add_argument("--owner", action="store_true",
                   help="acrescenta as ferramentas de decisão (aprovar, recusar, responder)")
    return parser


def main(argv=None) -> int:
    # a escolha salva vale antes de imprimir qualquer coisa, inclusive o --help
    try:
        set_language(config.load().get("language"))
    except Exception:
        pass
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except config.ConfigError as exc:
        return _fail(str(exc))
    except KeyboardInterrupt:
        print()
        return 130
