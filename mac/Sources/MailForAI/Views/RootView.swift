import SwiftUI

/// A janela do app: barra lateral à esquerda, conteúdo à direita.
struct RootView: View {
    @ObservedObject var store: Store
    @AppStorage("language") private var idioma: String = Lang.system.rawValue

    var body: some View {
        NavigationSplitView {
            barraLateral
                .navigationSplitViewColumnWidth(min: 190, ideal: 200, max: 240)
        } detail: {
            conteudo
                .frame(minWidth: 520, minHeight: 460)
        }
        .frame(minWidth: 760, minHeight: 520)
        .id(idioma)
        .onAppear { store.start() }
    }

    private var barraLateral: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack(spacing: 9) {
                Image(systemName: "tray.full")
                    .foregroundStyle(store.waitingCount > 0 ? Color.orange : .secondary)
                VStack(alignment: .leading, spacing: 1) {
                    Text("MailForAI").font(.headline)
                    Text(store.mailbox.configured ? store.mailbox.address : S.notConfiguredShort)
                        .font(.caption).foregroundStyle(.secondary).lineLimit(1)
                }
            }
            .padding(.horizontal, 14).padding(.top, 16).padding(.bottom, 12)

            List(selection: Binding(get: { store.secao }, set: { store.secao = $0 ?? .fila })) {
                item(.entrada, "tray.and.arrow.down", S.sectionInbox, badge: nil)
                item(.fila, "checkmark.circle", S.sectionQueue,
                     badge: store.waitingCount > 0 ? store.waitingCount : nil)
                item(.enviados, "paperplane", S.sectionSent, badge: nil)
                item(.memoria, "brain", S.sectionMemory, badge: nil)
                item(.ajustes, "gearshape", S.sectionSettings, badge: nil)
            }
            .listStyle(.sidebar)

            Divider()
            HStack(spacing: 10) {
                Picker("", selection: $idioma) {
                    Text("PT").tag("pt"); Text("EN").tag("en")
                }
                .pickerStyle(.segmented).frame(width: 78)
                Spacer()
                if store.busy { ProgressView().controlSize(.small) }
            }
            .padding(10)
        }
    }

    private func item(_ secao: Secao, _ icone: String, _ titulo: String, badge: Int?) -> some View {
        Label(titulo, systemImage: icone)
            .badge(badge ?? 0)
            .tag(secao)
    }

    @ViewBuilder
    private var conteudo: some View {
        if !store.mailbox.configured {
            SetupWizardView(store: store)
        } else {
            switch store.secao {
            case .entrada: InboxView(store: store)
            case .fila: QueueView(store: store)
            case .enviados: SentView(store: store)
            case .memoria: MemoryView(store: store)
            case .ajustes: SettingsView(store: store)
            }
        }
    }
}

/// Cabeçalho comum das telas: título, explicação e ações à direita.
struct Cabecalho<Acoes: View>: View {
    let titulo: String
    let descricao: String
    @ViewBuilder var acoes: () -> Acoes

    var body: some View {
        HStack(alignment: .firstTextBaseline) {
            VStack(alignment: .leading, spacing: 3) {
                Text(titulo).font(.title3).fontWeight(.semibold)
                Text(descricao).font(.caption).foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
            }
            Spacer(minLength: 12)
            acoes()
        }
        .padding(.horizontal, 18).padding(.top, 16).padding(.bottom, 12)
    }
}

struct InboxView: View {
    @ObservedObject var store: Store
    @State private var selecionada: InboxMessage?
    @State private var corpo: String = ""
    @State private var respondendo = false
    @State private var rascunho = ""
    @State private var resultadoResposta: String?

    var body: some View {
        VStack(spacing: 0) {
            Cabecalho(titulo: S.sectionInbox, descricao: S.inboxHelp) {
                HStack(spacing: 8) {
                    Button(S.checkNow) { store.varrerAgora() }
                        .buttonStyle(.borderedProminent)
                        .disabled(store.busy)
                    Button(S.refresh) { store.carregarEntrada(force: true) }
                }
            }
            Divider()
            if let erro = store.errorText, store.inbox.isEmpty {
                aviso(erro)
            } else if store.inbox.isEmpty {
                if store.carregandoEntrada {
                    ProgressView().padding(40)
                } else {
                    vazio(S.inboxEmpty)
                }
            } else {
                HSplitView {
                    lista.frame(minWidth: 230, idealWidth: 260)
                    detalhe.frame(minWidth: 280)
                }
            }
        }
        .onAppear { store.carregarEntrada() }
    }

    private var lista: some View {
        List(store.inbox, selection: Binding(
            get: { selecionada?.uid },
            set: { uid in
                selecionada = store.inbox.first { $0.uid == uid }
                corpo = ""
                respondendo = false
                rascunho = ""
                resultadoResposta = nil
                if let msg = selecionada {
                    store.corpo(de: msg) { texto in corpo = texto }
                }
            })) { mensagem in
            VStack(alignment: .leading, spacing: 2) {
                HStack(spacing: 6) {
                    if mensagem.unread == true {
                        Circle().fill(Color.accentColor).frame(width: 6, height: 6)
                    }
                    Text(mensagem.sender).font(.system(size: 12, weight: .semibold)).lineLimit(1)
                    Spacer()
                    Text(String(mensagem.date.prefix(10)))
                        .font(.caption2).foregroundStyle(.secondary)
                }
                Text(mensagem.subject).font(.caption).lineLimit(2).foregroundStyle(.secondary)
                if let decisao = store.watchLog.first(where: { $0.uid == mensagem.uid }) {
                    Text(rotuloDecisao(decisao.action))
                        .font(.caption2)
                        .padding(.horizontal, 6).padding(.vertical, 1)
                        .background(Capsule().fill(corDecisao(decisao.action).opacity(0.18)))
                        .foregroundStyle(corDecisao(decisao.action))
                }
            }
            .padding(.vertical, 3)
            .tag(mensagem.uid)
        }
    }

    private var detalhe: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 10) {
                if let mensagem = selecionada {
                    Text(mensagem.subject).font(.title3).fontWeight(.semibold)
                        .fixedSize(horizontal: false, vertical: true)
                    Text(mensagem.from).font(.caption).foregroundStyle(.secondary)
                    Text(mensagem.date).font(.caption2).foregroundStyle(.secondary)
                    Divider()
                    Text(corpo.isEmpty ? S.loading : corpo)
                        .font(.system(size: 12))
                        .textSelection(.enabled)
                        .fixedSize(horizontal: false, vertical: true)

                    Divider()
                    if respondendo {
                        TextEditor(text: $rascunho)
                            .font(.system(size: 12))
                            .frame(minHeight: 120)
                            .overlay(RoundedRectangle(cornerRadius: 6)
                                .stroke(Color.secondary.opacity(0.3)))
                        HStack {
                            Button(S.cancel) { respondendo = false; rascunho = "" }
                            Spacer()
                            Button(S.sendReply) {
                                store.responder(uid: mensagem.uid, corpo: rascunho) { saida in
                                    resultadoResposta = saida
                                    respondendo = false
                                    rascunho = ""
                                }
                            }
                            .buttonStyle(.borderedProminent)
                            .disabled(rascunho.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                        }
                    } else {
                        HStack {
                            Button(S.reply) { respondendo = true }
                            if let resultadoResposta {
                                Text(resultadoResposta.contains("pending")
                                     ? S.replyQueued : S.replySent)
                                    .font(.caption).foregroundStyle(.secondary)
                            }
                        }
                    }
                } else {
                    Text(S.pickAMessage).foregroundStyle(.secondary).padding(.top, 40)
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(16)
        }
    }

    private func rotuloDecisao(_ acao: String) -> String {
        switch acao {
        case "reply": return S.actionReplied
        case "ask": return S.actionAsked
        case "ignore": return S.actionIgnored
        case "escalate": return S.actionEscalated
        case "out-of-scope": return S.actionOutOfScope
        default: return acao
        }
    }

    private func corDecisao(_ acao: String) -> Color {
        switch acao {
        case "reply": return .green
        case "ask": return .orange
        case "escalate": return .red
        case "out-of-scope": return .secondary
        default: return .secondary
        }
    }
}

struct SentView: View {
    @ObservedObject var store: Store
    @State private var compondo = false

    var body: some View {
        VStack(spacing: 0) {
            Cabecalho(titulo: S.sectionSent, descricao: S.sentHelp) {
                HStack(spacing: 8) {
                    Button(S.compose) { compondo = true }.buttonStyle(.borderedProminent)
                    Button(S.openHistory) { store.openHistory() }
                }
            }
            Divider()
            if store.sent.isEmpty {
                vazio(S.sentEmpty)
            } else {
                List(store.sent) { item in
                    VStack(alignment: .leading, spacing: 3) {
                        HStack {
                            Text(simbolo(item.status)).foregroundStyle(cor(item.status))
                            Text(item.subject).font(.system(size: 12, weight: .semibold))
                            Spacer()
                            Text(String(item.ts.prefix(16)).replacingOccurrences(of: "T", with: " "))
                                .font(.caption2).foregroundStyle(.secondary)
                        }
                        Text(item.to.joined(separator: ", "))
                            .font(.caption).foregroundStyle(.secondary)
                        if let erro = item.error, !erro.isEmpty {
                            Text(erro).font(.caption2).foregroundStyle(.orange)
                                .fixedSize(horizontal: false, vertical: true)
                        }
                    }
                    .padding(.vertical, 2)
                }
            }
        }
        .sheet(isPresented: $compondo) { ComposeView(store: store) }
    }

    private func simbolo(_ status: String) -> String {
        ["sent": "→", "failed": "✗", "blocked": "⊘"][status] ?? "•"
    }
    private func cor(_ status: String) -> Color {
        ["sent": Color.green, "failed": .red, "blocked": .orange][status] ?? .secondary
    }
}

/// Escrever uma mensagem à mão. Segue o mesmo caminho de um envio da IA:
/// passa pela allowlist, pelo teto e pela fila quando a caixa pede aprovação.
struct ComposeView: View {
    @ObservedObject var store: Store
    @Environment(\.dismiss) private var dismiss
    @State private var para = ""
    @State private var assunto = ""
    @State private var corpo = ""
    @State private var resultado: String?

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text(S.compose).font(.headline)
            TextField(S.to, text: $para).textFieldStyle(.roundedBorder)
            TextField(S.subject, text: $assunto).textFieldStyle(.roundedBorder)
            TextEditor(text: $corpo)
                .font(.system(size: 12))
                .frame(minHeight: 180)
                .overlay(RoundedRectangle(cornerRadius: 6).stroke(Color.secondary.opacity(0.3)))
            if let resultado {
                Text(resultado).font(.caption).foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
            }
            HStack {
                Button(S.cancel) { dismiss() }
                Spacer()
                Button(S.send) {
                    store.enviar(para: para, assunto: assunto, corpo: corpo) { saida in
                        resultado = saida
                        if saida.lowercased().contains("erro") || saida.lowercased().contains("error") {
                            return
                        }
                        dismiss()
                    }
                }
                .buttonStyle(.borderedProminent)
                .disabled(para.isEmpty || assunto.isEmpty || corpo.isEmpty || store.busy)
            }
        }
        .padding(16)
        .frame(width: 520)
    }
}

// MARK: - pedaços compartilhados

@ViewBuilder
func vazio(_ texto: String) -> some View {
    VStack(spacing: 8) {
        Image(systemName: "checkmark.circle").font(.title2).foregroundStyle(.secondary)
        Text(texto).font(.callout).foregroundStyle(.secondary)
            .multilineTextAlignment(.center)
    }
    .frame(maxWidth: .infinity, maxHeight: .infinity)
    .padding(30)
}

@ViewBuilder
func aviso(_ texto: String) -> some View {
    VStack(spacing: 10) {
        Image(systemName: "exclamationmark.triangle").font(.title2).foregroundStyle(.orange)
        Text(texto).font(.callout).foregroundStyle(.secondary)
            .multilineTextAlignment(.center)
            .fixedSize(horizontal: false, vertical: true)
    }
    .frame(maxWidth: .infinity, maxHeight: .infinity)
    .padding(30)
}
