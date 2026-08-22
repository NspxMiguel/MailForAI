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
mailforai pending                   # what the agent wants to send, awaiting your call
mailforai approve <id>              # send it
mailforai inbox                     # read what came back
```

- **Nothing goes out unapproved**, unless you say so. Two modes, like a coding
  agent's permission modes: `confirm` queues every message for your call,
  `auto` lets it send within the allowlist and the cap.
- **A real app, not a web page.** A macOS app with an inbox, the approval queue,
  sent mail, its memory and every setting — plus a menu-bar item with the count.
  Setting up a mailbox is a guided flow with the steps for each provider; you
  never open a terminal.
- **It reads and answers by itself.** New mail is read, understood and either
  answered, queued for you, ignored, or escalated — and it learns what it needs
  to know about you along the way, so it stops asking twice.
- **No dependencies.** Python 3.9+ standard library, nothing to `pip install`.
- **Any provider with app passwords.** iCloud, Gmail, Fastmail, Zoho, Outlook,
  Migadu, or any SMTP/IMAP host.
- **MCP built in.** One command plugs the mailbox into Claude Code, or any other
  MCP client.

## Install

The Mac app, which brings the CLI with it:

```bash
brew install --cask nspxmiguel/tap/mailforai
```

Or the CLI alone, on any machine with Python 3.9+:

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

That exposes six tools: `send_email`, `list_inbox`, `read_email`,
`reply_email`, `sent_history`, and `mailbox_info` — the last one tells the
agent how the mailbox introduces itself and how much of the daily cap is left,
so it does not sign the body twice or guess at its own name. A refused send
comes back as a tool error with the reason, so the agent learns the boundary
instead of retrying blindly.

### CLI (agents without MCP)

Any agent that can run a shell command can use the CLI. `--json` on every
command makes the output parseable, and `--agent` tags the history with who
asked:

```bash
mailforai send --json --agent codex -t "support@example.com" -s "Subject" -b "Body"
mailforai inbox --json --unread
```

## How the agent introduces itself

Three postures, because the situations really are different. The owner picks —
it is their identity on the line.

```bash
mailforai identity                              # what recipients see today
mailforai identity ia --owner-name Miguel       # the default
mailforai identity assistente
mailforai identity dono
```

| Mode | `From:` | Signature | Announces itself as automated |
| --- | --- | --- | --- |
| `ia` | `Claude (IA de Miguel)` | says it is an AI assistant | yes |
| `assistente` | `Claude · assistente de Miguel` | writes on the owner's behalf | yes |
| `dono` | `Miguel` | the owner's name | no |

`ia` is the default: it is the only one that leaves no doubt on the other end,
and a default that misleads by omission would be the tool's choice, not the
owner's.

`dono` drops the `X-Mailer` and `Auto-Submitted` headers too — keeping them
would say one thing in the body and another in the envelope. Worth knowing
before picking it: recipients will believe they are corresponding with the
person, and some services' terms forbid exactly that.

`Auto-Submitted` also does real work in the other two modes — mail servers read
it to avoid firing auto-replies at robots.

The signature follows the interface language, so a mailbox set to Portuguese
signs in Portuguese. Writing mostly to English-speaking support desks? Pin the
text and the language stops mattering:

```bash
mailforai identity --signature "Claude, AI assistant to Miguel"
```

## Reading and answering on its own

`mailforai watch` (or **Check now** in the app) reads what arrived and decides
one of four things per message:

| Decision | What happens |
| --- | --- |
| `reply` | drafts the answer and follows the mailbox mode — sent, or queued for you |
| `ask` | a fact is missing that only you have; it opens a question instead of guessing |
| `ignore` | newsletters, receipts, automated notices — no reply |
| `escalate` | money, banking, cancellations, legal — it does not answer, it warns you |

A draft it is not confident about never goes out on its own, even in `auto`
mode: below `min_confidence` it lands in the queue anyway.

The model that reads is configurable — by default the `claude` command already
on the machine, so there is no new API key to get. Anthropic, Groq and Gemini
work too.

### What it may read

On iCloud a custom-domain address is an **alias**: `claude@yourdomain.dev`
lands in the same mailbox as your personal mail, and the app-specific password
opens all of it. So the default scope is `alias` — the agent only looks at
messages addressed to it, and skips everything else, recording each skip.

```bash
mailforai scope           # what it is now
mailforai scope alias     # only mail addressed to the agent (default)
mailforai scope all       # the whole mailbox — only on a mailbox that is his alone
```

That is a software leash, not a cryptographic one. For real separation, host
the agent's mailbox somewhere your personal mail is not.

## What it remembers about you

Support asks for a console serial, an account ID, an order number. Answer once:

```bash
mailforai memory                                  # what it knows
mailforai memory --add "PSN ID" nspxmiguel --category conta
mailforai memory --forget psn-id
```

Answering a question in the app or the CLI files the fact automatically, and the
agent reads that list before writing anything. It is a plain JSON file at
`~/.mailforai/memory.json` — readable and deletable without any tool.

## Approving what goes out

The agent drafting a support ticket is useful. The agent sending it at 3am
without you reading it is not, at least not until you trust it. So the mailbox
has the same two postures a coding agent has:

```bash
mailforai mode              # which one is on
mailforai mode confirm      # the default: every message waits for you
mailforai mode auto         # it sends on its own, still inside the leash below
```

In the app, switching to `auto` asks for confirmation first — it disarms the
only thing standing between the agent and a sent message. Switching back never
asks: tightening a leash needs no ceremony.

In `confirm`, `send_email` returns a request id instead of sending, and the
message sits in the queue until you decide:

```bash
mailforai pending                          # queue, with the reason the AI gave
mailforai approve a1b2c3d4                 # send it
mailforai approve a1b2c3d4 --body "..."    # fix the text first, then send
mailforai reject a1b2c3d4 --note "I'll open it myself"
```

Every decision is recorded with who made it — `app`, `chat`, `dono` — and
rejected requests keep the note, which the agent reads before trying again.

### Three ways to decide, so you actually do

1. **The Mac app.** Menu-bar icon with the number of waiting items; the panel
   lists each message with subject, recipient, reason and body, and approves or
   rejects with a click. macOS hides menu-bar icons that do not fit, so opening
   the app again — Launchpad, Finder, or `mailforai app` — brings the same panel
   up as a window.
2. **The terminal.** `mailforai pending`, `approve`, `reject`.
3. **Your AI chat.** `mailforai mcp --owner` adds `list_pending`,
   `approve_email`, `reject_email` and `answer_question`, so you can clear the
   queue from a conversation you are already in.

And so the queue does not rot forgotten:

```bash
mailforai hook          # installs a reminder into Claude Code, every project
```

That hook prints one line at the start of each session and each message —
only when something is actually waiting — naming what is parked. Remove it with
`mailforai hook --remove`.

> The owner tools let an AI record your decision. That is the point of
> approving from a chat, and also its limit: the tool cannot prove the human
> agreed. The record says the decision came through the chat, and the app shows
> it. If you want approval that no agent can perform, do not load `--owner` and
> keep the app or the terminal as the only way in.

## When the AI needs something only you know

Nintendo asks for the console serial, Rockstar wants the Social Club ID. The
agent should not invent it, and should not send the ticket half-filled:

```bash
mailforai questions                      # what it asked
mailforai answer 8f2a1c "NspxMiguel#4471"
```

Over MCP that is `ask_owner` and `check_answers`. The question shows up in the
app, in a notification, and in the Claude Code reminder, next to the email it
is blocking.

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
  identity.py          how the agent introduces itself
  approval.py          the queue, and the questions
  notify.py            system notifications and the waiting summary
  i18n.py              Portuguese and English for the CLI
  history.py           the append-only log
  crypto.py            encryption for the published history
  mcp_server.py        MCP server over stdio
  keyring.py           Keychain / libsecret / env var
docs/                  the history viewer (static, no build step)
hooks/waiting_hook.py  the Claude Code reminder
mac/                   the macOS menu-bar app (SwiftPM, no Xcode project)
```

## Notes

- **Recipients can tell, by default.** Outside `dono` mode every message carries
  `X-Mailer: MailForAI` and `Auto-Submitted: auto-generated`, so the disclosure
  holds at the protocol level and not only in the signature.
- **`openssl` is required only by `publish`** — the Python standard library has
  no symmetric cipher. Everything else is stdlib.
- **Portuguese and English** everywhere the user reads: the app, the history
  page and the CLI follow the system language, each can be switched by hand, and
  `MAILFORAI_LANG=pt|en` forces one. `mailforai lang pt` saves the choice.
  The argparse help strings are still Portuguese-only — the one gap left.

## License

MIT
