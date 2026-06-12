#!/usr/bin/env bash
# package.sh — Build a distributable Pac-Man bundle with PyInstaller.
#
# Usage:
#   ./package.sh            Build a one-folder bundle under dist/pacman/
#   ./package.sh --zip      Also create dist/pacman-linux.zip for Itch.io upload
#
# Requirements:
#   uv must be installed (https://docs.astral.sh/uv/).
#   PyInstaller is added automatically to the project dev dependencies.
#
# The packaged executable expects assets/ and config.json to sit next to it
# (they are copied into the bundle by PyInstaller's --add-data directives).

set -euo pipefail

ENTRY="pac-man.py"
BUNDLE_NAME="pacman"
ASSETS_DIR="assets"
CONFIG_FILE="config.json"
WHEEL="mazegen-0.2.0-py3-none-any.whl"
GAME_README="GAME_README.txt"

echo "==> Building bundle '${BUNDLE_NAME}'…"
uv run pyinstaller \
    --name        "${BUNDLE_NAME}" \
    --onedir \
    --windowed \
    --add-data    "${ASSETS_DIR}:assets" \
    --add-data    "${CONFIG_FILE}:." \
    --add-data    "${WHEEL}:." \
    --add-data    "${GAME_README}:." \
    --noconfirm \
    "${ENTRY}"

echo "==> Bundle ready: dist/${BUNDLE_NAME}/"

# Optional: create a zip archive suitable for Itch.io upload.
if [[ "${1:-}" == "--zip" ]]; then
    ZIP_FILE="dist/${BUNDLE_NAME}-linux.zip"
    echo "==> Creating archive ${ZIP_FILE}…"
    (cd dist && zip -r "${BUNDLE_NAME}-linux.zip" "${BUNDLE_NAME}/")
    echo "==> Archive ready: ${ZIP_FILE}"
fi
