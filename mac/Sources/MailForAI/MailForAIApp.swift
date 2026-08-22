import SwiftUI

/// Cria a janela quando o app roda em modo janela.
///
/// Um app de barra de menus é `LSUIElement`, e nesse modo o SwiftUI não abre
/// cena de janela sozinho — a `WindowGroup` fica declarada e nada aparece. Por
/// isso a janela nasce aqui, na mão, com política de ativação trocada antes.
final class AppDelegate: NSObject, NSApplicationDelegate {
    static let windowMode: Bool =
        CommandLine.arguments.contains("--window")
        || ProcessInfo.processInfo.environment["MAILFORAI_UI_WINDOW"] == "1"

    private var window: NSWindow?

    func applicationDidFinishLaunching(_ notification: Notification) {
        let store = Store.shared
        Task { @MainActor in store.start() }
        guard Self.windowMode else { return }
        NSApp.setActivationPolicy(.regular)

        // contentView, e não contentViewController: com o controller o SwiftUI
        // impõe o fitting size e a janela abre espremida, cortando a fila.
        let window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 420, height: 620),
            styleMask: [.titled, .closable, .miniaturizable, .resizable],
            backing: .buffered, defer: false)
        window.contentView = NSHostingView(rootView: PanelView(store: store))
        window.title = "MailForAI"
        window.setContentSize(NSSize(width: 420, height: 620))
        window.center()
        window.makeKeyAndOrderFront(nil)
        self.window = window
        NSApp.activate(ignoringOtherApps: true)
    }
}

@main
struct MailForAIApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) private var delegate
    @StateObject private var store = Store.shared

    var body: some Scene {
        MenuBarExtra {
            PanelView(store: store)
                .onAppear { store.start() }
        } label: {
            // o número no ícone é o ponto do app: dá para saber que tem coisa
            // parada sem abrir nada. Ícone e número precisam sair como UM Text
            // interpolado — dois elementos soltos aqui e o SwiftUI desenha só o
            // primeiro, deixando o contador invisível.
            if store.waitingCount > 0 {
                Text("\(Image(systemName: "tray.full.fill")) \(store.waitingCount)")
            } else {
                Text("\(Image(systemName: "tray"))")
            }
        }
        .menuBarExtraStyle(.window)
    }
}
