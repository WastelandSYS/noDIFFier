#!/usr/bin/env bash
set -euo pipefail

APP_NAME="noDIFFier"
INSTALL_DIR="${NODIFFIER_INSTALL_DIR:-/usr/local/share/nodiffier}"
BIN_DIR="${NODIFFIER_BIN_DIR:-/usr/local/bin}"
INSTALLED_FILE="$INSTALL_DIR/nodiffier.py"
INSTALLED_UNINSTALLER="$INSTALL_DIR/uninstall.sh"

if [ "${EUID:-$(id -u)}" -eq 0 ]; then
    SUDO=""
else
    SUDO="sudo"
fi

run_as_root() {
    if [ -n "$SUDO" ]; then
        "$SUDO" "$@"
    else
        "$@"
    fi
}

printf '\n🧹 Uninstalling %s...\n\n' "$APP_NAME"

if [ -n "$SUDO" ] && ! command -v sudo >/dev/null 2>&1; then
    printf '❌ sudo was not found and this uninstaller is not running as root.\n'
    printf 'Re-run with root privileges or install sudo first.\n'
    exit 1
fi

remove_path() {
    local path="$1"
    if [ -e "$path" ] || [ -L "$path" ]; then
        run_as_root rm -f -- "$path"
        printf 'Removed: %s\n' "$path"
    else
        printf 'Not found: %s\n' "$path"
    fi
}

remove_path "$BIN_DIR/nodiffier"
remove_path "$BIN_DIR/noDIFFier"
remove_path "$INSTALLED_FILE"
remove_path "$INSTALLED_UNINSTALLER"

if [ -d "$INSTALL_DIR" ]; then
    if find "$INSTALL_DIR" -mindepth 1 -print -quit 2>/dev/null | grep -q .; then
        printf 'Kept non-empty install directory: %s\n' "$INSTALL_DIR"
    else
        run_as_root rmdir "$INSTALL_DIR"
        printf 'Removed empty install directory: %s\n' "$INSTALL_DIR"
    fi
else
    printf 'Not found: %s\n' "$INSTALL_DIR"
fi

printf '\n✅ noDIFFier uninstalled.\n\n'
