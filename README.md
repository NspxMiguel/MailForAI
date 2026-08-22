# MailForAI

Give an AI agent its own mailbox — one it can actually use, with a leash on who
it may write to and a log of everything it sent.

Agents can already read your screen, run your shell and open pull requests.
Email is the one channel they still cannot touch, because handing an agent a
mail account normally means handing it your mail account. MailForAI splits
those apart: a dedicated address, a password that lives in the OS keychain, a
recipient allowlist, a daily cap, and an append-only history the owner reads in
a browser.

```
mailforai setup                     # one mailbox, any provider
mailforai send -t support@game.com -s "Save file bug" -b "..."
mailforai inbox                     # read what came back
mailforai serve                     # what the agent has been sending, in a browser
```

- **No dependencies.** Python 3.9+ standard library, nothing to `pip install`.
- **Any provider with app passwords.** iCloud, Gmail, Fastmail, Zoho, Outlook,
  Migadu, or any SMTP/IMAP host.
- **MCP built in.** One command plugs the mailbox into Claude Code, or any other
  MCP client.

## Install

```bash
git clone https://github.com/NspxMiguel/MailForAI.git
cd MailForAI
./install.sh
mailforai setup
```

`setup` asks for the address, picks the servers from the provider, and stores
the password in the macOS Keychain (or libsecret on Linux). It never writes the
password to disk.

### Getting an address for the agent

Any mailbox works, but a subdomain-free alias on a domain you own reads best —
`claude@yourdomain.dev`. Two common ways:

| Route | What it takes |
| --- | --- |
| **iCloud+ Custom Email Domain** | iCloud+ subscription, domain added under iCloud settings, MX/SPF/DKIM records at your registrar, then a new address under *Custom Email Domain → Manage → Email Addresses* |
| **Gmail / Workspace** | A plain Gmail account, or a Workspace user; 2FA on, then an app password |

Whatever you pick, the login is an **app-specific password**, not the account
password — that is the whole point. Revoking it later cuts the agent off
without touching anything else you own.

> On iCloud the SMTP/IMAP username is your **Apple ID**, not the alias. The
> `From:` address is the alias; the login is the Apple ID. Getting this backwards
> is the most common cause of an authentication failure here.

## Using it from an AI

### MCP (Claude Code, and any MCP client)

```bash
claude mcp add mailforai -- /absolute/path/to/MailForAI/bin/mailforai mcp
```

That exposes five tools: `send_email`, `list_inbox`, `read_email`,
`reply_email`, `sent_history`. A refused send comes back as a tool error with
the reason, so the agent learns the boundary instead of retrying blindly.

### CLI (agents without MCP)

Any agent that can run a shell command can use the CLI. `--json` on every
command makes the output parseable, and `--agent` tags the history with who
asked:

```bash
mailforai send --json --agent codex -t "support@example.com" -s "Subject" -b "Body"
mailforai inbox --json --unread
```

## Keeping it on a leash

An agent with SMTP can go wrong in three expensive ways: writing to the wrong
person, writing too much, and writing the same thing in a loop. Each control
answers one of those.

```bash
mailforai allow "*@nintendo.com" "support@larian.com"   # only these recipients
mailforai block "boss@work.com"                          # never these
mailforai limit 10                                       # ten messages per 24h
```

An empty allowlist means "anyone" — fine while you are testing, worth
narrowing once the agent runs unattended. Every attempt is recorded either way:
sent, failed, or blocked by policy.

## The history

`~/.mailforai/history.jsonl` is append-only, one JSON object per line, never
rewritten. Two ways to read it:

```bash
mailforai serve      # localhost, in the clear — you are already on the machine
mailforai publish    # encrypted bundle for a static site
```

`publish` writes `docs/data/history.enc.json`: PBKDF2-SHA256 (250k iterations)
derives an encryption key and a MAC key from a passphrase, AES-256-CBC
encrypts, HMAC-SHA256 authenticates. The page decrypts in the browser with
WebCrypto. The file can sit in a public repo — without the passphrase it is
noise. Push it to GitHub Pages and the mailbox log is readable from anywhere,
by you.

## Layout

```
bin/mailforai          entrypoint — runs straight from the clone
mailforai_lib/
  cli.py               commands
  mailer.py            SMTP send
  reader.py            IMAP inbox and read
  guard.py             allowlist, blocklist, daily cap
  history.py           the append-only log
  crypto.py            encryption for the published history
  mcp_server.py        MCP server over stdio
  keyring.py           Keychain / libsecret / env var
docs/                  the history viewer (static, no build step)
```

## Notes

- **Recipients can tell.** Every message carries `X-Mailer: MailForAI` and
  `Auto-Submitted: auto-generated`. An agent writing to a human should say so;
  these headers make that true at the protocol level too.
- **`openssl` is required only by `publish`** — the Python standard library has
  no symmetric cipher. Everything else is stdlib.
- The CLI and the history viewer are currently in Portuguese; the code and the
  docs are in English. Translating the interface is open work.

## License

MIT
