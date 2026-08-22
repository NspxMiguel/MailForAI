import Foundation

/// Um envio parado esperando decisão. Espelha uma linha do outbox.jsonl.
struct PendingEmail: Identifiable, Decodable, Equatable {
    let id: String
    var subject: String?
    var to: [String]
    var cc: [String]?
    var body: String?
    var reason: String?
    var agent: String?
    var account: String?
    var created: String?
    var status: String?

    var displaySubject: String { (subject?.isEmpty == false ? subject! : nil) ?? "—" }
    var recipients: String { to.joined(separator: ", ") }
}

/// Uma pergunta que a IA fez ao dono e ainda não teve resposta.
struct Question: Identifiable, Decodable, Equatable {
    let id: String
    var question: String
    var context: String?
    var options: [String]?
    var agent: String?
    var status: String?
    var answer: String?
}

struct PendingPayload: Decodable {
    var pending: [PendingEmail]
    var questions: [Question]
}

/// Conta configurada, do jeito que `mailforai accounts --json` devolve.
struct MailboxSummary: Equatable {
    var name: String = ""
    var address: String = ""
    var mode: String = "confirm"
    var identity: String = "ia"
    var hasSecret: Bool = false
}
