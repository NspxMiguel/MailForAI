import SwiftUI

/// Provedores que o assistente sabe configurar, com o passo a passo de cada um.
///
/// A instrução importa mais que o formulário: quem trava não é no campo de
/// host, é em descobrir onde o provedor esconde a senha de aplicativo.
struct Provedor: Identifiable {
    let id: String
    let nome: String
    let dominios: [String]
    let usuarioEhContaPrincipal: Bool
    let paginaSenha: String
    let passos: [String]
    let aviso: String?
}

let PROVEDORES: [Provedor] = [
    Provedor(
        id: "icloud", nome: "iCloud / Apple Mail",
        dominios: ["icloud.com", "me.com", "mac.com"],
        usuarioEhContaPrincipal: true,
        paginaSenha: "https://account.apple.com",
        passos: [
            S.t("Abra account.apple.com e entre com o seu Apple ID.",
                "Open account.apple.com and sign in with your Apple ID."),
            S.t("Vá em Segurança (ou \"Sign-In and Security\") → Senhas de app.",
                "Go to Sign-In and Security → App-Specific Passwords."),
            S.t("Toque em + , dê o nome \"MailForAI\" e confirme.",
                "Tap +, name it \"MailForAI\" and confirm."),
            S.t("Copie a senha de 16 letras que aparecer e cole aqui embaixo.",
                "Copy the 16-character password shown and paste it below."),
            S.t("No campo \"usuário\", use o seu Apple ID inteiro — não o endereço do agente.",
                "In the username field, use your full Apple ID — not the agent's address."),
        ],
        aviso: S.t(
            "No iCloud, um endereço de domínio próprio é apelido: ele cai na mesma caixa do seu "
            + "e-mail pessoal, e a senha de aplicativo abre essa caixa inteira. Por isso o "
            + "MailForAI já vem com o escopo limitado ao endereço do agente. Para separação de "
            + "verdade, hospede o e-mail do agente em outro provedor.",
            "On iCloud a custom-domain address is an alias: it lands in the same mailbox as your "
            + "personal mail, and an app-specific password opens that whole mailbox. MailForAI "
            + "therefore limits its scope to the agent's address by default. For real separation, "
            + "host the agent's mailbox elsewhere.")),
    Provedor(
        id: "gmail", nome: "Gmail / Google Workspace",
        dominios: ["gmail.com", "googlemail.com"],
        usuarioEhContaPrincipal: false,
        paginaSenha: "https://myaccount.google.com/apppasswords",
        passos: [
            S.t("A verificação em duas etapas precisa estar ligada na conta.",
                "Two-step verification must be on for the account."),
            S.t("Abra myaccount.google.com/apppasswords.",
                "Open myaccount.google.com/apppasswords."),
            S.t("Dê o nome \"MailForAI\" e clique em Criar.",
                "Name it \"MailForAI\" and click Create."),
            S.t("Copie a senha de 16 letras (sem espaços) e cole aqui embaixo.",
                "Copy the 16-character password (no spaces) and paste it below."),
        ],
        aviso: S.t(
            "Uma conta do Gmail só para o agente é a forma mais simples de separação: ela não "
            + "toca a sua conta pessoal, e você a apaga quando quiser.",
            "A Gmail account dedicated to the agent is the simplest real separation: it never "
            + "touches your personal account, and you can delete it whenever you want.")),
    Provedor(
        id: "fastmail", nome: "Fastmail", dominios: ["fastmail.com", "fastmail.fm"],
        usuarioEhContaPrincipal: false,
        paginaSenha: "https://app.fastmail.com/settings/security/apps",
        passos: [
            S.t("Abra Configurações → Privacidade e Segurança → Senhas de app.",
                "Open Settings → Privacy & Security → App Passwords."),
            S.t("Crie uma senha nova com acesso a IMAP e SMTP.",
                "Create a new password with IMAP and SMTP access."),
            S.t("Cole a senha aqui embaixo.", "Paste the password below."),
        ], aviso: nil),
    Provedor(
        id: "zoho", nome: "Zoho Mail", dominios: ["zoho.com"],
        usuarioEhContaPrincipal: false,
        paginaSenha: "https://accounts.zoho.com",
        passos: [
            S.t("IMAP e SMTP exigem um plano pago (Mail Lite) — o gratuito não tem.",
                "IMAP and SMTP need a paid plan (Mail Lite) — the free tier has neither."),
            S.t("Em accounts.zoho.com → Segurança → Senhas específicas de app, crie uma.",
                "At accounts.zoho.com → Security → App Passwords, create one."),
            S.t("Cole a senha aqui embaixo.", "Paste the password below."),
        ], aviso: nil),
    Provedor(
        id: "outlook", nome: "Outlook / Microsoft 365", dominios: ["outlook.com", "hotmail.com", "live.com"],
        usuarioEhContaPrincipal: false,
        paginaSenha: "https://account.microsoft.com/security",
        passos: [
            S.t("A verificação em duas etapas precisa estar ligada.",
                "Two-step verification must be on."),
            S.t("Em Segurança → Opções avançadas, crie uma senha de app.",
                "Under Security → Advanced options, create an app password."),
            S.t("Cole a senha aqui embaixo.", "Paste the password below."),
        ], aviso: nil),
    Provedor(
        id: "migadu", nome: "Migadu", dominios: [], usuarioEhContaPrincipal: false,
        paginaSenha: "https://admin.migadu.com",
        passos: [
            S.t("No admin da Migadu, crie a caixa do agente no seu domínio.",
                "In the Migadu admin, create the agent's mailbox on your domain."),
            S.t("Defina a senha dela e cole aqui embaixo.",
                "Set its password and paste it below."),
        ], aviso: nil),
    Provedor(
        id: "custom", nome: S.t("Outro servidor", "Another server"), dominios: [],
        usuarioEhContaPrincipal: false, paginaSenha: "",
        passos: [
            S.t("Informe o host de SMTP e o de IMAP do seu provedor.",
                "Enter your provider's SMTP and IMAP hosts."),
            S.t("Use a senha da caixa (ou a senha de app, se o provedor tiver).",
                "Use the mailbox password (or an app password, if the provider has one)."),
        ], aviso: nil),
]

/// Configuração pela interface: escolher o provedor, seguir o passo a passo,
/// colar a senha e testar. Nenhum comando de terminal no caminho.
struct SetupWizardView: View {
    @ObservedObject var store: Store

    @State private var passo = 0
    @State private var provedorID = "icloud"
    @State private var endereco = ""
    @State private var usuario = ""
    @State private var dono = ""
    @State private var apelido = "Claude"
    @State private var senha = ""
    @State private var smtpHost = ""
    @State private var imapHost = ""
    @State private var testando = false
    @State private var resultado: String?
    @State private var deuCerto = false

    private var provedor: Provedor {
        PROVEDORES.first { $0.id == provedorID } ?? PROVEDORES[0]
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                cabecalho
                switch passo {
                case 0: passoEndereco
                case 1: passoSenha
                default: passoPronto
                }
            }
            .padding(22)
            .frame(maxWidth: 620, alignment: .leading)
        }
        .frame(maxWidth: .infinity)
    }

    private var cabecalho: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(S.setupTitle).font(.title2).fontWeight(.semibold)
            Text(S.setupSubtitle).font(.callout).foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)
            HStack(spacing: 6) {
                ForEach(0..<3) { indice in
                    Capsule()
                        .fill(indice <= passo ? Color.accentColor : Color.secondary.opacity(0.25))
                        .frame(height: 3)
                }
            }
            .padding(.top, 6)
        }
    }

    private var passoEndereco: some View {
        VStack(alignment: .leading, spacing: 12) {
            campo(S.setupAddress, S.setupAddressHelp) {
                TextField("claude@seudominio.dev", text: $endereco)
                    .textFieldStyle(.roundedBorder)
                    .onChange(of: endereco) { novo in
                        if let achado = PROVEDORES.first(where: { prov in
                            prov.dominios.contains(where: { novo.lowercased().hasSuffix("@" + $0) })
                        }) {
                            provedorID = achado.id
                        }
                    }
            }
            campo(S.setupProvider, S.setupProviderHelp) {
                Picker("", selection: $provedorID) {
                    ForEach(PROVEDORES) { Text($0.nome).tag($0.id) }
                }
                .labelsHidden()
            }
            if provedorID == "custom" {
                HStack {
                    TextField("smtp.exemplo.com", text: $smtpHost).textFieldStyle(.roundedBorder)
                    TextField("imap.exemplo.com", text: $imapHost).textFieldStyle(.roundedBorder)
                }
            }
            campo(S.setupOwner, S.setupOwnerHelp) {
                TextField("Miguel", text: $dono).textFieldStyle(.roundedBorder)
            }
            campo(S.setupAgentName, S.setupAgentNameHelp) {
                TextField("Claude", text: $apelido).textFieldStyle(.roundedBorder)
            }
            if let aviso = provedor.aviso {
                caixaAviso(aviso)
            }
            HStack {
                Spacer()
                Button(S.next) {
                    usuario = provedor.usuarioEhContaPrincipal ? "" : endereco
                    passo = 1
                }
                .buttonStyle(.borderedProminent)
                .disabled(!endereco.contains("@") || dono.isEmpty)
            }
        }
    }

    private var passoSenha: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(S.setupPasswordTitle).font(.headline)
            Text(S.setupPasswordWhy).font(.caption).foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)

            VStack(alignment: .leading, spacing: 7) {
                ForEach(Array(provedor.passos.enumerated()), id: \.offset) { indice, texto in
                    HStack(alignment: .top, spacing: 8) {
                        Text("\(indice + 1)")
                            .font(.caption).fontWeight(.bold)
                            .frame(width: 18, height: 18)
                            .background(Circle().fill(Color.accentColor.opacity(0.18)))
                        Text(texto).font(.callout)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                }
            }
            .padding(12)
            .background(RoundedRectangle(cornerRadius: 8).fill(Color.primary.opacity(0.05)))

            if !provedor.paginaSenha.isEmpty {
                Button(S.setupOpenPage) {
                    if let url = URL(string: provedor.paginaSenha) { NSWorkspace.shared.open(url) }
                }
                .buttonStyle(.bordered)
            }

            campo(S.setupUsername,
                  provedor.usuarioEhContaPrincipal ? S.setupUsernameApple : S.setupUsernameSame) {
                TextField(provedor.usuarioEhContaPrincipal ? "voce@icloud.com" : endereco,
                          text: $usuario)
                    .textFieldStyle(.roundedBorder)
            }
            campo(S.setupPassword, S.setupPasswordHelp) {
                SecureField("••••••••••••••••", text: $senha)
                    .textFieldStyle(.roundedBorder)
            }

            if let resultado {
                Text(resultado)
                    .font(.caption)
                    .foregroundStyle(deuCerto ? .green : .orange)
                    .fixedSize(horizontal: false, vertical: true)
            }

            HStack {
                Button(S.back) { passo = 0 }
                Spacer()
                if testando { ProgressView().controlSize(.small) }
                Button(S.setupTest) { configurarETestar() }
                    .buttonStyle(.borderedProminent)
                    .disabled(senha.isEmpty || usuario.isEmpty || testando)
            }
        }
    }

    private var passoPronto: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(spacing: 8) {
                Image(systemName: "checkmark.seal.fill").foregroundStyle(.green).font(.title2)
                Text(S.setupDone).font(.headline)
            }
            Text(S.setupDoneHelp).font(.callout).foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)
            Button(S.setupOpenInbox) { store.secao = .entrada; store.refresh() }
                .buttonStyle(.borderedProminent)
        }
    }

    private func campo<Conteudo: View>(_ titulo: String, _ ajuda: String,
                                       @ViewBuilder conteudo: () -> Conteudo) -> some View {
        VStack(alignment: .leading, spacing: 3) {
            Text(titulo).font(.caption).fontWeight(.semibold)
            conteudo()
            Text(ajuda).font(.caption2).foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    private func caixaAviso(_ texto: String) -> some View {
        HStack(alignment: .top, spacing: 8) {
            Image(systemName: "info.circle").foregroundStyle(.orange)
            Text(texto).font(.caption).fixedSize(horizontal: false, vertical: true)
        }
        .padding(11)
        .background(RoundedRectangle(cornerRadius: 8).fill(Color.orange.opacity(0.10)))
    }

    /// Cria a conta, grava a senha no chaveiro e testa o login de verdade.
    private func configurarETestar() {
        guard let cli = Store.cliPath() else { resultado = S.cliMissing; return }
        testando = true
        resultado = nil
        let nome = String(endereco.split(separator: "@").first ?? "agente")
        var args = ["setup", "--no-prompt", "--address", endereco, "--name", nome,
                    "--provider", provedorID, "--username", usuario,
                    "--display-name", apelido, "--owner-name", dono]
        if provedorID == "custom" {
            args += ["--smtp-host", smtpHost, "--imap-host", imapHost]
        }
        let senhaDigitada = senha
        Task.detached(priority: .userInitiated) {
            let criada = Store.run(cli, args)
            guard criada.status == 0 else {
                await MainActor.run { testando = false; resultado = criada.err }
                return
            }
            // a senha vai pelo stdin: em argumento ela apareceria em `ps`
            let guardada = Store.run(cli, ["secret", nome, "--stdin"], stdin: senhaDigitada)
            guard guardada.status == 0 else {
                await MainActor.run { testando = false; resultado = guardada.err }
                return
            }
            let teste = Store.run(cli, ["doctor", "--account", nome, "--json"])
            await MainActor.run {
                testando = false
                senha = ""
                if teste.status == 0 {
                    deuCerto = true
                    resultado = S.setupWorked
                    passo = 2
                    store.refresh()
                } else {
                    deuCerto = false
                    resultado = Self.explicar(teste.out + teste.err)
                }
            }
        }
    }

    /// Traduz o erro do servidor para o que a pessoa precisa fazer.
    static func explicar(_ bruto: String) -> String {
        let texto = bruto.lowercased()
        if texto.contains("authentication") || texto.contains("535") || texto.contains("password") {
            return S.setupErrAuth
        }
        if texto.contains("not found") || texto.contains("não encontrada") {
            return S.setupErrNoSecret
        }
        if texto.contains("timed out") || texto.contains("connection") || texto.contains("resolve") {
            return S.setupErrNetwork
        }
        return bruto.trimmingCharacters(in: .whitespacesAndNewlines)
    }
}
