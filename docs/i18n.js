/* Tradução da página. O idioma do navegador escolhe o padrão; a escolha do
 * visitante vence e fica salva. O HTML nasce em português — o dicionário só
 * precisa do inglês. */

const TEXTOS_EN = {
  sent: "sent",
  refused: "refused",
  failed: "failed",
  encTitle: "This history is encrypted",
  encBody: "The file is public, the contents are not. Type the passphrase you used in "
    + "<code>mailforai publish</code> — decryption happens here in your browser.",
  passPlaceholder: "history passphrase",
  open: "Open",
  remember: "remember on this browser",
  searchPlaceholder: "search by subject, recipient or text…",
  all: "all",
  empty: "Nothing here yet.",
  aboutTitle: "A mailbox the AI uses on its own",
  aboutBody: "Agents already read your screen, run your shell and open pull requests. Email is "
    + "the channel left over, because giving an AI a mail account today means giving it "
    + "<em>your</em> mail account. MailForAI splits the two: a dedicated address, a password in "
    + "the system keychain, a list of who it may write to, a daily cap, and a history you read "
    + "on this page.",
  b1t: "On a leash",
  b1b: "Recipient allowlist, blocklist and a cap per 24h, checked before every send. What the "
    + "policy refuses is recorded with the reason.",
  b2t: "Auditable history",
  b2b: "One line per attempt, never rewritten — sent, failed or refused. Read it from "
    + "<code>localhost</code>, or publish it encrypted and read it from anywhere.",
  b3t: "Any AI",
  b3b: "MCP server built in for Claude Code and friends; a <code>--json</code> CLI for the "
    + "agents that only know how to run a command.",
  b4t: "Identity",
  b4b: "Three modes: the AI says it is an AI, writes on the owner's behalf, or signs as the "
    + "owner. The default is the one that leaves no doubt on the other end.",
  b5t: "It reads, too",
  b5b: "IMAP inbox: the AI follows the support reply and answers in the same thread, without "
    + "you relaying anything.",
  b6t: "No dependencies",
  b6b: "Python 3.9+ standard library. Clone and use — iCloud, Gmail, Fastmail, Zoho, Outlook, "
    + "Migadu or any SMTP/IMAP.",
  cta: "View on GitHub",
  codeOnGithub: "code on GitHub",
};

const LEGENDAS = {
  pt: {
    local: "histórico local · nada saiu desta máquina",
    published: "histórico publicado · decifrado neste navegador",
    encrypted: "histórico cifrado",
    about: "histórico de e-mail para agentes",
    none: "Nenhum histórico publicado neste endereço — rode mailforai serve na sua máquina.",
    wrongPass: "Senha não confere.",
    generatedAt: "gerado em",
  },
  en: {
    local: "local history · nothing left this machine",
    published: "published history · decrypted in this browser",
    encrypted: "encrypted history",
    about: "email history for agents",
    none: "No history published at this address — run mailforai serve on your machine.",
    wrongPass: "That passphrase does not match.",
    generatedAt: "generated on",
  },
};

const CHAVE_IDIOMA = "mailforai.lang";

function idiomaInicial() {
  const salvo = localStorage.getItem(CHAVE_IDIOMA);
  if (salvo === "pt" || salvo === "en") return salvo;
  return (navigator.language || "en").toLowerCase().startsWith("pt") ? "pt" : "en";
}

let IDIOMA = idiomaInicial();

function t(chave) {
  return LEGENDAS[IDIOMA][chave] ?? LEGENDAS.pt[chave] ?? "";
}

function aplicarIdioma(idioma) {
  IDIOMA = idioma;
  localStorage.setItem(CHAVE_IDIOMA, idioma);
  document.documentElement.lang = idioma === "pt" ? "pt-BR" : "en";

  for (const elemento of document.querySelectorAll("[data-i18n]")) {
    const chave = elemento.dataset.i18n;
    if (!elemento.dataset.ptOriginal) elemento.dataset.ptOriginal = elemento.innerHTML;
    elemento.innerHTML = idioma === "en" && TEXTOS_EN[chave]
      ? TEXTOS_EN[chave]
      : elemento.dataset.ptOriginal;
  }
  for (const elemento of document.querySelectorAll("[data-i18n-ph]")) {
    const chave = elemento.dataset.i18nPh;
    if (!elemento.dataset.ptOriginal) elemento.dataset.ptOriginal = elemento.placeholder;
    elemento.placeholder = idioma === "en" && TEXTOS_EN[chave]
      ? TEXTOS_EN[chave]
      : elemento.dataset.ptOriginal;
  }
  for (const botao of document.querySelectorAll(".chip-lang")) {
    botao.classList.toggle("ativo", botao.dataset.lang === idioma);
  }
  // o app.js redesenha os textos que ele mesmo escreve
  document.dispatchEvent(new CustomEvent("idioma", { detail: idioma }));
}

document.getElementById("idiomas")?.addEventListener("click", (evento) => {
  const botao = evento.target.closest(".chip-lang");
  if (botao) aplicarIdioma(botao.dataset.lang);
});

aplicarIdioma(IDIOMA);
