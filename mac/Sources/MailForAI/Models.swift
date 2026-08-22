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

/// Mensagem recebida, como o `inbox --json` devolve.
struct InboxMessage: Identifiable, Decodable, Equatable {
    let uid: String
    var from: String
    var to: String?
    var subject: String
    var date: String
    var unread: Bool?
    var body: String?

    var id: String { uid }
    var sender: String {
        // "Nome <e@mail>" fica melhor como só o nome na lista
        guard let abre = from.firstIndex(of: "<"), abre != from.startIndex else { return from }
        let nome = from[from.startIndex..<abre].trimmingCharacters(
            in: CharacterSet(charactersIn: " \"'"))
        return nome.isEmpty ? from : nome
    }
}

/// Uma linha do histórico de envios.
struct SentItem: Identifiable, Decodable, Equatable {
    let id: String
    var ts: String
    var status: String
    var to: [String]
    var subject: String
    var body: String?
    var error: String?
    var agent: String?
}

/// Um fato que o agente aprendeu sobre o dono.
struct Fact: Identifiable, Decodable, Equatable {
    let key: String
    var label: String
    var value: String
    var category: String
    var source: String?
    var sensitive: Bool?
    var updated: String?

    var id: String { key }
}

struct MemoryPayload: Decodable {
    var facts: [Fact]
    var notes: String?
}

/// O que o agente fez com cada mensagem que chegou.
struct WatchEntry: Identifiable, Decodable, Equatable {
    var message_id: String?
    var uid: String?
    var from: String?
    var subject: String?
    var action: String
    var reason: String?
    var confidence: Double?
    var ts: String?

    var id: String { (message_id ?? uid ?? "") + (ts ?? "") }
}

/// Conta configurada, como o app precisa dela.
struct MailboxSummary: Equatable {
    var name: String = ""
    var address: String = ""
    var username: String = ""
    var provider: String = ""
    var mode: String = "confirm"
    var identity: String = "ia"
    var ownerName: String = ""
    var scope: String = "alias"
    var brain: String = "claude-cli"
    var dailyLimit: Int = 25
    var allowlist: [String] = []
    var hasSecret: Bool = false
    var configured: Bool = false
}
