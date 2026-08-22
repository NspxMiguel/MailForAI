"""Presets de servidor para os provedores que aceitam senha de aplicativo.

Só entram aqui provedores onde dá para autenticar com uma senha dedicada,
sem OAuth — é o que permite entregar a caixa para uma IA sem entregar a
conta inteira do dono.
"""

from .i18n import T

PROVIDERS = {
    "icloud": {
        "label": T("iCloud / Apple Mail (domínio próprio ou @icloud.com)",
                   "iCloud / Apple Mail (custom domain or @icloud.com)"),
        "smtp": {"host": "smtp.mail.me.com", "port": 587, "starttls": True},
        "imap": {"host": "imap.mail.me.com", "port": 993, "ssl": True},
        # o iCloud autentica pelo Apple ID, não pelo alias do domínio próprio
        "username_hint": T("seu Apple ID completo (ex.: voce@icloud.com)",
                            "your full Apple ID (e.g. you@icloud.com)"),
        "secret_hint": T("senha de aplicativo criada em account.apple.com > Segurança",
                          "app-specific password from account.apple.com > Sign-In and Security"),
    },
    "gmail": {
        "label": "Gmail / Google Workspace",
        "smtp": {"host": "smtp.gmail.com", "port": 587, "starttls": True},
        "imap": {"host": "imap.gmail.com", "port": 993, "ssl": True},
        "username_hint": T("o endereço completo do Gmail", "the full Gmail address"),
        "secret_hint": T("senha de app em myaccount.google.com/apppasswords (exige 2FA)",
                          "app password at myaccount.google.com/apppasswords (needs 2FA)"),
    },
    "fastmail": {
        "label": "Fastmail",
        "smtp": {"host": "smtp.fastmail.com", "port": 587, "starttls": True},
        "imap": {"host": "imap.fastmail.com", "port": 993, "ssl": True},
        "username_hint": T("o endereço completo", "the full address"),
        "secret_hint": T("app password em fastmail.com/settings/security/apps",
                          "app password at fastmail.com/settings/security/apps"),
    },
    "zoho": {
        "label": "Zoho Mail",
        "smtp": {"host": "smtp.zoho.com", "port": 587, "starttls": True},
        "imap": {"host": "imap.zoho.com", "port": 993, "ssl": True},
        "username_hint": "o endereço completo",
        "secret_hint": T("app password em accounts.zoho.com > Segurança",
                          "app password at accounts.zoho.com > Security"),
    },
    "outlook": {
        "label": "Outlook / Microsoft 365",
        "smtp": {"host": "smtp-mail.outlook.com", "port": 587, "starttls": True},
        "imap": {"host": "outlook.office365.com", "port": 993, "ssl": True},
        "username_hint": "o endereço completo",
        "secret_hint": T("app password — só existe com 2FA ligada na conta",
                          "app password — only exists with 2FA enabled"),
    },
    "migadu": {
        "label": "Migadu",
        "smtp": {"host": "smtp.migadu.com", "port": 587, "starttls": True},
        "imap": {"host": "imap.migadu.com", "port": 993, "ssl": True},
        "username_hint": T("o endereço completo da caixa", "the full mailbox address"),
        "secret_hint": T("senha da caixa criada no admin da Migadu",
                          "mailbox password created in the Migadu admin"),
    },
    "custom": {
        "label": T("Outro servidor (informar host e porta na mão)",
                   "Another server (host and port by hand)"),
        "smtp": {"host": "", "port": 587, "starttls": True},
        "imap": {"host": "", "port": 993, "ssl": True},
        "username_hint": T("o usuário que o servidor espera", "the username the server expects"),
        "secret_hint": T("a senha dessa caixa", "that mailbox's password"),
    },
}


def guess(address: str) -> str:
    """Chuta o preset pelo domínio do endereço. Devolve 'custom' se não souber."""
    domain = address.rsplit("@", 1)[-1].lower()
    table = {
        "icloud.com": "icloud", "me.com": "icloud", "mac.com": "icloud",
        "gmail.com": "gmail", "googlemail.com": "gmail",
        "fastmail.com": "fastmail", "fastmail.fm": "fastmail",
        "zoho.com": "zoho",
        "outlook.com": "outlook", "hotmail.com": "outlook", "live.com": "outlook",
    }
    return table.get(domain, "custom")
