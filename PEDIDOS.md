# Pedidos — MailForAI

## 21/08/2026

- [x] *"quero te dar um email, pra vc usar msm, como consigo fazer isso? posso criar
  pra vc?? claude@nspx.dev pra vc fazer oq vc quiser, me ajudar a sla, pedir suporte
  em jogos e etc. um email so pra vc"* — conta `claude` criada no MailForAI
  apontando para `claude@nspx.dev` via iCloud. **Falta ele criar o endereço no
  iCloud e gerar a senha de aplicativo** (ver README).
- [x] *"ai vc salva no seu claude md, + credenciais e vc msm pode mandar emails"* —
  a credencial vai para o **chaveiro do macOS**, não para o CLAUDE.md: o conteúdo
  do CLAUDE.md entra no contexto e o transcript sobe para o claude.ai.
  `pbpaste | mailforai secret claude --stdin` leva a senha da área de
  transferência direto para o chaveiro, sem passar por tela.
- [x] *"mas para isso, vc precisaria criar um app pra eu ver o historico tbm doq vc
  manda"* — `mailforai serve` (local) e `mailforai publish` (cifrado, no site).
- [x] *"e colocar o app no meu github obvio"* — https://github.com/NspxMiguel/MailForAI
  e https://www.nspx.dev/MailForAI/, com capa na vitrine.
- [x] *"ou melhor, faz um app Email for ias, que dai eu posso dar um email, para
  qualquer ia, e posso colocar no github, pra qualquer pessoa poder fazer o msm"* —
  o app é genérico: presets de iCloud, Gmail, Fastmail, Zoho, Outlook e Migadu,
  mais qualquer SMTP/IMAP; MCP para IA com suporte a MCP e CLI `--json` para as
  outras.
- [x] *"coloca nas configuraçÕes do app, para ele se identificar como ia, assistente
  pessoal etc ou nao. (...) ou se ela se identifica pela pessoa e finge ser a pessoa
  msm. vc escolhe."* — `mailforai identity` com três modos (`ia`, `assistente`,
  `dono`). Padrão escolhido: `ia`.

## A fazer

- [ ] Traduzir o CLI e a página do histórico para inglês — o repositório é público
      e o README já está em inglês.
