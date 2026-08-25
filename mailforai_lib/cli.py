"""Linha de comando do MailForAI."""

import argparse
import getpass
import json
import sys
from pathlib import Path
from typing import Any, Dict

from . import (__version__, approval, brain, config, crypto, diagnose, guard, history,
               identity, keyring, mailer, memory, notify, providers, reader,
               service, watch)
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
    if args.no_prompt and not args.address:
        return _fail(T("--no-prompt exige --address", "--no-prompt requires --address"))
    address = args.address or input(T("Endereço da IA (ex.: claude@seudominio.dev): ",
                                      "Address for the AI (e.g. claude@yourdomain.dev): ")).strip()
    if "@" not in address:
        return _fail(T("isso não é um endereço de e-mail", "that is not an email address"))

    provider = args.provider
    if not provider and args.no_prompt:
        provider = providers.guess(address)
    if not provider:
        chute = providers.guess(address)
        print(T("\nProvedores:", "\nProviders:"))
        for key, preset in providers.PROVIDERS.items():
            marca = " (chute pelo domínio)" if key == chute else ""
            print(f"  {key:9} {preset['label']}{marca}")
        provider = input(T(f"\nProvedor [{chute}]: ", f"\nProvider [{chute}]: ")).strip() or chute
    if provider not in providers.PROVIDERS:
        return _fail(f"provedor '{provider}' desconhecido")

    preset = providers.PROVIDERS[provider]
    username = args.username
    if not username and args.no_prompt:
        username = address
    if not username:
        print(T("\nUsuário de login — ", "\nLogin username — ") + preset["username_hint"])
        username = input(T(f"Usuário [{address}]: ", f"Username [{address}]: ")).strip() or address

    smtp_host = args.smtp_host
    imap_host = args.imap_host
    if provider == "custom" and not smtp_host and args.no_prompt:
        return _fail(T("o provedor 'custom' exige --smtp-host",
                       "the 'custom' provider needs --smtp-host"))
    if provider == "custom" and not smtp_host:
        smtp_host = input("Host SMTP: ").strip()
        imap_host = input("Host IMAP: ").strip()

    name = args.name or address.split("@")[0]
    account = config.build_account(
        name=name, address=address, provider=provider, username=username,
        display_name=args.display_name, smtp_host=smtp_host, imap_host=imap_host,
        smtp_port=args.smtp_port, imap_port=args.imap_port, no_tls=args.no_tls,
    )
    if not args.no_prompt:
        print(T("\nComo a IA se apresenta para quem recebe:",
                "\nHow the AI introduces itself to recipients:"))
        print(T("  ia          diz que é um assistente de IA — o padrão, e o único sem ambiguidade",
                "  ia          says it is an AI assistant — the default, and the only unambiguous one"))
        print(T("  assistente  escreve em nome do dono, sem entrar no mérito de ser software",
                "  assistente  writes on the owner's behalf, without arguing about software"))
        print(T("  dono        assina como o próprio dono; quem recebe pensa estar falando com ele",
                "  dono        signs as the owner; recipients believe they are talking to them"))
    modo = args.identity or ("ia" if args.no_prompt
                             else (input(T("Modo [ia]: ", "Mode [ia]: ")).strip() or "ia"))
    if modo not in identity.MODES:
        return _fail(f"modo '{modo}' não existe")
    dono = args.owner_name or ("" if args.no_prompt
                               else input(T("Nome do dono da caixa (ex.: Miguel): ",
                                            "Name of the mailbox owner (e.g. Miguel): ")).strip())
    account["identity"] = dict(identity.DEFAULT_IDENTITY)
    account["identity"].update({"mode": modo, "owner_name": dono,
                                "agent_name": account["display_name"]})

    config.add_account(name, account)
    print(T(f"\nConta '{name}' gravada em {CONFIG_FILE}",
            f"\nMailbox '{name}' saved to {CONFIG_FILE}"))
    completa = config.get_account(name)
    print(T("As mensagens sairão como: ", "Messages will go out as: ")
          + f"{identity.display_name(completa)} <{address}>")

    if args.no_prompt:
        print(T(f"\nSem senha ainda. Grave com: mailforai secret {name} --stdin",
                f"\nNo password yet. Store it with: mailforai secret {name} --stdin"))
        return 0
    print(T("\nSenha — ", "\nPassword — ") + preset["secret_hint"])
    print(T("Ela vai para o chaveiro do sistema. Não fica em arquivo nenhum.",
            "It goes to the system keychain. It is never written to a file."))
    secret = getpass.getpass(T("Senha (não aparece na tela): ",
                               "Password (not echoed): "))
    if secret:
        backend = keyring.set_secret(name, secret)
        print(T("Senha guardada no ", "Password stored in the ") + backend + ".")
        print(T("\nTestando login...", "\nTesting the login..."))
        return cmd_doctor(argparse.Namespace(account=name, json=False))
    print(T(f"\nSem senha ainda. Grave depois com: mailforai secret {name}",
            f"\nNo password yet. Store it later with: mailforai secret {name}"))
    return 0


def cmd_secret(args) -> int:
    # aceita tanto `secret claude` quanto `secret --account claude`: a primeira
    # forma é a que aparece nas mensagens de ajuda, e tinha que funcionar
    account = config.get_account(args.name or args.account)
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
    # o --json vem antes do caso vazio: o app lê esta saída e um texto solto
    # no lugar do JSON o deixava sem saber se havia conta ou se algo quebrou
    if args.json:
        _out({"default": cfg.get("default_account"), "accounts": accounts}, True)
        return 0
    if not accounts:
        print(T("nenhuma conta — rode 'mailforai setup'", "no mailbox yet — run 'mailforai setup'"))
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

    autenticou = result["smtp"] == "ok" and result["imap"] == "ok"
    if not autenticou and (args.fix or args.apple_id):
        print(T("procurando a combinação certa de usuário e senha…",
                "looking for the right username and password format…"))
        try:
            conserto = diagnose.autofix(account, extra_usernames=args.apple_id)
        except keyring.KeyringError as exc:
            return _fail(str(exc))
        if conserto["fixed"]:
            print(T("achei: usuário ", "found it: username ") + conserto["username"]
                  + T(", senha ", ", password ") + conserto["password_format"])
            account = config.get_account(args.account)
            result = reader.check(account)
        else:
            if args.json:
                _out({"fixed": False, "attempts": conserto["attempts"]}, True)
                return 1
            print(T("nenhuma combinação funcionou. Tentei:",
                    "no combination worked. Tried:"))
            for tentativa in conserto["attempts"]:
                print(f"  {tentativa['username']} ({tentativa['password_format']}) — "
                      f"{tentativa['detail']}")
            return 1
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
    # o escopo vale para a listagem também: numa caixa compartilhada, mostrar
    # tudo já entrega a correspondência do dono para quem olha o app
    escopo = watch.settings(account)["scope"]
    if escopo == "alias" and not args.all:
        messages = [m for m in messages
                    if account["address"].lower() in
                    ((m.get("to") or "") + " " + (m.get("cc") or "")).lower()]
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
    # sem isto a página nem pede o arquivo cifrado: ela confia no manifesto para
    # não sondar arquivo ausente e sujar o console de quem só veio ler a apresentação
    (out_dir / "manifest.json").write_text(
        json.dumps({"local": False, "published": True}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
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
    print(T("modo: ", "mode: ") + resumo["mode"] + "\n"
          + T("De:   ", "From: ") + resumo["from"] + "\n"
          + T("assinatura:\n  ", "signature:\n  ") + resumo["signature"].replace("\n", "\n  "))
    print(T("cabeçalhos: ", "headers: ")
          + (", ".join(f"{k}: {v}" for k, v in resumo["headers"].items())
             or T("nenhum — a mensagem não se anuncia como automática",
                  "none — the message does not announce itself as automated")))
    if resumo["mode"] == "dono":
        print(T("\naviso: neste modo quem recebe acredita estar falando com a pessoa.",
                "\nwarning: in this mode recipients believe they are talking to the person."))
    return 0


def _mostrar_pedido(pedido: Dict[str, Any], completo: bool = False) -> None:
    print(f"[{pedido['id']}] {pedido['subject'] or '(sem assunto)'}")
    print("       " + T("para: ", "to:   ") + ", ".join(pedido["to"]))
    if pedido.get("cc"):
        print("       cc:   " + ", ".join(pedido["cc"]))
    print("       " + T("quem: ", "who:  ") + pedido["agent"]
          + T("   quando: ", "   when: ") + pedido["created"][:16])
    if pedido.get("reason"):
        print("       " + T("motivo: ", "why:  ") + pedido["reason"])
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
            print("       " + T("contexto: ", "context: ") + pergunta["context"])
        if pergunta.get("options"):
            print("       " + T("opções: ", "options: ") + ", ".join(pergunta["options"]))
        print("       " + T("responder: ", "answer with: ")
              + f"mailforai answer {pergunta['id']} \"...\"")
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
        T(f"pergunta {pergunta['id']} registrada — o dono responde com ",
          f"question {pergunta['id']} recorded — the owner answers with ")
        + f"'mailforai answer {pergunta['id']} \"...\"'")
    return 0


def cmd_answer(args) -> int:
    try:
        pergunta = approval.answer(args.id, args.text)
    except approval.ApprovalError as exc:
        return _fail(str(exc))
    # o dado que ele acabou de dar não volta a ser perguntado
    aprendido = memory.learn_from_answer(pergunta["question"], args.text)
    notify.refresh_waiting()
    if aprendido and not args.json:
        print(T("guardei: ", "learned: ") + f"{aprendido['label']} = {aprendido['value']}")
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


def cmd_app(args) -> int:
    """Abre o app. Útil quando a barra de menus está cheia e o ícone sumiu."""
    import subprocess
    caminhos = ["/Applications/MailForAI.app",
                str(Path(__file__).resolve().parent.parent / "mac" / "MailForAI.app")]
    alvo = next((c for c in caminhos if Path(c).exists()), None)
    if not alvo:
        return _fail(T("o app não está instalado — brew install --cask nspxmiguel/tap/mailforai",
                       "the app is not installed — brew install --cask nspxmiguel/tap/mailforai"))
    subprocess.run(["open", "-a", alvo] + (["--args", "--window"] if args.window else []),
                   check=False)
    print(T("app aberto", "app opened"))
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


def cmd_watch(args) -> int:
    conta = config.get_account(args.account)
    if args.once or args.dry_run:
        try:
            feitos = watch.scan_once(conta, dry_run=args.dry_run)
        except Exception as exc:
            return _fail(str(exc))
        if args.json:
            _out(feitos, True)
            return 0
        if not feitos:
            print(T("nada novo na caixa", "nothing new in the inbox"))
        for item in feitos:
            print(f"[{item['action']}] {item.get('subject')} — {(item.get('from') or '')[:45]}")
            if item.get("reason"):
                print(f"    {item['reason'][:160]}")
        return 0
    print(T(f"vigiando {conta['address']} a cada {args.interval or watch.settings(conta)['interval']}s",
            f"watching {conta['address']} every {args.interval or watch.settings(conta)['interval']}s"))
    watch.run(conta, interval=args.interval)
    return 0


def cmd_memory(args) -> int:
    if args.add:
        rotulo, valor = args.add[0], " ".join(args.add[1:])
        if not valor:
            return _fail(T("faltou o valor", "missing the value"))
        fato = memory.remember(rotulo, valor, category=args.category or "outro",
                               source=T("digitado", "typed by hand"),
                               sensitive=args.sensitive)
        print(T("guardei: ", "learned: ") + f"{fato['label']} = {fato['value']}")
        return 0
    if args.forget:
        ok = memory.forget(args.forget)
        print(T("esqueci", "forgotten") if ok else T("não achei", "not found"))
        return 0 if ok else 1
    if args.notes is not None:
        memory.set_notes(args.notes)
        print(T("observações salvas", "notes saved"))
        return 0
    itens = memory.facts(args.category)
    if args.json:
        _out({"facts": itens, "notes": memory.load().get("notes", "")}, True)
        return 0
    if not itens:
        print(T("ainda não aprendi nada", "nothing learned yet"))
    for fato in itens:
        marca = " *" if fato.get("sensitive") else ""
        print(f"{fato['label']}{marca}: {fato['value']}")
        print(f"    [{fato['category']}] {fato.get('source') or ''} — {fato['updated'][:10]}")
    observacoes = memory.load().get("notes")
    if observacoes:
        print(T("\nObservações:\n", "\nNotes:\n") + observacoes)
    return 0


def cmd_brain(args) -> int:
    cfg = config.load()
    nome = args.account or cfg.get("default_account")
    if not nome or nome not in cfg.get("accounts", {}):
        return _fail(T("conta não encontrada", "mailbox not found"))
    conta = cfg["accounts"][nome]
    if args.backend or args.model:
        miolo = conta.setdefault("brain", {})
        if args.backend:
            miolo["backend"] = args.backend
        if args.model:
            miolo["model"] = args.model
        config.save(cfg)
    atual = conta.get("brain") or {}
    dados = {"backend": atual.get("backend") or brain.DEFAULT_BACKEND,
             "model": atual.get("model"), "available": list(brain.BACKENDS)}
    _out(dados, True) if args.json else print(
        T("cérebro: ", "brain: ") + dados["backend"] + (f" ({dados['model']})" if dados["model"] else ""))
    return 0


def cmd_scope(args) -> int:
    cfg = config.load()
    nome = args.account or cfg.get("default_account")
    if not nome or nome not in cfg.get("accounts", {}):
        return _fail(T("conta não encontrada", "mailbox not found"))
    conta = cfg["accounts"][nome]
    vigia = conta.setdefault("watch", dict(watch.DEFAULT_WATCH))
    for campo, valor in (("scope", args.scope), ("interval", args.interval),
                         ("min_confidence", args.min_confidence)):
        if valor is not None:
            vigia[campo] = valor
    if args.enable_watch is not None:
        vigia["enabled"] = args.enable_watch.lower() in ("sim", "yes", "1", "true", "on")
    config.save(cfg)
    atual = watch.settings(config.get_account(nome))
    if args.json:
        _out(atual, True)
        return 0
    print(T("escopo: ", "scope: ") + atual["scope"] + (
        T("  (só o que é endereçado ao agente)", "  (only mail addressed to the agent)")
        if atual["scope"] == "alias" else T("  (a caixa inteira)", "  (the whole mailbox)")))
    print(T("intervalo: ", "interval: ") + f"{atual['interval']}s   "
          + T("confiança mínima: ", "min confidence: ") + f"{atual['min_confidence']}   "
          + T("automático: ", "automatic: ")
          + (T("ligado", "on") if atual["enabled"] else T("desligado", "off")))
    return 0


def cmd_hook(args) -> int:
    """Instala (ou tira) o lembrete no Claude Code, valendo para todo projeto."""
    import os
    settings = Path(os.path.expanduser("~/.claude/settings.json"))
    if args.status:
        instalado = False
        if settings.exists():
            try:
                dados = json.loads(settings.read_text(encoding="utf-8"))
                instalado = "waiting_hook.py" in json.dumps(dados.get("hooks") or {})
            except json.JSONDecodeError:
                instalado = False
        _out({"installed": instalado, "settings": str(settings)}, True) if args.json \
            else print(T("instalado", "installed") if instalado
                       else T("não instalado", "not installed"))
        return 0
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


def cmd_notify_cmd(args) -> int:
    """Dispara uma notificação de teste — e o pedido de permissão, se faltar."""
    ok = notify.system(args.title or "MailForAI",
                       args.message or T("Notificação de teste", "Test notification"),
                       args.subtitle)
    if args.json:
        _out({"sent": ok}, True)
        return 0 if ok else 1
    print(T("notificação enviada", "notification sent") if ok
          else T("não consegui notificar", "could not notify"))
    return 0 if ok else 1


def cmd_selftest(args) -> int:
    """Prova o ciclo inteiro numa caixa de mentira, sem tocar na de verdade."""
    from . import selftest
    print(T("Testando o agente numa caixa de mentira (nada aqui toca a sua)…\n",
            "Testing the agent against a stand-in mailbox (nothing here touches yours)…\n"))
    resultado = selftest.run()
    if args.json:
        _out(resultado, True)
        return 0 if resultado.get("ok") else 1
    if resultado.get("error"):
        return _fail(resultado["error"])
    print(f"\n{resultado['passed']}/{resultado['total']} " + T("passaram", "passed"))
    return 0 if resultado["ok"] else 1


def cmd_state(args) -> int:
    """Tudo que a interface precisa, numa chamada só.

    O app pedia fila, conta, memória e histórico em quatro processos separados,
    a cada poucos segundos. Quatro interpretadores subindo o tempo todo é o que
    deixava a janela pesada.
    """
    cfg = config.load()
    nome = args.account or cfg.get("default_account")
    conta_bruta = (cfg.get("accounts") or {}).get(nome) if nome else None

    dados = {
        "accounts": {"default": cfg.get("default_account"), "accounts": cfg.get("accounts", {})},
        "pending": approval.outbox(status="pending", limit=30),
        "questions": approval.questions(status="open"),
        "memory": {"facts": memory.facts(), "notes": memory.load().get("notes", "")},
        "history": history.read_all(account=nome, limit=40),
        "watch_log": watch.processed(limit=40),
        "service": service.status(),
    }
    if conta_bruta:
        conta = config.get_account(nome)
        dados["watch"] = watch.settings(conta)
        dados["has_secret"] = keyring.has_secret(nome)
    _out(dados, True)
    return 0


def cmd_service(args) -> int:
    """Liga o vigia como serviço do sistema: funciona com o app fechado."""
    if args.remove:
        dados = service.desinstalar()
    elif args.status:
        dados = service.status()
    else:
        conta = config.get_account(args.account)
        dados = service.instalar(intervalo=args.interval or watch.settings(conta)["interval"],
                                 conta=conta["name"])
    if args.json:
        _out(dados, True)
        return 0 if dados.get("ok", True) else 1
    if dados.get("error"):
        return _fail(dados["error"])
    estado = (T("ligado", "on") if dados.get("running") else
              (T("instalado, subindo…", "installed, starting…") if dados.get("installed")
               else T("desligado", "off")))
    print(T("serviço: ", "service: ") + estado)
    if dados.get("installed"):
        print(T("registro em ", "log at ") + dados["log"])
    return 0


def cmd_connect(args) -> int:
    """Liga a caixa ao Claude Code, para decidir a fila conversando."""
    import shutil
    import subprocess
    binario = shutil.which("claude")
    if not binario:
        return _fail(T("o Claude Code não está instalado nesta máquina",
                       "Claude Code is not installed on this machine"))
    caminho = str(Path(__file__).resolve().parent.parent / "bin" / "mailforai")

    if args.status:
        listagem = subprocess.run([binario, "mcp", "list"], capture_output=True, timeout=30)
        ligado = "mailforai" in listagem.stdout.decode()
        _out({"connected": ligado}, True) if args.json else print(
            T("ligado", "connected") if ligado else T("não ligado", "not connected"))
        return 0

    subprocess.run([binario, "mcp", "remove", "mailforai", "-s", "user"],
                   capture_output=True, timeout=30)
    if args.remove:
        print(T("desligado do Claude Code", "disconnected from Claude Code"))
        return 0

    comando = [binario, "mcp", "add", "mailforai", "-s", "user", "--", caminho, "mcp"]
    if not args.agent_only:
        # com --owner o Claude Code também pode aprovar e recusar pela conversa
        comando.append("--owner")
    proc = subprocess.run(comando, capture_output=True, timeout=60)
    if proc.returncode != 0:
        return _fail(proc.stderr.decode()[:300])
    print(T("ligado ao Claude Code", "connected to Claude Code"))
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
    p.add_argument("--smtp-port", type=int)
    p.add_argument("--imap-port", type=int)
    p.add_argument("--no-tls", action="store_true",
                   help="servidor sem criptografia (rede local ou teste)")
    p.add_argument("--identity", choices=list(identity.MODES))
    p.add_argument("--owner-name")
    p.add_argument("--no-prompt", action="store_true",
                   help="não perguntar nada; é como o app configura a conta")

    p = add("secret", cmd_secret, "gravar/trocar a senha da conta no chaveiro")
    p.add_argument("name", nargs="?", help="conta (o mesmo que --account)")
    p.add_argument("--stdin", action="store_true",
                   help="ler a senha da entrada padrão (ex.: pbpaste | mailforai secret conta --stdin)")
    add("accounts", cmd_accounts, "listar as contas configuradas")
    p = add("doctor", cmd_doctor, "testar login SMTP e IMAP")
    p.add_argument("--fix", action="store_true",
                   help="se falhar, procurar o usuário e o formato de senha que funcionam")
    p.add_argument("--apple-id", action="append", metavar="EMAIL",
                   help="outro usuário para testar (repetível)")

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
    p.add_argument("--all", action="store_true",
                   help="mostrar também o que não é endereçado ao agente")
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

    p = add("app", cmd_app, "abrir o app do MailForAI")
    p.add_argument("--window", action="store_true", help="forçar janela em vez da barra")

    p = add("lang", cmd_lang, "idioma do CLI (pt | en)")
    p.add_argument("code", nargs="?", choices=["pt", "en"])
    p.add_argument("--system", action="store_true", help="voltar a seguir o sistema")

    p = add("watch", cmd_watch, "ler a caixa e agir sozinho")
    p.add_argument("--once", action="store_true", help="uma passada e sai")
    p.add_argument("--dry-run", action="store_true", help="decide mas não age")
    p.add_argument("--interval", type=int, help="segundos entre varreduras")

    p = add("memory", cmd_memory, "o que o agente sabe sobre você")
    p.add_argument("--add", nargs="+", metavar=("RÓTULO", "VALOR"))
    p.add_argument("--forget", metavar="CHAVE")
    p.add_argument("--notes", help="texto livre que entra em todo pedido ao modelo")
    p.add_argument("--category", choices=list(memory.CATEGORIES))
    p.add_argument("--sensitive", action="store_true")

    p = add("brain", cmd_brain, "qual modelo lê e responde")
    p.add_argument("backend", nargs="?", choices=list(brain.BACKENDS))
    p.add_argument("--model")

    p = add("scope", cmd_scope, "o que o agente pode ler na caixa")
    p.add_argument("scope", nargs="?", choices=["alias", "all"])
    p.add_argument("--interval", type=int)
    p.add_argument("--min-confidence", type=float)
    p.add_argument("--enable-watch", metavar="sim|nao",
                   help="ligar ou desligar a leitura automática")

    p = add("hook", cmd_hook, "lembrar no Claude Code, em qualquer projeto, o que está parado")
    p.add_argument("--remove", action="store_true", help="desinstalar o lembrete")
    p.add_argument("--status", action="store_true", help="dizer apenas se está instalado")

    p = add("notify", cmd_notify_cmd, "testar a notificação (e pedir permissão)")
    p.add_argument("--title")
    p.add_argument("--message")
    p.add_argument("--subtitle")

    add("selftest", cmd_selftest, "provar que o agente funciona, numa caixa de mentira")

    add("state", cmd_state, "estado inteiro em JSON (é o que o app lê)")

    p = add("service", cmd_service, "rodar o vigia 24h, mesmo com o app fechado")
    p.add_argument("--remove", action="store_true")
    p.add_argument("--status", action="store_true")
    p.add_argument("--interval", type=int)

    p = add("connect", cmd_connect, "ligar a caixa ao Claude Code")
    p.add_argument("--remove", action="store_true")
    p.add_argument("--status", action="store_true")
    p.add_argument("--agent-only", action="store_true",
                   help="sem as ferramentas de decisão (aprovar/recusar)")

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
