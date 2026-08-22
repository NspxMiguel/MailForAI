import Foundation

/// Textos do app em português e inglês.
///
/// O idioma do sistema é o ponto de partida, não a sentença: alguém com o Mac
/// em inglês pode preferir o app em português, e a escolha fica salva.
/// `MAILFORAI_LANG` força um dos dois, que é como se confere a tradução sem
/// mexer no idioma da máquina inteira.
enum Lang: String {
    case pt, en

    static var current: Lang {
        if let forced = ProcessInfo.processInfo.environment["MAILFORAI_LANG"],
           let lang = Lang(rawValue: String(forced.prefix(2)).lowercased()) {
            return lang
        }
        if let escolhido = UserDefaults.standard.string(forKey: "language"),
           let lang = Lang(rawValue: escolhido) {
            return lang
        }
        return system
    }

    static var system: Lang {
        let preferred = Locale.preferredLanguages.first ?? "en"
        return preferred.lowercased().hasPrefix("pt") ? .pt : .en
    }
}

struct S {
    static func t(_ pt: String, _ en: String) -> String { Lang.current == .pt ? pt : en }

    // navegação
    static var sectionInbox: String { t("Caixa de entrada", "Inbox") }
    static var sectionQueue: String { t("Esperando você", "Waiting on you") }
    static var sectionSent: String { t("Enviados", "Sent") }
    static var sectionMemory: String { t("Memória", "Memory") }
    static var sectionSettings: String { t("Ajustes", "Settings") }

    // gerais
    static var approve: String { t("Aprovar e enviar", "Approve and send") }
    static var reject: String { t("Recusar", "Reject") }
    static var sendAnswer: String { t("Responder", "Answer") }
    static var send: String { t("Enviar", "Send") }
    static var save: String { t("Salvar", "Save") }
    static var add: String { t("Adicionar", "Add") }
    static var cancel: String { t("Cancelar", "Cancel") }
    static var next: String { t("Continuar", "Continue") }
    static var back: String { t("Voltar", "Back") }
    static var to: String { t("Para", "To") }
    static var subject: String { t("Assunto", "Subject") }
    static var why: String { t("Motivo", "Why") }
    static var askedBy: String { t("pedido por", "asked by") }
    static var refresh: String { t("Atualizar", "Refresh") }
    static var checkNow: String { t("Verificar agora", "Check now") }
    static var checking: String { t("lendo a caixa…", "reading the mailbox…") }
    static var loading: String { t("carregando…", "loading…") }
    static var saving: String { t("salvando…", "saving…") }
    static var testing: String { t("testando…", "testing…") }
    static var quit: String { t("Sair", "Quit") }
    static var openApp: String { t("Abrir o MailForAI", "Open MailForAI") }
    static var openHistory: String { t("Abrir histórico", "Open history") }
    static var compose: String { t("Escrever", "Compose") }
    static var showMore: String { t("Ver mensagem inteira", "Show full message") }
    static var showLess: String { t("Encolher", "Show less") }
    static var forget: String { t("Esquecer", "Forget") }
    static var writtenInApp: String { t("escrito por você no app", "written by you in the app") }

    // estados
    static var nothingWaiting: String { t("Nada esperando você", "Nothing waiting on you") }
    static var waitingEmails: String { t("E-mails para aprovar", "Emails to approve") }
    static var waitingQuestions: String { t("Perguntas da IA", "Questions from the AI") }
    static var openQuestions: String { t("perguntas abertas", "open questions") }
    static var answerPlaceholder: String { t("Sua resposta…", "Your answer…") }
    static var rejectNote: String { t("Motivo da recusa (opcional)", "Reason (optional)") }
    static var answerBecomesMemory: String {
        t("O que você responder vira memória: não perguntarei de novo.",
          "What you answer becomes memory: I will not ask again.")
    }
    static var notConfiguredShort: String { t("nenhuma caixa configurada", "no mailbox set up") }
    static var cliMissing: String {
        t("Não achei o comando mailforai. Reinstale com: brew reinstall --cask mailforai",
          "Could not find the mailforai command. Reinstall with: brew reinstall --cask mailforai")
    }
    static var inboxHelp: String {
        t("O que chegou, e o que o agente decidiu sobre cada mensagem.",
          "What arrived, and what the agent decided about each message.")
    }
    static var inboxEmpty: String {
        t("Nada na caixa ainda — ou a senha ainda não foi configurada.",
          "Nothing in the mailbox yet — or the password is not set up.")
    }
    static var pickAMessage: String { t("Escolha uma mensagem.", "Pick a message.") }
    static var queueHelp: String {
        t("Nada sai daqui sem você aprovar, e nenhuma pergunta se responde sozinha.",
          "Nothing leaves here without your approval, and no question answers itself.")
    }
    static var sentHelp: String {
        t("Tudo que saiu desta caixa, incluindo o que falhou e o que foi recusado.",
          "Everything that left this mailbox, including failures and refusals.")
    }
    static var sentEmpty: String { t("Nada enviado ainda.", "Nothing sent yet.") }

    // decisões do agente
    static var actionReplied: String { t("respondeu", "replied") }
    static var actionAsked: String { t("perguntou a você", "asked you") }
    static var actionIgnored: String { t("ignorou", "ignored") }
    static var actionEscalated: String { t("passou pra você", "escalated") }
    static var actionOutOfScope: String { t("fora do escopo", "out of scope") }

    // memória
    static var memoryHelp: String {
        t("O que o agente aprendeu sobre você. Ele consulta isto antes de perguntar.",
          "What the agent learned about you. It checks here before asking.")
    }
    static var memoryEmpty: String { t("Ainda não aprendi nada.", "Nothing learned yet.") }
    static var memoryAdd: String { t("Ensinar um dado", "Teach it something") }
    static var memoryLabel: String { t("Nome do dado (ex.: ID da PSN)", "Label (e.g. PSN ID)") }
    static var memoryValue: String { t("Valor", "Value") }
    static var memoryNotes: String { t("Observações livres", "Free-form notes") }
    static var memoryNotesHelp: String {
        t("Entra em todo pedido que o agente faz ao modelo.",
          "Goes into every request the agent makes to the model.")
    }

    // ajustes
    static var settingsHelp: String {
        t("Tudo que dá para mudar sem abrir o terminal.",
          "Everything you can change without opening a terminal.")
    }
    static var settingsAuto: String { t("Automático", "Automatic") }
    static var serviceOn: String {
        t("Funcionar 24h, mesmo com o app fechado",
          "Run around the clock, even with the app closed")
    }
    static var serviceHelp: String {
        t("Instala um serviço do sistema que lê a caixa sozinho, sobe quando o Mac liga e volta "
          + "se cair. É isto que faz o agente trabalhar sem você por perto.",
          "Installs a system service that reads the mailbox on its own, starts with the Mac and "
          + "comes back if it dies. This is what makes the agent work without you around.")
    }
    static var autoWatch: String {
        t("Ler a caixa e agir sozinho", "Read the mailbox and act on its own")
    }
    static var autoWatchHelp: String {
        t("Verificação extra enquanto a janela está aberta. Com o serviço acima ligado, isto é "
          + "só para ver o resultado na hora.",
          "Extra checking while the window is open. With the service above on, this is only to "
          + "see results right away.")
    }
    static var autoEvery: String { t("Verificar a cada", "Check every") }
    static var every1min: String { t("1 minuto", "1 minute") }
    static var every5min: String { t("5 minutos", "5 minutes") }
    static var every15min: String { t("15 minutos", "15 minutes") }
    static var every1hour: String { t("1 hora", "1 hour") }
    static var lastCheck: String { t("Última verificação", "Last check") }
    static var openAtLogin: String { t("Abrir quando eu ligar o Mac", "Open when I start my Mac") }
    static var openAtLoginHelp: String {
        t("Necessário para o agente ler a caixa sem você abrir nada.",
          "Needed for the agent to read the mailbox without you opening anything.")
    }
    static var noCap: String { t("sem teto", "no cap") }
    static var settingsCheck: String { t("Conferir", "Check") }
    static var runSelfTest: String { t("Testar o agente agora", "Test the agent now") }
    static var selfTestHelp: String {
        t("Passa o agente por quatro situações numa caixa de mentira: uma que ele responde, uma "
          + "que ele pergunta, uma propaganda, e uma mensagem com instruções escondidas. Nada "
          + "toca a sua caixa.",
          "Puts the agent through four situations against a stand-in mailbox: one it answers, one "
          + "it asks about, an ad, and a message with hidden instructions. Nothing touches your "
          + "real mailbox.")
    }
    static var testNotification: String { t("Testar notificação", "Test notification") }
    static var notificationHelp: String {
        t("Na primeira vez o macOS pergunta se pode notificar — é preciso permitir para o "
          + "agente avisar quando responder sozinho.",
          "The first time, macOS asks whether it may notify you — allow it, or the agent cannot "
          + "tell you when it answers on its own.")
    }
    static var settingsIntegrations: String { t("Integrações", "Integrations") }
    static var integrationHook: String {
        t("Avisar no Claude Code quando algo estiver esperando",
          "Remind me in Claude Code when something is waiting")
    }
    static var integrationHookHelp: String {
        t("Uma linha no começo de cada conversa, em qualquer projeto, só quando há fila.",
          "One line at the start of each session, in any project, only when the queue is not empty.")
    }
    static var integrationMCP: String {
        t("Deixar o Claude Code decidir a fila por conversa",
          "Let Claude Code clear the queue from a conversation")
    }
    static var integrationMCPHelp: String {
        t("Aprovar, recusar e responder perguntas conversando, sem abrir o app.",
          "Approve, reject and answer questions by chatting, without opening the app.")
    }
    static var reply: String { t("Responder", "Reply") }
    static var sendReply: String { t("Enviar resposta", "Send reply") }
    static var replyQueued: String { t("foi para a fila", "queued for approval") }
    static var replySent: String { t("resposta enviada", "reply sent") }
    static var settingsAccount: String { t("Conta", "Account") }
    static var settingsSending: String { t("Envio", "Sending") }
    static var settingsReading: String { t("Leitura", "Reading") }
    static var settingsIdentity: String { t("Identidade", "Identity") }
    static var settingsBrain: String { t("Cérebro", "Brain") }
    static var settingsAllowlist: String { t("Quem ele pode escrever", "Who it may write to") }
    static var address: String { t("Endereço", "Address") }
    static var username: String { t("Usuário do login", "Login username") }
    static var provider: String { t("Provedor", "Provider") }
    static var changePassword: String { t("Trocar a senha", "Change the password") }
    static var newPassword: String { t("Senha nova", "New password") }
    static var passwordGoesToKeychain: String {
        t("Vai para o Chaveiro do macOS. Não fica em arquivo nenhum.",
          "Goes to the macOS Keychain. It is never written to a file.")
    }
    static var testLogin: String { t("Testar o login", "Test the login") }
    static var modeTitle: String { t("Quando o agente quer enviar", "When the agent wants to send") }
    static var modeAuto: String { t("Envia sozinho", "Sends on its own") }
    static var modeConfirm: String { t("Pede sua aprovação", "Asks you first") }
    static var dailyCap: String { t("Teto por 24h", "Cap per 24h") }
    static var autoTitle: String { t("Deixar a IA enviar sozinha?", "Let the AI send on its own?") }
    static var autoBody: String {
        t("Nesse modo as mensagens saem sem passar por você. A lista de destinatários "
          + "permitidos e o teto diário continuam valendo.",
          "In this mode messages go out without your review. The recipient allowlist and the "
          + "daily cap still apply.")
    }
    static var autoConfirm: String { t("Enviar sozinha", "Send on its own") }
    static var scopeTitle: String { t("O que ele pode ler", "What it may read") }
    static var scopeAlias: String {
        t("Só o que for endereçado ao agente", "Only mail addressed to the agent")
    }
    static var scopeAll: String { t("A caixa inteira", "The whole mailbox") }
    static var scopeHelp: String {
        t("No iCloud, o endereço do agente é apelido e cai na mesma caixa da sua conta pessoal. "
          + "Com o escopo limitado, o agente ignora tudo que não foi endereçado a ele.",
          "On iCloud the agent's address is an alias landing in your personal mailbox. With the "
          + "scope limited, the agent ignores anything not addressed to it.")
    }
    static var scopeAllTitle: String { t("Deixar ler a caixa inteira?", "Read the whole mailbox?") }
    static var scopeAllBody: String {
        t("O agente passará a ler todas as mensagens que chegarem, inclusive as suas pessoais e "
          + "códigos de verificação. Só faça isso numa caixa que seja só dele.",
          "The agent will read every incoming message, including your personal mail and "
          + "verification codes. Only do this on a mailbox that is his alone.")
    }
    static var scopeAllConfirm: String { t("Ler tudo", "Read everything") }
    static var identityTitle: String { t("Como ele se apresenta", "How it introduces itself") }
    static var identityAI: String { t("Diz que é uma IA", "Says it is an AI") }
    static var identityAssistant: String { t("Assistente de você", "Your assistant") }
    static var identityOwner: String { t("Assina como você", "Signs as you") }
    static var identityHelp: String {
        t("No último modo quem recebe acredita estar falando com você.",
          "In the last mode recipients believe they are talking to you.")
    }
    static var brainTitle: String { t("Quem lê e redige", "Who reads and drafts") }
    static var brainHelp: String {
        t("O padrão usa o comando claude já instalado nesta máquina — sem chave de API nova. "
          + "Groq e Gemini usam as chaves guardadas no chaveiro.",
          "The default uses the claude command already installed here — no new API key. Groq and "
          + "Gemini use the keys stored in the keychain.")
    }
    static var allowlistEmpty: String {
        t("Qualquer destinatário (a lista está vazia).", "Anyone (the list is empty).")
    }
    static var allowlistHelp: String {
        t("Com a lista vazia ele escreve para qualquer um. Um item como *@nintendo.com libera "
          + "só aquele domínio.",
          "With an empty list it writes to anyone. An entry like *@nintendo.com allows only that "
          + "domain.")
    }

    // assistente
    static var setupTitle: String { t("Vamos dar um e-mail para a sua IA", "Let's give your AI an email") }
    static var setupSubtitle: String {
        t("Três passos. Nada de terminal — só o endereço, a senha de aplicativo do provedor, e um teste.",
          "Three steps. No terminal — just the address, the provider's app password, and a test.")
    }
    static var setupAddress: String { t("Endereço do agente", "The agent's address") }
    static var setupAddressHelp: String {
        t("O e-mail que a IA vai usar, por exemplo claude@seudominio.dev.",
          "The email the AI will use, e.g. claude@yourdomain.dev.")
    }
    static var setupProvider: String { t("Onde esse e-mail está hospedado", "Where that email lives") }
    static var setupProviderHelp: String {
        t("Escolhido pelo domínio quando dá para adivinhar.",
          "Picked from the domain when it can be guessed.")
    }
    static var setupServers: String { t("Servidores", "Servers") }
    static var setupServersHelp: String {
        t("O host de envio (SMTP) e o de leitura (IMAP), com as portas.",
          "The sending (SMTP) and reading (IMAP) hosts, with their ports.")
    }
    static var setupNoTLS: String {
        t("Servidor sem criptografia (rede local ou teste)",
          "Server without encryption (local network or testing)")
    }
    static var setupOwner: String { t("Seu nome", "Your name") }
    static var setupOwnerHelp: String {
        t("Entra na apresentação: \"assistente de IA de Fulano\".",
          "Goes into the introduction: \"AI assistant to Someone\".")
    }
    static var setupAgentName: String { t("Nome da IA", "The AI's name") }
    static var setupAgentNameHelp: String {
        t("Aparece como remetente para quem recebe.", "Shows as the sender name to recipients.")
    }
    static var setupPasswordTitle: String { t("A senha de aplicativo", "The app password") }
    static var setupPasswordWhy: String {
        t("Não é a senha da sua conta: é uma credencial separada, só para este app, que você "
          + "revoga quando quiser sem mexer em mais nada.",
          "Not your account password: a separate credential, just for this app, which you can "
          + "revoke at any time without touching anything else.")
    }
    static var setupOpenPage: String { t("Abrir a página do provedor", "Open the provider's page") }
    static var setupUsername: String { t("Usuário do login", "Login username") }
    static var setupUsernameApple: String {
        t("No iCloud, é o seu Apple ID inteiro — não o endereço do agente.",
          "On iCloud this is your full Apple ID — not the agent's address.")
    }
    static var setupUsernameSame: String {
        t("Costuma ser o próprio endereço.", "Usually the address itself.")
    }
    static var setupPassword: String { t("Cole a senha aqui", "Paste the password here") }
    static var setupPasswordHelp: String {
        t("Vai direto para o Chaveiro do macOS. O app não guarda em arquivo.",
          "Goes straight to the macOS Keychain. The app never writes it to a file.")
    }
    static var setupTest: String { t("Testar e salvar", "Test and save") }
    static var setupWorked: String {
        t("Funcionou: envio e leitura autenticados.", "It works: sending and reading authenticated.")
    }
    static var setupErrAuth: String {
        t("O servidor recusou a senha. Confira se ela é uma senha de aplicativo (não a da conta) "
          + "e se o usuário está certo — no iCloud é o Apple ID inteiro.",
          "The server refused the password. Check that it is an app password (not your account "
          + "password) and that the username is right — on iCloud it is your full Apple ID.")
    }
    static var setupErrNoSecret: String {
        t("A senha não chegou ao chaveiro. Tente colar de novo.",
          "The password did not reach the keychain. Try pasting it again.")
    }
    static var setupErrNetwork: String {
        t("Não consegui falar com o servidor. Verifique a conexão e tente de novo.",
          "Could not reach the server. Check your connection and try again.")
    }
    static var setupDone: String { t("Pronto.", "All set.") }
    static var setupDoneHelp: String {
        t("A caixa está ligada. O agente começa pedindo sua aprovação para tudo — você troca isso "
          + "em Ajustes quando confiar nele.",
          "The mailbox is live. The agent starts by asking your approval for everything — change "
          + "that in Settings once you trust it.")
    }
    static var setupOpenInbox: String { t("Ver a caixa de entrada", "Open the inbox") }
}
