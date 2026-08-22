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

## 21/08/2026 — segunda rodada

- [x] *"ja criei o email, so precisamos descobrir agr como te damos acesso a ele"* —
  `Claude@nspx.dev` existe no iCloud. O acesso é uma **senha de aplicativo**
  gerada em account.apple.com (só ele pode: exige a senha dele e o 2FA).
- [ ] *"dai coloca uma opção, de enviar email automaticamente, ou vc ter q confirmar
  primeiro, tipo o claude code, q tem essas opcoes"* — modos de aprovação.
- [ ] *"a ai pode fazer varias coisas, como sla, responder email de suporte (...)
  mando pro email do claude e ele responde pra mim (...) tbm com apps meus por
  exemplo, se eu implementar funcao de suporte, claude ajuda eles"*.
- [ ] *"n quero interface web, quero o esquema de homebrew q eu fiz tipo no
  taskmanager, para parecer um app de vdd. alem de ter o cli pra propria ia poder
  fazer"* — app nativo via Homebrew, no molde do Mac Task Manager.
- [ ] *"tbm quero q eu possa aceitar direito por aqui, pelo chat os emails, caso eu
  esqueça do app"* — aprovar pelo chat do Claude Code.
- [ ] *"seria legal, se aparece-se sempre, o claude code enchendo o saco, msm se n
  for no msm projeto, aparece solicitacao de email revisar, aceitar ou recusar"* —
  aviso de pendência em qualquer sessão, não só neste projeto.
- [ ] *"a ia tbm faz perguntas pra vc quando necessario, ex: suporte nintendo, eles
  podem querer perguntar seu id (...) quando precisa de informacao extra colocar
  informacao extra"* — a IA pergunta, ele responde.
- [ ] *"pro desing do app dps usamos claude desing (...) quando for fazer o prompt
  pro claude desing me avisa, q dai vamos usar o fable"* — avisar antes de escrever
  o prompt do Claude Design.
- [ ] Traduzir o CLI e a página do histórico (i18n) — regra nova, vale para todo
      projeto.
