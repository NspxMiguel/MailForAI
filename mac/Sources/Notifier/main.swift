import AppKit
import Foundation
import UserNotifications

/// Notificador com a cara do MailForAI.
///
/// A notificação saía por `osascript`, e o macOS mostrava o ícone do Editor de
/// Scripts — o aviso não parecia vir do app. Este é um bundle próprio, com o
/// mesmo ícone, que só posta a notificação e sai. Vive dentro do MailForAI.app
/// e é chamado tanto pelo app quanto pelo serviço em Python.
///
///     MailForAINotifier "título" "mensagem" "subtítulo"

let argumentos = Array(CommandLine.arguments.dropFirst())
guard argumentos.count >= 2 else {
    FileHandle.standardError.write(Data("uso: notifier <título> <mensagem> [subtítulo]\n".utf8))
    exit(2)
}

let conteudo = UNMutableNotificationContent()
conteudo.title = argumentos[0]
conteudo.body = argumentos[1]
if argumentos.count > 2, !argumentos[2].isEmpty {
    conteudo.subtitle = argumentos[2]
}
conteudo.sound = .default

let centro = UNUserNotificationCenter.current()
let pronto = DispatchSemaphore(value: 0)
var saida: Int32 = 0

// Quando a permissão ainda não foi dada, o macOS abre um diálogo e só responde
// quando a pessoa clica. Desistir em poucos segundos matava o processo com o
// diálogo ainda na tela — e a permissão nunca era concedida.
var esperandoPessoa = false
centro.getNotificationSettings { ajustes in
    esperandoPessoa = ajustes.authorizationStatus == .notDetermined
}
Thread.sleep(forTimeInterval: 0.2)

centro.requestAuthorization(options: [.alert, .sound]) { autorizado, _ in
    guard autorizado else {
        saida = 3
        pronto.signal()
        return
    }
    let pedido = UNNotificationRequest(identifier: UUID().uuidString,
                                       content: conteudo, trigger: nil)
    centro.add(pedido) { erro in
        if erro != nil { saida = 4 }
        // sair na hora corta a notificação antes de ela aparecer
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.6) { pronto.signal() }
    }
}

// o processo precisa de um runloop vivo para o callback chegar
DispatchQueue.global().async {
    let limite: DispatchTime = esperandoPessoa ? .now() + 120 : .now() + 8
    if pronto.wait(timeout: limite) == .timedOut { saida = 5 }
    exit(saida)
}
_ = NSApplication.shared
NSApplication.shared.setActivationPolicy(.prohibited)
NSApplication.shared.run()
