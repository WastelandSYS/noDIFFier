#!/usr/bin/env bash
set -euo pipefail

APP_NAME="noDIFFier"

REPO_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
SOURCE_FILE="$REPO_DIR/nodiffier.py"
SOURCE_UNINSTALLER="$REPO_DIR/uninstall.sh"

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

printf '\n✨ Installing %s...\n\n' "$APP_NAME"

# =========================
#      PLATFORM CHECKS
# =========================

case "$(uname -s)" in
    Linux) ;;
    *)
        printf '❌ Unsupported OS: %s\n' "$(uname -s)"
        printf 'This installer currently supports Linux only.\n'
        exit 1
        ;;
esac

ARCH="$(uname -m)"
case "$ARCH" in
    x86_64|amd64|aarch64|arm64|armv7l|armv6l)
        printf 'Detected architecture: %s\n' "$ARCH"
        ;;
    *)
        printf '⚠ Unrecognized architecture: %s\n' "$ARCH"
        printf 'Proceeding anyway because noDIFFier is pure Python.\n'
        ;;
esac

# =========================
#      DEPENDENCY CHECKS
# =========================

if ! command -v python3 >/dev/null 2>&1; then
    printf '❌ python3 was not found.\n'
    printf 'Install it first with:\n'
    printf '   sudo apt install python3\n'
    exit 1
fi

if ! command -v git >/dev/null 2>&1; then
    printf '❌ git was not found.\n'
    printf 'Install it first with:\n'
    printf '   sudo apt install git\n'
    exit 1
fi

if [ -n "$SUDO" ] && ! command -v sudo >/dev/null 2>&1; then
    printf '❌ sudo was not found and this installer is not running as root.\n'
    printf 'Re-run with root privileges or install sudo first.\n'
    exit 1
fi

# =========================
#       FILE CHECKS
# =========================

if [ ! -f "$SOURCE_FILE" ]; then
    printf '❌ Could not find:\n'
    printf '   %s\n\n' "$SOURCE_FILE"
    printf 'Run this installer from inside the noDIFFier folder.\n'
    exit 1
fi

if [ ! -f "$SOURCE_UNINSTALLER" ]; then
    printf '❌ Could not find:\n'
    printf '   %s\n\n' "$SOURCE_UNINSTALLER"
    printf 'Expected uninstall.sh in the same folder as install.sh.\n'
    exit 1
fi

# =========================
#     CREATE DIRECTORIES
# =========================

run_as_root mkdir -p "$INSTALL_DIR"
run_as_root mkdir -p "$BIN_DIR"

# =========================
#      INSTALL SCRIPT
# =========================

run_as_root cp "$SOURCE_FILE" "$INSTALLED_FILE"
run_as_root chmod 0755 "$INSTALLED_FILE"
run_as_root cp "$SOURCE_UNINSTALLER" "$INSTALLED_UNINSTALLER"
run_as_root chmod 0755 "$INSTALLED_UNINSTALLER"

# =========================
#      CREATE SHORTCUTS
# =========================

run_as_root ln -sfn "$INSTALLED_FILE" "$BIN_DIR/noDIFFier"
run_as_root ln -sfn "$INSTALLED_FILE" "$BIN_DIR/nodiffier"

# =========================
#       INSTALL DONE
# =========================

printf '\n✅ noDIFFier installed successfully!\n\n'
printf 'Installed files:\n'
printf '   %s\n' "$INSTALLED_FILE"
printf '   %s\n' "$INSTALLED_UNINSTALLER"

printf '\nCommands available:\n'
printf '   noDIFFier\n'
printf '   nodiffier\n\n'

printf 'Testing installation...\n\n'

if command -v nodiffier >/dev/null 2>&1; then
    nodiffier --version
    printf '\n🚀 Ready to use!\n\n'
    printf 'Example usage:\n'
    printf '   nodiffier\n'
    printf '   nodiffier update.diff\n'
    printf '   noDIFFier update.diff\n\n'
else
    printf '⚠ Install completed, but command was not found in PATH.\n\n'
    printf 'Check shortcut with:\n'
    printf '   ls -l %s/nodiffier\n\n' "$BIN_DIR"
    exit 1
fi
