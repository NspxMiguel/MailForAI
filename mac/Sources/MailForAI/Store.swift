import Foundation
import ServiceManagement
import SwiftUI

enum Secao: String, CaseIterable, Identifiable {
    case entrada, fila, enviados, memoria, ajustes
    var id: String { rawValue }
}

/// Estado do app. Lê e age pelo próprio CLI, chamando os mesmos comandos que
/// uma pessoa digitaria — assim app e terminal nunca discordam sobre o que
/// aconteceu, e o registro sai igual pelos dois caminhos.
@MainActor
final class Store: ObservableObject {
    /// Um estado só para o app inteiro: a janela e o painel da barra mostram a
    /// mesma fila, e um refresh serve aos dois.
    static let shared = Store()

    @Published var secao: Secao = .fila
    @Published var emails: [PendingEmail] = []
    @Published var questions: [Question] = []
    @Published var inbox: [InboxMessage] = []
    @Published var sent: [SentItem] = []
    @Published var facts: [Fact] = []
    @Published var notes: String = ""
    @Published var watchLog: [WatchEntry] = []
    @Published var mailbox = MailboxSummary()
    @Published var errorText: String?
    @Published var statusText: String?
    @Published var busy = false
    @Published var carregandoEntrada = false
    @Published var vigiaLigado = false
    @Published var vigiaIntervalo = 300
    @Published var hookInstalado = false
    @Published var ligadoAoClaude = false
    @Published var ultimaVarredura: Date?

    private var timer: Timer?
    private var timerVigia: Timer?

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
        conferirIntegracoes()
        timer = Timer.scheduledTimer(withTimeInterval: 4.0, repeats: true) { [weak self] _ in
            Task { @MainActor in self?.refresh() }
        }
    }

    func stop() {
        timer?.invalidate()
        timer = nil
        timerVigia?.invalidate()
        timerVigia = nil
    }

    /// O vigia é o que faz a caixa funcionar sem ninguém olhando: de tempos em
    /// tempos lê o que chegou e deixa o agente decidir. Só roda com o app
    /// aberto — é o mesmo trato de qualquer cliente de e-mail.
    func aplicarVigia() {
        timerVigia?.invalidate()
        timerVigia = nil
        guard vigiaLigado else { return }
        let intervalo = Double(max(60, vigiaIntervalo))
        timerVigia = Timer.scheduledTimer(withTimeInterval: intervalo, repeats: true) { [weak self] _ in
            Task { @MainActor in self?.varrerAgora(silencioso: true) }
        }
        varrerAgora(silencioso: true)
    }

    func ligarVigia(_ ligado: Bool) {
        vigiaLigado = ligado
        act(["scope", "--enable-watch", ligado ? "sim" : "nao"])
        aplicarVigia()
    }

    func mudarIntervalo(_ segundos: Int) {
        vigiaIntervalo = segundos
        act(["scope", "--interval", String(segundos)])
        aplicarVigia()
    }

    func responder(uid: String, corpo: String, completo: @escaping (String) -> Void) {
        guard let cli = Store.cliPath() else { return }
        busy = true
        Task.detached(priority: .userInitiated) {
            let r = Self.run(cli, ["reply", uid, "--body", corpo, "--agent", "app", "--json"])
            await MainActor.run {
                self.busy = false
                completo(r.status == 0 ? r.out : r.err)
                self.refresh()
            }
        }
    }

    func instalarHook(_ ligar: Bool) {
        act(ligar ? ["hook"] : ["hook", "--remove"])
        conferirIntegracoes()
    }

    func conectarClaude(_ ligar: Bool) {
        act(ligar ? ["connect"] : ["connect", "--remove"])
        conferirIntegracoes()
    }

    /// Abrir junto com o Mac. Sem isto, "ler sozinho" depende de alguém lembrar
    /// de abrir o app — que é justamente o que ninguém faz.
    var abreNoLogin: Bool {
        if #available(macOS 13.0, *) { return SMAppService.mainApp.status == .enabled }
        return false
    }

    func definirAbrirNoLogin(_ ligar: Bool) {
        guard #available(macOS 13.0, *) else { return }
        do {
            if ligar {
                try SMAppService.mainApp.register()
            } else {
                try SMAppService.mainApp.unregister()
            }
            objectWillChange.send()
        } catch {
            errorText = error.localizedDescription
        }
    }

    func definirTeto(_ valor: Int) { act(["limit", String(valor)]) }

    func conferirIntegracoes() {
        guard let cli = Store.cliPath() else { return }
        Task.detached(priority: .utility) {
            let hook = Self.run(cli, ["hook", "--status", "--json"])
            let mcp = Self.run(cli, ["connect", "--status", "--json"])
            let lerBool = { (texto: String, chave: String) -> Bool in
                guard let dados = texto.data(using: .utf8),
                      let obj = try? JSONSerialization.jsonObject(with: dados) as? [String: Any]
                else { return false }
                return obj[chave] as? Bool ?? false
            }
            await MainActor.run {
                self.hookInstalado = lerBool(hook.out, "installed")
                self.ligadoAoClaude = lerBool(mcp.out, "connected")
            }
        }
    }

    // MARK: - leitura

    /// O que é barato e vale reler sempre: fila, conta, memória, histórico.
    /// A caixa de entrada fica de fora — ela é uma ida à rede, e só recarrega
    /// quando o usuário está olhando para ela ou pede.
    func refresh() {
        guard !busy, let cli = Store.cliPath() else {
            if Store.cliPath() == nil { errorText = S.cliMissing }
            return
        }
        Task.detached(priority: .utility) {
            let pending = Self.run(cli, ["pending", "--json"])
            let accounts = Self.run(cli, ["accounts", "--json"])
            let mem = Self.run(cli, ["memory", "--json"])
            let hist = Self.run(cli, ["history", "--json", "-n", "60"])
            await MainActor.run {
                self.aplicar(pending: pending, accounts: accounts, memory: mem, history: hist)
            }
        }
    }

    private func aplicar(pending: Saida, accounts: Saida, memory: Saida, history: Saida) {
        if pending.status != 0, !pending.err.isEmpty {
            // sem caixa configurada não é erro do app: é o primeiro uso
            errorText = pending.err.contains("setup") ? nil : pending.err
            mailbox.configured = false
            emails = []; questions = []
            return
        }
        errorText = nil
        if let dados = pending.out.data(using: .utf8),
           let carga = try? JSONDecoder().decode(PendingPayload.self, from: dados) {
            emails = carga.pending.filter { ($0.status ?? "pending") == "pending" }
            questions = carga.questions.filter { ($0.status ?? "open") == "open" }
        }
        if let dados = memory.out.data(using: .utf8),
           let carga = try? JSONDecoder().decode(MemoryPayload.self, from: dados) {
            facts = carga.facts
            if notes != carga.notes ?? "" { notes = carga.notes ?? "" }
        }
        if let dados = history.out.data(using: .utf8),
           let itens = try? JSONDecoder().decode([SentItem].self, from: dados) {
            sent = itens
        }
        aplicarConta(accounts.out)
    }

    private func aplicarConta(_ json: String) {
        guard let dados = json.data(using: .utf8),
              let raiz = try? JSONSerialization.jsonObject(with: dados) as? [String: Any],
              let contas = raiz["accounts"] as? [String: Any],
              let nome = raiz["default"] as? String,
              let conta = contas[nome] as? [String: Any] else {
            mailbox.configured = false
            return
        }
        var resumo = MailboxSummary()
        resumo.name = nome
        resumo.configured = true
        resumo.address = conta["address"] as? String ?? ""
        resumo.username = conta["username"] as? String ?? ""
        resumo.provider = conta["provider"] as? String ?? ""
        resumo.mode = (conta["approval"] as? [String: Any])?["mode"] as? String ?? "confirm"
        let ident = conta["identity"] as? [String: Any]
        resumo.identity = ident?["mode"] as? String ?? "ia"
        resumo.ownerName = ident?["owner_name"] as? String ?? ""
        let vigia = conta["watch"] as? [String: Any]
        resumo.scope = vigia?["scope"] as? String ?? "alias"
        resumo.brain = (conta["brain"] as? [String: Any])?["backend"] as? String ?? "claude-cli"
        let guarda = conta["guard"] as? [String: Any]
        resumo.dailyLimit = guarda?["daily_limit"] as? Int ?? 25
        resumo.allowlist = guarda?["allowlist"] as? [String] ?? []
        resumo.hasSecret = mailbox.hasSecret || resumo.hasSecret
        mailbox = resumo

        let ligado = vigia?["enabled"] as? Bool ?? false
        let intervalo = vigia?["interval"] as? Int ?? 300
        if ligado != vigiaLigado || intervalo != vigiaIntervalo {
            vigiaLigado = ligado
            vigiaIntervalo = intervalo
            aplicarVigia()
        }
    }

    func carregarEntrada(force: Bool = false) {
        guard let cli = Store.cliPath(), !carregandoEntrada else { return }
        guard force || inbox.isEmpty else { return }
        carregandoEntrada = true
        Task.detached(priority: .userInitiated) {
            let resultado = Self.run(cli, ["inbox", "--json", "-n", "25"])
            let vigia = Self.run(cli, ["watch", "--json", "--dry-run"])
            await MainActor.run {
                self.carregandoEntrada = false
                if resultado.status == 0, let dados = resultado.out.data(using: .utf8),
                   let itens = try? JSONDecoder().decode([InboxMessage].self, from: dados) {
                    self.inbox = itens
                    self.errorText = nil
                } else if !resultado.err.isEmpty {
                    self.errorText = resultado.err
                }
                if let dados = vigia.out.data(using: .utf8),
                   let itens = try? JSONDecoder().decode([WatchEntry].self, from: dados) {
                    self.watchLog = itens
                }
            }
        }
    }

    func corpo(de mensagem: InboxMessage, completo: @escaping (String) -> Void) {
        guard let cli = Store.cliPath() else { return }
        Task.detached(priority: .userInitiated) {
            let r = Self.run(cli, ["read", mensagem.uid, "--json", "--keep-unread"])
            let texto: String
            if let dados = r.out.data(using: .utf8),
               let obj = try? JSONSerialization.jsonObject(with: dados) as? [String: Any] {
                texto = obj["body"] as? String ?? ""
            } else {
                texto = r.err
            }
            await MainActor.run { completo(texto) }
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
    func setScope(_ scope: String) { act(["scope", scope]) }
    func setBrain(_ backend: String) { act(["brain", backend]) }
    func setIdentity(_ mode: String) { act(["identity", mode]) }

    func esquecer(_ fato: Fact) { act(["memory", "--forget", fato.key]) }

    func lembrar(rotulo: String, valor: String, categoria: String) {
        guard !rotulo.isEmpty, !valor.isEmpty else { return }
        act(["memory", "--add", rotulo, valor, "--category", categoria])
    }

    func salvarNotas(_ texto: String) { act(["memory", "--notes", texto]) }

    func enviar(para: String, assunto: String, corpo: String, completo: @escaping (String) -> Void) {
        guard let cli = Store.cliPath() else { return }
        busy = true
        Task.detached(priority: .userInitiated) {
            let r = Self.run(cli, ["send", "-t", para, "-s", assunto, "-b", corpo,
                                   "--agent", "app", "--reason", S.writtenInApp])
            await MainActor.run {
                self.busy = false
                completo(r.status == 0 ? r.out.trimmingCharacters(in: .whitespacesAndNewlines)
                                       : r.err.trimmingCharacters(in: .whitespacesAndNewlines))
                self.refresh()
            }
        }
    }

    /// Uma varredura agora: lê o que chegou e deixa o agente agir.
    func varrerAgora(silencioso: Bool = false) {
        guard let cli = Store.cliPath(), !busy else { return }
        busy = true
        if !silencioso { statusText = S.checking }
        Task.detached(priority: .userInitiated) {
            let r = Self.run(cli, ["watch", "--once", "--json"])
            await MainActor.run {
                self.busy = false
                self.ultimaVarredura = Date()
                self.statusText = r.status == 0 ? nil : r.err
                self.carregarEntrada(force: true)
                self.refresh()
            }
        }
    }

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

    typealias Saida = (out: String, err: String, status: Int32)

    nonisolated static func run(_ cli: String, _ args: [String], stdin: String? = nil) -> Saida {
        let process = Process()
        process.executableURL = URL(fileURLWithPath: cli)
        process.arguments = args
        let out = Pipe(), err = Pipe()
        process.standardOutput = out
        process.standardError = err
        if stdin != nil {
            process.standardInput = Pipe()
        }
        do {
            try process.run()
        } catch {
            return ("", error.localizedDescription, 1)
        }
        if let stdin, let entrada = process.standardInput as? Pipe {
            entrada.fileHandleForWriting.write(Data(stdin.utf8))
            entrada.fileHandleForWriting.closeFile()
        }
        let saida = out.fileHandleForReading.readDataToEndOfFile()
        let erro = err.fileHandleForReading.readDataToEndOfFile()
        process.waitUntilExit()
        return (String(data: saida, encoding: .utf8) ?? "",
                String(data: erro, encoding: .utf8) ?? "",
                process.terminationStatus)
    }
}
