import SwiftUI

/// Abre e mantém a janela do app.
///
/// Um app de barra de menus é `LSUIElement`, e nesse modo o SwiftUI não abre
/// cena de janela sozinho. Por isso a janela nasce aqui, na mão.
final class AppDelegate: NSObject, NSApplicationDelegate {
    private var window: NSWindow?

    func applicationDidFinishLaunching(_ notification: Notification) {
        Task { @MainActor in Store.shared.start() }
        // A janela abre já na primeira execução. O ícone da barra some quando a
        // barra está cheia — o macOS esconde o que não cabe —, e um app que não
        // mostra nada ao abrir passa por quebrado.
        mostrarJanela()
    }

    /// Clicar no app no Launchpad, Finder ou Dock traz a janela de volta.
    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows: Bool) -> Bool {
        mostrarJanela()
        return true
    }

    /// Fechar a janela não encerra o app: ele continua vigiando pela barra.
    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        false
    }

    @MainActor
    func mostrarJanela() {
        NSApp.setActivationPolicy(.regular)
        if let window {
            window.makeKeyAndOrderFront(nil)
            NSApp.activate(ignoringOtherApps: true)
            return
        }
        // contentView, e não contentViewController: com o controller o SwiftUI
        // impõe o fitting size e a janela abre espremida.
        let window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 940, height: 620),
            styleMask: [.titled, .closable, .miniaturizable, .resizable],
            backing: .buffered, defer: false)
        window.contentView = NSHostingView(rootView: RootView(store: Store.shared))
        window.title = "MailForAI"
        window.setFrameAutosaveName("MailForAIMainWindow")
        window.isReleasedWhenClosed = false
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
            MenuBarPanel(store: store) {
                (NSApp.delegate as? AppDelegate)?.mostrarJanela()
            }
        } label: {
            // Ícone e número precisam sair como UM Text interpolado — dois
            // elementos soltos aqui e o SwiftUI desenha só o primeiro, deixando
            // o contador invisível.
            if store.waitingCount > 0 {
                Text("\(Image(systemName: "tray.full.fill")) \(store.waitingCount)")
            } else {
                Text("\(Image(systemName: "tray"))")
            }
        }
        .menuBarExtraStyle(.window)
    }
}
