// swift-tools-version:5.9
import PackageDescription

let package = Package(
    name: "MailForAI",
    platforms: [.macOS(.v13)],
    targets: [
        .executableTarget(
            name: "MailForAI",
            path: "Sources/MailForAI"
        ),
        // bundle próprio só para as notificações saírem com o ícone do app
        .executableTarget(
            name: "MailForAINotifier",
            path: "Sources/Notifier"
        )
    ]
)
