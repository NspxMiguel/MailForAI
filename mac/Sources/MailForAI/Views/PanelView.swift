import SwiftUI

struct PanelView: View {
    @ObservedObject var store: Store
    @AppStorage("language") private var idioma: String = Lang.system.rawValue
    @State private var confirmarAuto = false
    @State private var expandido: Set<String> = []
    @State private var notas: [String: String] = [:]
    @State private var respostas: [String: String] = [:]

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            cabecalho
            Divider()
            if let erro = store.errorText {
                aviso(erro)
            } else if store.waitingCount == 0 {
                vazio
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
                    .padding(12)
                }
                .frame(minHeight: 300, maxHeight: 460)
            }
            Divider()
            rodape
        }
        .frame(width: 420)
        .id(idioma)
    }

    // MARK: - partes

    private var cabecalho: some View {
        HStack(spacing: 8) {
            Image(systemName: "tray.full")
                .foregroundStyle(store.waitingCount > 0 ? Color.orange : Color.secondary)
            VStack(alignment: .leading, spacing: 1) {
                Text("MailForAI").font(.headline)
                Text(store.mailbox.address.isEmpty ? S.noMailbox : store.mailbox.address)
                    .font(.caption).foregroundStyle(.secondary).lineLimit(1)
            }
            Spacer()
            Picker("", selection: Binding(
                get: { store.mailbox.mode },
                // ligar o modo automático desarma a única trava que segura um
                // envio: vale um clique a mais. Voltar para `confirm` é sempre
                // direto — aperta a trava, não afrouxa.
                set: { novo in
                    if novo == "auto" { confirmarAuto = true } else { store.setMode(novo) }
                })) {
                Text(S.modeConfirm).tag("confirm")
                Text(S.modeAuto).tag("auto")
            }
            .pickerStyle(.menu)
            .frame(width: 150)
            .help(S.modeTitle)
            .alert(S.autoTitle, isPresented: $confirmarAuto) {
                Button(S.cancel, role: .cancel) { }
                Button(S.autoConfirm) { store.setMode("auto") }
            } message: {
                Text(S.autoBody)
            }
        }
        .padding(12)
    }

    private func secao(_ titulo: String) -> some View {
        Text(titulo.uppercased())
            .font(.caption2).fontWeight(.semibold)
            .foregroundStyle(.secondary)
            .padding(.top, 2)
    }

    private func cartaoEmail(_ email: PendingEmail) -> some View {
        let aberto = expandido.contains(email.id)
        let corpo = email.body ?? ""
        return VStack(alignment: .leading, spacing: 6) {
            Text(email.displaySubject).font(.system(size: 13, weight: .semibold))
            linha(S.to, email.recipients)
            if let motivo = email.reason, !motivo.isEmpty { linha(S.why, motivo) }

            Text(aberto || corpo.count <= 240 ? corpo : String(corpo.prefix(240)) + "…")
                .font(.system(size: 12))
                .foregroundStyle(.primary.opacity(0.85))
                .textSelection(.enabled)
                .fixedSize(horizontal: false, vertical: true)

            if corpo.count > 240 {
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
                Button(S.send) { store.answer(pergunta, text: respostas[pergunta.id] ?? "") }
                    .buttonStyle(.borderedProminent)
                    .disabled((respostas[pergunta.id] ?? "").trimmingCharacters(
                        in: .whitespacesAndNewlines).isEmpty)
            }
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

    private var vazio: some View {
        HStack {
            Spacer()
            VStack(spacing: 6) {
                Image(systemName: "checkmark.circle").font(.title2).foregroundStyle(.secondary)
                Text(S.nothingWaiting).font(.callout).foregroundStyle(.secondary)
            }
            Spacer()
        }
        .padding(.vertical, 30)
    }

    private func aviso(_ texto: String) -> some View {
        Text(texto)
            .font(.callout)
            .foregroundStyle(.secondary)
            .fixedSize(horizontal: false, vertical: true)
            .padding(16)
    }

    private var rodape: some View {
        HStack {
            Button(S.openHistory) { store.openHistory() }.buttonStyle(.link)
            Button(S.refresh) { store.refresh() }.buttonStyle(.link)
            Spacer()
            Picker("", selection: $idioma) {
                Text("PT").tag("pt")
                Text("EN").tag("en")
            }
            .pickerStyle(.segmented)
            .frame(width: 84)
            .help(S.language)
            Button(S.quit) { NSApplication.shared.terminate(nil) }.buttonStyle(.link)
        }
        .font(.caption)
        .padding(10)
    }
}
