#!/bin/bash
# Gera Resources/AppIcon.icns a partir de um PNG de 1024. Sem PNG novo, mantém
# o ícone que já existe — o design definitivo vem depois, e regerar a cada
# build sujaria o diff sem motivo.
set -euo pipefail
cd "$(dirname "$0")"

SOURCE="${1:-Resources/icon-1024.png}"
[ -f "$SOURCE" ] || { echo "sem $SOURCE — nada a fazer"; exit 0; }

ICONSET="$(mktemp -d)/AppIcon.iconset"
mkdir -p "$ICONSET"
for size in 16 32 128 256 512; do
  sips -z $size $size "$SOURCE" --out "$ICONSET/icon_${size}x${size}.png" >/dev/null
  sips -z $((size*2)) $((size*2)) "$SOURCE" --out "$ICONSET/icon_${size}x${size}@2x.png" >/dev/null
done
iconutil -c icns "$ICONSET" -o Resources/AppIcon.icns
echo "==> Resources/AppIcon.icns"
