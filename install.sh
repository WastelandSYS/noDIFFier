#!/bin/bash
set -eu

APP_NAME="noDIFFier"

REPO_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

SOURCE_FILE="$REPO_DIR/nodiffier.py"

INSTALL_DIR="${NODIFFIER_INSTALL_DIR:-$HOME/.local/share/nodiffier}"
BIN_DIR="${NODIFFIER_BIN_DIR:-$HOME/.local/bin}"

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

mkdir -p "$INSTALL_DIR"
mkdir -p "$BIN_DIR"

# =========================
#      INSTALL SCRIPT
# =========================

cp "$SOURCE_FILE" "$INSTALLED_FILE"
chmod +x "$INSTALLED_FILE"

# =========================
#      CREATE WRAPPERS
# =========================

cat > "$BIN_DIR/noDIFFier" <<EOF
#!/bin/bash
exec python3 "$INSTALLED_FILE" "\$@"
EOF

cat > "$BIN_DIR/nodiffier" <<EOF
#!/bin/bash
exec python3 "$INSTALLED_FILE" "\$@"
EOF

chmod +x "$BIN_DIR/noDIFFier"
chmod +x "$BIN_DIR/nodiffier"

# =========================
#        PATH FIX
# =========================

PATH_LINE='export PATH="$HOME/.local/bin:$PATH"'

if ! grep -Fq "$PATH_LINE" "$HOME/.bashrc"; then

    printf '🔧 Adding ~/.local/bin to PATH...\n'

    echo '' >> "$HOME/.bashrc"
    echo '# noDIFFier PATH setup' >> "$HOME/.bashrc"
    echo "$PATH_LINE" >> "$HOME/.bashrc"

fi

# Export immediately for current session
export PATH="$HOME/.local/bin:$PATH"

# =========================
#       INSTALL DONE
# =========================

printf '\n✅ noDIFFier installed successfully!\n\n'

printf 'Installed files:\n'
printf '   %s\n' "$INSTALLED_FILE"

printf '\nCommands available:\n'
printf '   noDIFFier\n'
printf '   nodiffier\n\n'

printf 'Testing installation...\n\n'

if command -v noDIFFier >/dev/null 2>&1; then

    noDIFFier --version

    printf '\n🚀 Ready to use!\n\n'
    printf 'Example usage:\n'
    printf '   noDIFFier\n'
    printf '   noDIFFier update.diff\n\n'

else

    printf '⚠ PATH update may require a new terminal session.\n\n'
    printf 'Run:\n'
    printf '   source ~/.bashrc\n\n'
    printf 'Then test:\n'
    printf '   noDIFFier --version\n\n'

fi
