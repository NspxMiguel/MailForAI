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
- [x] *"dai coloca uma opção, de enviar email automaticamente, ou vc ter q confirmar
  primeiro, tipo o claude code, q tem essas opcoes"* — `mailforai mode auto|confirm`,
  com `confirm` de padrão. No app é o menu do cabeçalho.
- [x] *"a ai pode fazer varias coisas, como sla, responder email de suporte (...)
  mando pro email do claude e ele responde pra mim (...) tbm com apps meus por
  exemplo, se eu implementar funcao de suporte, claude ajuda eles"* — enviar,
  ler a caixa (IMAP) e responder na mesma thread, pelo CLI ou pelo MCP.
- [x] *"n quero interface web, quero o esquema de homebrew q eu fiz tipo no
  taskmanager, para parecer um app de vdd. alem de ter o cli pra propria ia poder
  fazer"* — app SwiftUI na barra de menus,
  `brew install --cask nspxmiguel/tap/mailforai`, com o CLI dentro do bundle.
- [x] *"tbm quero q eu possa aceitar direito por aqui, pelo chat os emails, caso eu
  esqueça do app"* — `mailforai mcp --owner` dá `list_pending`, `approve_email`,
  `reject_email` e `answer_question`; já registrado no Claude Code dele.
- [x] *"seria legal, se aparece-se sempre, o claude code enchendo o saco, msm se n
  for no msm projeto, aparece solicitacao de email revisar, aceitar ou recusar"* —
  `mailforai hook` instala em `~/.claude/settings.json` (SessionStart e
  UserPromptSubmit), vale para todo projeto. Só fala quando há algo parado.
- [x] *"a ia tbm faz perguntas pra vc quando necessario, ex: suporte nintendo, eles
  podem querer perguntar seu id (...) quando precisa de informacao extra colocar
  informacao extra"* — `ask_owner` / `check_answers` no MCP, `mailforai ask` e
  `answer` no CLI, e cartão com campo de resposta no app.
- [ ] *"pro desing do app dps usamos claude desing (...) quando for fazer o prompt
  pro claude desing me avisa, q dai vamos usar o fable"* — avisar antes de escrever
  o prompt do Claude Design.
- [x] i18n — app, página e CLI em português e inglês, seguindo o sistema, com
      troca manual e `MAILFORAI_LANG`. Regra gravada no CLAUDE.md.

## A fazer

- [ ] *"pro desing do app dps usamos claude desing (...) quando for fazer o prompt
  pro claude desing me avisa, q dai vamos usar o fable"* — **aguardando ele**: aviso
  antes de escrever o prompt.
- [ ] Traduzir os textos de ajuda do argparse (`--help`) — o resto do CLI já está
  nos dois idiomas.
- [ ] **Falta ele**: gerar a senha de aplicativo em account.apple.com e rodar
  `pbpaste | mailforai secret claude --stdin`. Sem isso o envio para no SMTP.
