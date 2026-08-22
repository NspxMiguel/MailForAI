import SwiftUI

/// O que está esperando decisão: envios na fila e perguntas abertas.
struct QueueView: View {
    @ObservedObject var store: Store
    @State private var expandido: Set<String> = []
    @State private var notas: [String: String] = [:]
    @State private var respostas: [String: String] = [:]

    var body: some View {
        VStack(spacing: 0) {
            Cabecalho(titulo: S.sectionQueue, descricao: S.queueHelp) {
                Button(S.checkNow) { store.varrerAgora() }
                    .disabled(store.busy)
            }
            Divider()
            if store.waitingCount == 0 {
                vazio(S.nothingWaiting)
            } else {
                ScrollView {
                    VStack(alignment: .leading, spacing: 10) {
                        if !store.emails.isEmpty {
                            secao(S.waitingEmails)
                            ForEach(store.emails) { email in cartaoEmail(email) }
                        }
                        if !store.questions.isEmpty {
                            secao(S.waitingQuestions)
                            ForEach(store.questions) { pergunta in cartaoPergunta(pergunta) }
                        }
                    }
                    .padding(16)
                }
            }
        }
    }

    private func secao(_ titulo: String) -> some View {
        Text(titulo.uppercased())
            .font(.caption2).fontWeight(.semibold)
            .foregroundStyle(.secondary)
    }

    private func cartaoEmail(_ email: PendingEmail) -> some View {
        let aberto = expandido.contains(email.id)
        let corpo = email.body ?? ""
        return VStack(alignment: .leading, spacing: 6) {
            Text(email.displaySubject).font(.system(size: 13, weight: .semibold))
            linha(S.to, email.recipients)
            if let motivo = email.reason, !motivo.isEmpty { linha(S.why, motivo) }

            Text(aberto || corpo.count <= 260 ? corpo : String(corpo.prefix(260)) + "…")
                .font(.system(size: 12))
                .foregroundStyle(.primary.opacity(0.85))
                .textSelection(.enabled)
                .fixedSize(horizontal: false, vertical: true)

            if corpo.count > 260 {
                Button(aberto ? S.showLess : S.showMore) {
                    if aberto { expandido.remove(email.id) } else { expandido.insert(email.id) }
                }
                .buttonStyle(.link).font(.caption)
            }

            TextField(S.rejectNote, text: Binding(
                get: { notas[email.id] ?? "" },
                set: { notas[email.id] = $0 }))
                .textFieldStyle(.roundedBorder)
                .font(.caption)

            HStack {
                Button(S.approve) { store.approve(email) }
                    .buttonStyle(.borderedProminent)
                Button(S.reject) { store.reject(email, note: notas[email.id] ?? "") }
                    .buttonStyle(.bordered)
                Spacer()
                if let agente = email.agent {
                    Text("\(S.askedBy) \(agente)").font(.caption2).foregroundStyle(.secondary)
                }
            }
        }
        .padding(10)
        .background(RoundedRectangle(cornerRadius: 8).fill(Color.primary.opacity(0.05)))
    }

    private func cartaoPergunta(_ pergunta: Question) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(pergunta.question).font(.system(size: 13, weight: .semibold))
                .fixedSize(horizontal: false, vertical: true)
            if let contexto = pergunta.context, !contexto.isEmpty {
                Text(contexto).font(.caption).foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
            }
            if let opcoes = pergunta.options, !opcoes.isEmpty {
                HStack(spacing: 6) {
                    ForEach(opcoes, id: \.self) { opcao in
                        Button(opcao) { respostas[pergunta.id] = opcao }
                            .buttonStyle(.bordered).font(.caption)
                    }
                }
            }
            HStack {
                TextField(S.answerPlaceholder, text: Binding(
                    get: { respostas[pergunta.id] ?? "" },
                    set: { respostas[pergunta.id] = $0 }))
                    .textFieldStyle(.roundedBorder)
                    .onSubmit { store.answer(pergunta, text: respostas[pergunta.id] ?? "") }
                Button(S.sendAnswer) { store.answer(pergunta, text: respostas[pergunta.id] ?? "") }
                    .buttonStyle(.borderedProminent)
                    .disabled((respostas[pergunta.id] ?? "").trimmingCharacters(
                        in: .whitespacesAndNewlines).isEmpty)
            }
            Text(S.answerBecomesMemory).font(.caption2).foregroundStyle(.secondary)
        }
        .padding(10)
        .background(RoundedRectangle(cornerRadius: 8).fill(Color.primary.opacity(0.05)))
    }

    private func linha(_ rotulo: String, _ valor: String) -> some View {
        HStack(alignment: .top, spacing: 4) {
            Text("\(rotulo):").font(.caption).foregroundStyle(.secondary)
            Text(valor).font(.caption).fixedSize(horizontal: false, vertical: true)
        }
    }
}

/// Painel compacto da barra de menus: o essencial, com atalho para a janela.
struct MenuBarPanel: View {
    @ObservedObject var store: Store
    var abrirJanela: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack(spacing: 8) {
                Image(systemName: "tray.full")
                    .foregroundStyle(store.waitingCount > 0 ? Color.orange : .secondary)
                VStack(alignment: .leading, spacing: 1) {
                    Text("MailForAI").font(.headline)
                    Text(store.mailbox.configured ? store.mailbox.address : S.notConfiguredShort)
                        .font(.caption).foregroundStyle(.secondary)
                }
                Spacer()
            }
            .padding(12)
            Divider()

            if store.waitingCount == 0 {
                Text(S.nothingWaiting)
                    .font(.callout).foregroundStyle(.secondary)
                    .frame(maxWidth: .infinity).padding(.vertical, 22)
            } else {
                VStack(alignment: .leading, spacing: 8) {
                    ForEach(store.emails.prefix(3)) { email in
                        VStack(alignment: .leading, spacing: 4) {
                            Text(email.displaySubject).font(.system(size: 12, weight: .semibold))
                                .lineLimit(1)
                            Text(email.recipients).font(.caption).foregroundStyle(.secondary)
                                .lineLimit(1)
                            HStack {
                                Button(S.approve) { store.approve(email) }
                                    .buttonStyle(.borderedProminent).controlSize(.small)
                                Button(S.reject) { store.reject(email, note: "") }
                                    .buttonStyle(.bordered).controlSize(.small)
                            }
                        }
                    }
                    if !store.questions.isEmpty {
                        Text("\(store.questions.count) \(S.openQuestions)")
                            .font(.caption).foregroundStyle(.orange)
                    }
                }
                .padding(12)
            }

            Divider()
            HStack {
                Button(S.openApp) { abrirJanela() }.buttonStyle(.link)
                Spacer()
                Button(S.quit) { NSApplication.shared.terminate(nil) }.buttonStyle(.link)
            }
            .font(.caption).padding(10)
        }
        .frame(width: 330)
    }
}
