import SwiftUI

/// Tudo que dá para mudar sem abrir o terminal.
struct SettingsView: View {
    @ObservedObject var store: Store
    @State private var confirmarAuto = false
    @State private var confirmarEscopoTotal = false
    @State private var trocandoSenha = false
    @State private var senhaNova = ""
    @State private var mensagemSenha: String?
    @State private var novoPermitido = ""

    var body: some View {
        VStack(spacing: 0) {
            Cabecalho(titulo: S.sectionSettings, descricao: S.settingsHelp) {
                Button(S.testLogin) { testar() }
            }
            Divider()
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    conta
                    automatico
                    envio
                    leitura
                    identidade
                    cerebro
                    permitidos
                    integracoes
                    diagnostico
                }
                .padding(16)
            }
        }
    }

    // MARK: - blocos

    private var conta: some View {
        bloco(S.settingsAccount) {
            linha(S.address, store.mailbox.address)
            linha(S.username, store.mailbox.username)
            linha(S.provider, store.mailbox.provider)
            HStack {
                Button(S.changePassword) { trocandoSenha.toggle() }
                if let mensagemSenha {
                    Text(mensagemSenha).font(.caption).foregroundStyle(.secondary)
                }
            }
            if trocandoSenha {
                HStack {
                    SecureField(S.newPassword, text: $senhaNova).textFieldStyle(.roundedBorder)
                    Button(S.save) { gravarSenha() }.disabled(senhaNova.isEmpty)
                }
                Text(S.passwordGoesToKeychain).font(.caption2).foregroundStyle(.secondary)
            }
        }
    }

    /// Sem isto o agente só age quando alguém clica — e a caixa que "funciona
    /// sozinha" some no primeiro dia em que ninguém abre o app.
    private var automatico: some View {
        bloco(S.settingsAuto) {
            Toggle(S.serviceOn, isOn: Binding(
                get: { store.servicoLigado },
                set: { store.ligarServico($0) }))
            Text(S.serviceHelp).font(.caption2).foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)
            Divider()
            Toggle(S.autoWatch, isOn: Binding(
                get: { store.vigiaLigado },
                set: { store.ligarVigia($0) }))
            Picker(S.autoEvery, selection: Binding(
                get: { store.vigiaIntervalo },
                set: { store.mudarIntervalo($0) })) {
                Text(S.every1min).tag(60)
                Text(S.every5min).tag(300)
                Text(S.every15min).tag(900)
                Text(S.every1hour).tag(3600)
            }
            .frame(maxWidth: 260)
            .disabled(!store.vigiaLigado)
            if let ultima = store.ultimaVarredura {
                Text(S.lastCheck + ": " + ultima.formatted(date: .omitted, time: .shortened))
                    .font(.caption2).foregroundStyle(.secondary)
            }
            Text(S.autoWatchHelp).font(.caption2).foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)
            Divider()
            Toggle(S.openAtLogin, isOn: Binding(
                get: { store.abreNoLogin },
                set: { store.definirAbrirNoLogin($0) }))
            Text(S.openAtLoginHelp).font(.caption2).foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    private var diagnostico: some View {
        bloco(S.settingsCheck) {
            HStack {
                Button(S.runSelfTest) { store.rodarAutoteste() }
                    .disabled(store.testando)
                if store.testando { ProgressView().controlSize(.small) }
            }
            Text(S.selfTestHelp).font(.caption2).foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)
            if let saida = store.testeSaida {
                ScrollView {
                    Text(saida)
                        .font(.system(size: 11, design: .monospaced))
                        .textSelection(.enabled)
                        .frame(maxWidth: .infinity, alignment: .leading)
                }
                .frame(maxHeight: 160)
                .padding(8)
                .background(RoundedRectangle(cornerRadius: 6).fill(Color.primary.opacity(0.06)))
            }
        }
    }

    private var integracoes: some View {
        bloco(S.settingsIntegrations) {
            Toggle(S.integrationHook, isOn: Binding(
                get: { store.hookInstalado },
                set: { store.instalarHook($0) }))
            Text(S.integrationHookHelp).font(.caption2).foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)
            Divider()
            Toggle(S.integrationMCP, isOn: Binding(
                get: { store.ligadoAoClaude },
                set: { store.conectarClaude($0) }))
            Text(S.integrationMCPHelp).font(.caption2).foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    private var envio: some View {
        bloco(S.settingsSending) {
            Picker(S.modeTitle, selection: Binding(
                get: { store.mailbox.mode },
                // ligar o automático desarma a única trava que segura um envio:
                // vale um clique a mais. Voltar para confirm é sempre direto.
                set: { novo in
                    if novo == "auto" { confirmarAuto = true } else { store.setMode(novo) }
                })) {
                Text(S.modeConfirm).tag("confirm")
                Text(S.modeAuto).tag("auto")
            }
            .pickerStyle(.radioGroup)
            .alert(S.autoTitle, isPresented: $confirmarAuto) {
                Button(S.cancel, role: .cancel) { }
                Button(S.autoConfirm) { store.setMode("auto") }
            } message: { Text(S.autoBody) }

            Stepper(value: Binding(
                get: { store.mailbox.dailyLimit },
                set: { store.definirTeto($0) }), in: 0...500, step: 5) {
                Text(S.dailyCap + ": " + (store.mailbox.dailyLimit == 0
                                          ? S.noCap : "\(store.mailbox.dailyLimit)"))
                    .font(.caption)
            }
            .frame(maxWidth: 260)
        }
    }

    private var leitura: some View {
        bloco(S.settingsReading) {
            Picker(S.scopeTitle, selection: Binding(
                get: { store.mailbox.scope },
                set: { novo in
                    if novo == "all" { confirmarEscopoTotal = true } else { store.setScope(novo) }
                })) {
                Text(S.scopeAlias).tag("alias")
                Text(S.scopeAll).tag("all")
            }
            .pickerStyle(.radioGroup)
            .alert(S.scopeAllTitle, isPresented: $confirmarEscopoTotal) {
                Button(S.cancel, role: .cancel) { }
                Button(S.scopeAllConfirm) { store.setScope("all") }
            } message: { Text(S.scopeAllBody) }

            Text(S.scopeHelp).font(.caption2).foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    private var identidade: some View {
        bloco(S.settingsIdentity) {
            Picker(S.identityTitle, selection: Binding(
                get: { store.mailbox.identity },
                set: { store.setIdentity($0) })) {
                Text(S.identityAI).tag("ia")
                Text(S.identityAssistant).tag("assistente")
                Text(S.identityOwner).tag("dono")
            }
            .pickerStyle(.radioGroup)
            Text(S.identityHelp).font(.caption2).foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    private var cerebro: some View {
        bloco(S.settingsBrain) {
            Picker(S.brainTitle, selection: Binding(
                get: { store.mailbox.brain },
                set: { store.setBrain($0) })) {
                Text("claude (CLI)").tag("claude-cli")
                Text("Anthropic API").tag("anthropic")
                Text("Groq").tag("groq")
                Text("Gemini").tag("gemini")
            }
            .frame(maxWidth: 260)
            Text(S.brainHelp).font(.caption2).foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    private var permitidos: some View {
        bloco(S.settingsAllowlist) {
            if store.mailbox.allowlist.isEmpty {
                Text(S.allowlistEmpty).font(.caption).foregroundStyle(.secondary)
            } else {
                ForEach(store.mailbox.allowlist, id: \.self) { padrao in
                    Text("• " + padrao).font(.system(size: 12))
                }
            }
            HStack {
                TextField("*@nintendo.com", text: $novoPermitido).textFieldStyle(.roundedBorder)
                Button(S.add) {
                    guard let cli = Store.cliPath(), !novoPermitido.isEmpty else { return }
                    _ = Store.run(cli, ["allow", novoPermitido])
                    novoPermitido = ""
                    store.refresh()
                }
                .disabled(novoPermitido.isEmpty)
            }
            Text(S.allowlistHelp).font(.caption2).foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    // MARK: - peças

    private func bloco<Conteudo: View>(_ titulo: String,
                                       @ViewBuilder conteudo: () -> Conteudo) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(titulo.uppercased()).font(.caption2).fontWeight(.semibold)
                .foregroundStyle(.secondary)
            conteudo()
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(12)
        .background(RoundedRectangle(cornerRadius: 8).fill(Color.primary.opacity(0.05)))
    }

    private func linha(_ rotulo: String, _ valor: String) -> some View {
        HStack {
            Text(rotulo).font(.caption).foregroundStyle(.secondary)
            Spacer()
            Text(valor).font(.system(size: 12)).textSelection(.enabled)
        }
    }

    private func gravarSenha() {
        guard let cli = Store.cliPath() else { return }
        let senha = senhaNova
        // o nome da conta é lido aqui, no MainActor: dentro da tarefa detached
        // seria acesso a estado isolado de outro ator
        let conta = store.mailbox.name
        senhaNova = ""
        mensagemSenha = S.saving
        Task.detached(priority: .userInitiated) {
            _ = Store.run(cli, ["secret", conta, "--stdin"], stdin: senha)
            let teste = Store.run(cli, ["doctor", "--fix", "--json"])
            await MainActor.run {
                trocandoSenha = false
                mensagemSenha = teste.status == 0 ? S.setupWorked
                    : SetupWizardView.explicar(teste.out + teste.err)
            }
        }
    }

    private func testar() {
        guard let cli = Store.cliPath() else { return }
        mensagemSenha = S.testing
        Task.detached(priority: .userInitiated) {
            let teste = Store.run(cli, ["doctor", "--fix", "--json"])
            await MainActor.run {
                mensagemSenha = teste.status == 0 ? S.setupWorked
                    : SetupWizardView.explicar(teste.out + teste.err)
            }
        }
    }
}
