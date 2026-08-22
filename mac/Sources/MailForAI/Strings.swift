import Foundation

/// Textos do app em português e inglês.
///
/// O idioma sai do sistema, e `MAILFORAI_LANG` força um dos dois — é o que
/// permite conferir a tradução sem trocar o idioma do Mac inteiro.
enum Lang: String {
    case pt, en

    /// O idioma do sistema é o ponto de partida, não a sentença: alguém com o
    /// Mac em inglês pode preferir o app em português, e a escolha fica salva.
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
    static func t(_ pt: String, _ en: String) -> String {
        Lang.current == .pt ? pt : en
    }

    static var nothingWaiting: String { t("Nada esperando você", "Nothing waiting on you") }
    static var waitingEmails: String { t("E-mails para aprovar", "Emails to approve") }
    static var waitingQuestions: String { t("Perguntas da IA", "Questions from the AI") }
    static var approve: String { t("Aprovar e enviar", "Approve and send") }
    static var reject: String { t("Recusar", "Reject") }
    static var send: String { t("Responder", "Answer") }
    static var to: String { t("Para", "To") }
    static var why: String { t("Motivo", "Why") }
    static var askedBy: String { t("pedido por", "asked by") }
    static var answerPlaceholder: String { t("Sua resposta…", "Your answer…") }
    static var rejectNote: String { t("Motivo da recusa (opcional)", "Reason (optional)") }
    static var modeAuto: String { t("Envia sozinha", "Sends on its own") }
    static var modeConfirm: String { t("Pede aprovação", "Asks first") }
    static var modeTitle: String { t("Modo de envio", "Sending mode") }
    static var openHistory: String { t("Abrir histórico", "Open history") }
    static var quit: String { t("Sair", "Quit") }
    static var noMailbox: String {
        t("Nenhuma caixa configurada. Rode 'mailforai setup' no terminal.",
          "No mailbox configured yet. Run 'mailforai setup' in a terminal.")
    }
    static var cliMissing: String {
        t("Não achei o comando mailforai. Instale com ./install.sh no repositório.",
          "Could not find the mailforai command. Install it with ./install.sh in the repo.")
    }
    static var refresh: String { t("Atualizar", "Refresh") }
    static var showMore: String { t("Ver mensagem inteira", "Show full message") }
    static var showLess: String { t("Encolher", "Show less") }
    static var noSecret: String { t("sem senha no chaveiro", "no password in the keychain") }
    static var language: String { t("Idioma", "Language") }
    static var cancel: String { t("Cancelar", "Cancel") }
    static var autoTitle: String {
        t("Deixar a IA enviar sozinha?", "Let the AI send on its own?")
    }
    static var autoBody: String {
        t("Nesse modo as mensagens saem sem passar por você. A lista de "
          + "destinatários permitidos e o teto diário continuam valendo.",
          "In this mode messages go out without your review. The recipient "
          + "allowlist and the daily cap still apply.")
    }
    static var autoConfirm: String { t("Enviar sozinha", "Send on its own") }
}
