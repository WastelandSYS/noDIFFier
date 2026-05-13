#!/usr/bin/env sh
set -eu

APP_NAME="noDIFFier"
REPO_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
SOURCE_FILE="$REPO_DIR/nodiffier.py"
INSTALL_DIR=${NODIFFIER_INSTALL_DIR:-"$HOME/.local/share/nodiffier"}
BIN_DIR=${NODIFFIER_BIN_DIR:-"$HOME/.local/bin"}
INSTALLED_FILE="$INSTALL_DIR/nodiffier.py"

printf '✨ Installing %s...\n' "$APP_NAME"

if ! command -v python3 >/dev/null 2>&1; then
    printf 'Error: python3 was not found. Install Python 3 first.\n' >&2
    exit 1
fi

if ! command -v git >/dev/null 2>&1; then
    printf 'Error: git was not found. Install it with: sudo apt install git\n' >&2
    exit 1
fi

if [ ! -f "$SOURCE_FILE" ]; then
    printf 'Error: %s was not found. Run this installer from the noDIFFier folder.\n' "$SOURCE_FILE" >&2
    exit 1
fi

mkdir -p "$INSTALL_DIR" "$BIN_DIR"
cp "$SOURCE_FILE" "$INSTALLED_FILE"
chmod +x "$INSTALLED_FILE"

cat > "$BIN_DIR/noDIFFier" <<EOF_WRAPPER
#!/usr/bin/env sh
exec python3 "$INSTALLED_FILE" "\$@"
EOF_WRAPPER

cat > "$BIN_DIR/nodiffier" <<EOF_WRAPPER
#!/usr/bin/env sh
exec python3 "$INSTALLED_FILE" "\$@"
EOF_WRAPPER

chmod +x "$BIN_DIR/noDIFFier" "$BIN_DIR/nodiffier"

printf '\n✅ Installed. Shortcuts created:\n'
printf '   %s/noDIFFier\n' "$BIN_DIR"
printf '   %s/nodiffier\n\n' "$BIN_DIR"

if command -v noDIFFier >/dev/null 2>&1; then
    noDIFFier --version
else
    printf 'Almost done: add ~/.local/bin to your PATH, then reopen your terminal:\n\n'
    printf '    echo '\''export PATH="$HOME/.local/bin:$PATH"'\'' >> ~/.bashrc\n'
    printf '    source ~/.bashrc\n\n'
    printf 'Then test it with:\n\n'
    printf '    noDIFFier --version\n'
fi
