import Foundation
import SwiftUI

/// Estado do app. Lê a fila pelo próprio CLI e age chamando os mesmos comandos
/// que uma pessoa digitaria — assim app e terminal nunca discordam sobre o que
/// aconteceu, e o registro sai igual nos dois caminhos.
@MainActor
final class Store: ObservableObject {
    /// Um estado só para o app inteiro: a janela e o painel da barra mostram a
    /// mesma fila, e um refresh serve aos dois.
    static let shared = Store()

    @Published var emails: [PendingEmail] = []
    @Published var questions: [Question] = []
    @Published var mailbox = MailboxSummary()
    @Published var errorText: String?
    @Published var busy = false

    private var timer: Timer?

    var waitingCount: Int { emails.count + questions.count }

    /// Onde o binário pode estar: dentro do bundle (instalado pelo Homebrew),
    /// no PATH do usuário, ou no clone de quem está desenvolvendo.
    static func cliPath() -> String? {
        var candidates: [String] = []
        if let resources = Bundle.main.resourceURL {
            candidates.append(resources.appendingPathComponent("mailforai/bin/mailforai").path)
        }
        let home = FileManager.default.homeDirectoryForCurrentUser.path
        candidates += [
            "\(home)/.local/bin/mailforai",
            "/opt/homebrew/bin/mailforai",
            "/usr/local/bin/mailforai",
            "\(home)/Documents/Claude/Projetos/MailForAI/bin/mailforai",
        ]
        return candidates.first { FileManager.default.isExecutableFile(atPath: $0) }
    }

    func start() {
        guard timer == nil else { return }
        refresh()
        timer = Timer.scheduledTimer(withTimeInterval: 3.0, repeats: true) { [weak self] _ in
            Task { @MainActor in self?.refresh() }
        }
    }

    func stop() {
        timer?.invalidate()
        timer = nil
    }

    // MARK: - leitura

    func refresh() {
        guard !busy else { return }
        guard let cli = Store.cliPath() else {
            errorText = S.cliMissing
            return
        }
        Task.detached(priority: .utility) {
            let pending = Self.run(cli, ["pending", "--json"])
            let accounts = Self.run(cli, ["accounts", "--json"])
            await MainActor.run {
                self.apply(pendingJSON: pending.out, accountsJSON: accounts.out,
                           failure: pending.status == 0 ? nil : pending.err)
            }
        }
    }

    private func apply(pendingJSON: String, accountsJSON: String, failure: String?) {
        if let failure, !failure.isEmpty {
            // sem caixa configurada não é erro do app: é o primeiro uso
            errorText = failure.contains("setup") ? S.noMailbox : failure
            emails = []; questions = []
            return
        }
        errorText = nil
        if let data = pendingJSON.data(using: .utf8),
           let payload = try? JSONDecoder().decode(PendingPayload.self, from: data) {
            emails = payload.pending.filter { ($0.status ?? "pending") == "pending" }
            questions = payload.questions.filter { ($0.status ?? "open") == "open" }
        }
        if let data = accountsJSON.data(using: .utf8),
           let root = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
           let accounts = root["accounts"] as? [String: Any],
           let name = root["default"] as? String,
           let account = accounts[name] as? [String: Any] {
            var resumo = MailboxSummary()
            resumo.name = name
            resumo.address = account["address"] as? String ?? ""
            resumo.mode = (account["approval"] as? [String: Any])?["mode"] as? String ?? "confirm"
            resumo.identity = (account["identity"] as? [String: Any])?["mode"] as? String ?? "ia"
            mailbox = resumo
        }
    }

    // MARK: - ações

    func approve(_ email: PendingEmail) { act(["approve", email.id, "--by", "app"]) }

    func reject(_ email: PendingEmail, note: String) {
        var args = ["reject", email.id, "--by", "app"]
        if !note.trimmingCharacters(in: .whitespaces).isEmpty { args += ["--note", note] }
        act(args)
    }

    func answer(_ question: Question, text: String) {
        let limpo = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !limpo.isEmpty else { return }
        act(["answer", question.id, limpo])
    }

    func setMode(_ mode: String) { act(["mode", mode]) }

    func openHistory() {
        guard let cli = Store.cliPath() else { return }
        // `serve` fica em primeiro plano servindo a página: soltar e não esperar
        let process = Process()
        process.executableURL = URL(fileURLWithPath: cli)
        process.arguments = ["serve"]
        try? process.run()
    }

    private func act(_ args: [String]) {
        guard let cli = Store.cliPath() else { return }
        busy = true
        Task.detached(priority: .userInitiated) {
            let resultado = Self.run(cli, args)
            await MainActor.run {
                self.busy = false
                if resultado.status != 0, !resultado.err.isEmpty { self.errorText = resultado.err }
                self.refresh()
            }
        }
    }

    // MARK: - processo

    nonisolated static func run(_ cli: String, _ args: [String]) -> (out: String, err: String, status: Int32) {
        let process = Process()
        process.executableURL = URL(fileURLWithPath: cli)
        process.arguments = args
        let out = Pipe(), err = Pipe()
        process.standardOutput = out
        process.standardError = err
        do {
            try process.run()
        } catch {
            return ("", error.localizedDescription, 1)
        }
        let saida = out.fileHandleForReading.readDataToEndOfFile()
        let erro = err.fileHandleForReading.readDataToEndOfFile()
        process.waitUntilExit()
        return (String(data: saida, encoding: .utf8) ?? "",
                String(data: erro, encoding: .utf8) ?? "",
                process.terminationStatus)
    }
}
