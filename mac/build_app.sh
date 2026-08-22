#!/bin/bash
# Monta MailForAI.app. O CLI em Python viaja dentro do bundle: o app não faz
# nada sozinho, ele conversa com o mesmo mailforai que roda no terminal.
set -euo pipefail
cd "$(dirname "$0")"

APP_NAME="MailForAI"
BUILD_DIR=".build/release"
APP_BUNDLE="${APP_NAME}.app"
REPO_DIR=".."
VERSION="$(python3 -c "import re,pathlib; print(re.search(r'__version__ = \"([^\"]+)\"', pathlib.Path('${REPO_DIR}/mailforai_lib/__init__.py').read_text()).group(1))")"

echo "==> Compilando (release)…"
swift build -c release
swift build -c release --product MailForAINotifier

./make_icon.sh >/dev/null || true

echo "==> Montando ${APP_BUNDLE} (versão ${VERSION})…"
rm -rf "${APP_BUNDLE}"
mkdir -p "${APP_BUNDLE}/Contents/MacOS"
mkdir -p "${APP_BUNDLE}/Contents/Resources/mailforai"

cp "${BUILD_DIR}/${APP_NAME}" "${APP_BUNDLE}/Contents/MacOS/${APP_NAME}"
[ -f Resources/AppIcon.icns ] && cp Resources/AppIcon.icns "${APP_BUNDLE}/Contents/Resources/AppIcon.icns"
# o PNG viaja junto: é o ícone que a notificação usa
[ -f Resources/icon-1024.png ] && cp Resources/icon-1024.png "${APP_BUNDLE}/Contents/Resources/icon-1024.png"

# O que o CLI precisa para rodar de dentro do bundle. `hooks` vai junto porque
# `mailforai hook` instala o lembrete apontando para o próprio caminho.
for item in bin mailforai_lib hooks docs tests; do
  cp -R "${REPO_DIR}/${item}" "${APP_BUNDLE}/Contents/Resources/mailforai/${item}"
done
find "${APP_BUNDLE}/Contents/Resources/mailforai" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Notificador: bundle próprio dentro do app. Sem ele a notificação sai pelo
# osascript e o macOS mostra o ícone do Editor de Scripts, como se o aviso
# viesse de outro programa.
NOTIFIER="${APP_BUNDLE}/Contents/Resources/MailForAINotifier.app"
mkdir -p "${NOTIFIER}/Contents/MacOS" "${NOTIFIER}/Contents/Resources"
cp "${BUILD_DIR}/MailForAINotifier" "${NOTIFIER}/Contents/MacOS/MailForAINotifier"
[ -f Resources/AppIcon.icns ] && cp Resources/AppIcon.icns "${NOTIFIER}/Contents/Resources/AppIcon.icns"
cat > "${NOTIFIER}/Contents/Info.plist" <<NPLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>MailForAINotifier</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>CFBundleIdentifier</key>
    <string>dev.nspx.mailforai.notifier</string>
    <key>CFBundleName</key>
    <string>MailForAI</string>
    <key>CFBundleDisplayName</key>
    <string>MailForAI</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>${VERSION}</string>
    <key>LSMinimumSystemVersion</key>
    <string>13.0</string>
    <key>LSUIElement</key>
    <true/>
</dict>
</plist>
NPLIST
codesign --force --sign - "${NOTIFIER}" >/dev/null 2>&1 || true

cat > "${APP_BUNDLE}/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>${APP_NAME}</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>CFBundleIdentifier</key>
    <string>dev.nspx.mailforai</string>
    <key>CFBundleName</key>
    <string>MailForAI</string>
    <key>CFBundleDisplayName</key>
    <string>MailForAI</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>${VERSION}</string>
    <key>CFBundleVersion</key>
    <string>${VERSION}</string>
    <key>LSMinimumSystemVersion</key>
    <string>13.0</string>
    <!-- app de barra de menus: sem ícone no Dock e sem janela ao abrir -->
    <key>LSUIElement</key>
    <true/>
    <key>NSHumanReadableCopyright</key>
    <string>MIT</string>
</dict>
</plist>
PLIST

# Assinatura ad-hoc: sem ela o macOS mata o app na primeira execução em
# máquinas com Gatekeeper mais rígido.
codesign --force --deep --sign - "${APP_BUNDLE}" >/dev/null 2>&1 || true

echo "==> Pronto: $(pwd)/${APP_BUNDLE}"
