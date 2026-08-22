/* MailForAI — leitor do histórico.
 *
 * Dois modos, decididos pelo que existe ao lado da página:
 *   data/history.json      — servido por `mailforai serve` na própria máquina, em claro
 *   data/history.enc.json  — publicado num site estático, cifrado; a senha decifra aqui
 */

const CHAVE_LEMBRAR = "mailforai.pass";
let TODAS = [];
let filtro = { status: "todos", texto: "" };

const $ = (id) => document.getElementById(id);

/* ---------------------------------------------------------------- decifragem */

const b64 = (s) => Uint8Array.from(atob(s), (c) => c.charCodeAt(0));

async function derivar(senha, salt, iteracoes) {
  const base = await crypto.subtle.importKey(
    "raw", new TextEncoder().encode(senha), "PBKDF2", false, ["deriveBits"]);
  const bits = await crypto.subtle.deriveBits(
    { name: "PBKDF2", salt, iterations: iteracoes, hash: "SHA-256" }, base, 512);
  return { enc: new Uint8Array(bits, 0, 32), mac: new Uint8Array(bits, 32, 32) };
}

async function decifrar(blob, senha) {
  const salt = b64(blob.salt), iv = b64(blob.iv), ct = b64(blob.ct), tag = b64(blob.tag);
  const { enc, mac } = await derivar(senha, salt, blob.kdf.iterations);

  // encrypt-then-MAC: conferir a autenticidade antes de decifrar qualquer byte
  const chaveMac = await crypto.subtle.importKey(
    "raw", mac, { name: "HMAC", hash: "SHA-256" }, false, ["verify"]);
  const assinado = new Uint8Array(salt.length + iv.length + ct.length);
  assinado.set(salt, 0); assinado.set(iv, salt.length); assinado.set(ct, salt.length + iv.length);
  if (!(await crypto.subtle.verify("HMAC", chaveMac, tag, assinado))) {
    throw new Error("senha errada");
  }

  const chaveAes = await crypto.subtle.importKey(
    "raw", enc, { name: "AES-CBC" }, false, ["decrypt"]);
  const claro = await crypto.subtle.decrypt({ name: "AES-CBC", iv }, chaveAes, ct);
  return JSON.parse(new TextDecoder().decode(claro));
}

/* ---------------------------------------------------------------- carregamento */

async function carregar() {
  const local = await fetch("data/history.json", { cache: "no-store" }).catch(() => null);
  if (local && local.ok) {
    mostrarLista(await local.json(), "local");
    return;
  }
  const cifrado = await fetch("data/history.enc.json", { cache: "no-store" }).catch(() => null);
  if (!cifrado || !cifrado.ok) {
    // ninguém publicou histórico aqui: a página vira a apresentação do projeto
    $("sub").textContent = t("about");
    $("nota-erro").textContent = t("none");
    $("tela-sobre").hidden = false;
    return;
  }
  const blob = await cifrado.json();
  const lembrada = sessionStorage.getItem(CHAVE_LEMBRAR) || localStorage.getItem(CHAVE_LEMBRAR);
  if (lembrada) {
    try {
      mostrarLista(await decifrar(blob, lembrada), "published");
      return;
    } catch (_) {
      localStorage.removeItem(CHAVE_LEMBRAR);
      sessionStorage.removeItem(CHAVE_LEMBRAR);
    }
  }
  $("sub").textContent = t("encrypted");
  $("tela-senha").hidden = false;
  $("senha").focus();
  $("form-senha").addEventListener("submit", async (evento) => {
    evento.preventDefault();
    const senha = $("senha").value;
    $("erro-senha").hidden = true;
    try {
      const dados = await decifrar(blob, senha);
      ($("lembrar").checked ? localStorage : sessionStorage).setItem(CHAVE_LEMBRAR, senha);
      $("tela-senha").hidden = true;
      mostrarLista(dados, "published");
    } catch (erro) {
      $("erro-senha").textContent = t("wrongPass");
      $("erro-senha").hidden = false;
      $("senha").select();
    }
  });
}

/* ---------------------------------------------------------------- tela */

let LEGENDA_ATUAL = "about";
let DADOS_ATUAIS = null;

function mostrarLista(dados, legenda) {
  TODAS = dados.entries || [];
  LEGENDA_ATUAL = legenda;
  DADOS_ATUAIS = dados;
  $("sub").textContent = t(legenda);
  $("tela-lista").hidden = false;
  $("resumo").hidden = false;
  const conta = (status) => TODAS.filter((e) => e.status === status).length;
  $("n-sent").textContent = conta("sent");
  $("n-blocked").textContent = conta("blocked");
  $("n-failed").textContent = conta("failed");
  $("rodape-data").textContent = dados.generated
    ? t("generatedAt") + " " + new Date(dados.generated).toLocaleString(
        IDIOMA === "pt" ? "pt-BR" : "en-US")
    : "";
  desenhar();
}

function aplicarFiltro() {
  const texto = filtro.texto.toLowerCase();
  return TODAS.filter((e) => {
    if (filtro.status !== "todos" && e.status !== filtro.status) return false;
    if (!texto) return true;
    return [e.subject, e.body, (e.to || []).join(" "), e.agent]
      .join(" ").toLowerCase().includes(texto);
  });
}

function desenhar() {
  const lista = $("lista");
  const itens = aplicarFiltro();
  lista.innerHTML = "";
  $("vazio").hidden = itens.length > 0;

  for (const entrada of itens) {
    const li = document.createElement("li");
    li.className = "item " + entrada.status;

    const botao = document.createElement("button");
    botao.className = "cabeca";
    botao.innerHTML =
      `<span class="assunto"></span><span class="para"></span><span class="data"></span>`;
    // textContent em vez de HTML: o assunto vem de fora e não vira marcação
    botao.querySelector(".assunto").textContent =
      entrada.subject || (IDIOMA === "pt" ? "(sem assunto)" : "(no subject)");
    botao.querySelector(".para").textContent = (entrada.to || []).join(", ");
    botao.querySelector(".data").textContent = new Date(entrada.ts).toLocaleString(
      IDIOMA === "pt" ? "pt-BR" : "en-US", { dateStyle: "short", timeStyle: "short" });

    const corpo = document.createElement("div");
    corpo.className = "corpo";
    corpo.hidden = true;
    const pre = document.createElement("pre");
    pre.textContent = entrada.body || "";
    corpo.appendChild(pre);

    if (entrada.error) {
      const motivo = document.createElement("p");
      motivo.className = "motivo";
      const rotulo = entrada.status === "blocked"
        ? (IDIOMA === "pt" ? "Recusado: " : "Refused: ")
        : (IDIOMA === "pt" ? "Falhou: " : "Failed: ");
      motivo.textContent = rotulo + entrada.error;
      corpo.appendChild(motivo);
    }

    const meta = document.createElement("div");
    meta.className = "meta";
    const campos = [
      [IDIOMA === "pt" ? "conta" : "account", entrada.account],
      [IDIOMA === "pt" ? "pedido por" : "asked by", entrada.agent],
      ["cc", (entrada.cc || []).join(", ")],
      ["anexos", (entrada.attachments || []).join(", ")],
      ["message-id", entrada.message_id],
    ].filter(([, valor]) => valor);
    for (const [rotulo, valor] of campos) {
      const span = document.createElement("span");
      span.textContent = `${rotulo}: ${valor}`;
      meta.appendChild(span);
    }
    corpo.appendChild(meta);

    botao.addEventListener("click", () => { corpo.hidden = !corpo.hidden; });
    li.append(botao, corpo);
    lista.appendChild(li);
  }
}

$("busca").addEventListener("input", (evento) => {
  filtro.texto = evento.target.value;
  desenhar();
});
$("chips").addEventListener("click", (evento) => {
  const chip = evento.target.closest(".chip");
  if (!chip) return;
  document.querySelectorAll(".chip").forEach((c) => c.classList.remove("ativo"));
  chip.classList.add("ativo");
  filtro.status = chip.dataset.status;
  desenhar();
});

// trocar de idioma redesenha o que o JS escreveu, sem recarregar a página
document.addEventListener("idioma", () => {
  if (DADOS_ATUAIS) mostrarLista(DADOS_ATUAIS, LEGENDA_ATUAL);
  else {
    $("sub").textContent = t(LEGENDA_ATUAL);
    const nota = $("nota-erro");
    if (nota && nota.textContent) nota.textContent = t("none");
  }
});

carregar();
