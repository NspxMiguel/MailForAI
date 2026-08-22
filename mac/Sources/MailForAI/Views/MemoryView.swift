import SwiftUI

/// O que o agente aprendeu sobre o dono — visível, editável, apagável.
struct MemoryView: View {
    @ObservedObject var store: Store
    @State private var rotulo = ""
    @State private var valor = ""
    @State private var categoria = "conta"
    @State private var rascunhoNotas = ""
    @State private var editandoNotas = false

    private let categorias = ["conta", "aparelho", "compra", "pessoal", "preferência", "outro"]

    var body: some View {
        VStack(spacing: 0) {
            Cabecalho(titulo: S.sectionMemory, descricao: S.memoryHelp) { EmptyView() }
            Divider()
            ScrollView {
                VStack(alignment: .leading, spacing: 14) {
                    adicionar
                    if store.facts.isEmpty {
                        Text(S.memoryEmpty).font(.callout).foregroundStyle(.secondary)
                            .frame(maxWidth: .infinity).padding(.vertical, 20)
                    } else {
                        ForEach(store.facts) { fato in cartao(fato) }
                    }
                    observacoes
                }
                .padding(16)
            }
        }
        .onAppear { rascunhoNotas = store.notes }
    }

    private var adicionar: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(S.memoryAdd).font(.caption).foregroundStyle(.secondary)
            HStack(spacing: 6) {
                TextField(S.memoryLabel, text: $rotulo).textFieldStyle(.roundedBorder)
                TextField(S.memoryValue, text: $valor).textFieldStyle(.roundedBorder)
                Picker("", selection: $categoria) {
                    ForEach(categorias, id: \.self) { Text($0).tag($0) }
                }
                .frame(width: 120)
                Button(S.save) {
                    store.lembrar(rotulo: rotulo, valor: valor, categoria: categoria)
                    rotulo = ""; valor = ""
                }
                .disabled(rotulo.isEmpty || valor.isEmpty)
            }
        }
    }

    private func cartao(_ fato: Fact) -> some View {
        HStack(alignment: .top) {
            VStack(alignment: .leading, spacing: 2) {
                HStack(spacing: 6) {
                    Text(fato.label).font(.system(size: 12, weight: .semibold))
                    Text(fato.category)
                        .font(.caption2)
                        .padding(.horizontal, 6).padding(.vertical, 1)
                        .background(Capsule().fill(Color.secondary.opacity(0.15)))
                    if fato.sensitive == true {
                        Image(systemName: "lock.fill").font(.caption2).foregroundStyle(.orange)
                    }
                }
                Text(fato.value).font(.system(size: 12)).textSelection(.enabled)
                Text("\(fato.source ?? "") · \(String((fato.updated ?? "").prefix(10)))")
                    .font(.caption2).foregroundStyle(.secondary)
            }
            Spacer()
            Button {
                store.esquecer(fato)
            } label: {
                Image(systemName: "trash")
            }
            .buttonStyle(.borderless)
            .help(S.forget)
        }
        .padding(10)
        .background(RoundedRectangle(cornerRadius: 8).fill(Color.primary.opacity(0.05)))
    }

    private var observacoes: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(S.memoryNotes).font(.caption).foregroundStyle(.secondary)
            TextEditor(text: $rascunhoNotas)
                .font(.system(size: 12))
                .frame(height: 90)
                .overlay(RoundedRectangle(cornerRadius: 6).stroke(Color.secondary.opacity(0.3)))
                .onChange(of: rascunhoNotas) { _ in editandoNotas = true }
            HStack {
                Text(S.memoryNotesHelp).font(.caption2).foregroundStyle(.secondary)
                Spacer()
                Button(S.save) {
                    store.salvarNotas(rascunhoNotas)
                    editandoNotas = false
                }
                .disabled(!editandoNotas)
            }
        }
    }
}
