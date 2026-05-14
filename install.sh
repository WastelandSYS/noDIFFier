#!/bin/bash
set -eu

APP_NAME="noDIFFier"

REPO_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

SOURCE_FILE="$REPO_DIR/nodiffier.py"

INSTALL_DIR="${NODIFFIER_INSTALL_DIR:-/usr/local/share/nodiffier}"
BIN_DIR="${NODIFFIER_BIN_DIR:-/usr/local/bin}"

INSTALLED_FILE="$INSTALL_DIR/nodiffier.py"

printf '\n✨ Installing %s...\n\n' "$APP_NAME"

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

# =========================
#       FILE CHECKS
# =========================

if [ ! -f "$SOURCE_FILE" ]; then
    printf '❌ Could not find:\n'
    printf '   %s\n\n' "$SOURCE_FILE"
    printf 'Run this installer from inside the noDIFFier folder.\n'
    exit 1
fi

# =========================
#     CREATE DIRECTORIES
# =========================

sudo mkdir -p "$INSTALL_DIR"
sudo mkdir -p "$BIN_DIR"

# =========================
#      INSTALL SCRIPT
# =========================

sudo cp "$SOURCE_FILE" "$INSTALLED_FILE"
sudo chmod +x "$INSTALLED_FILE"

# =========================
#      CREATE SHORTCUTS
# =========================

sudo ln -sf "$INSTALLED_FILE" "$BIN_DIR/noDIFFier"
sudo ln -sf "$INSTALLED_FILE" "$BIN_DIR/nodiffier"

# =========================
#       INSTALL DONE
# =========================

printf '\n✅ noDIFFier installed successfully!\n\n'

printf 'Installed file:\n'
printf '   %s\n' "$INSTALLED_FILE"

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
    printf '   ls -l /usr/local/bin/nodiffier\n\n'
    exit 1

fi
