#!/usr/bin/env sh
set -eu

APP_NAME="noDIFFier"
REPO_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
APP_DIR=${NODIFFIER_APP_DIR:-"$HOME/.local/share/nodiffier/app"}
BIN_DIR=${NODIFFIER_BIN_DIR:-"$HOME/.local/bin"}

printf '✨ Installing %s without touching system Python packages...\n' "$APP_NAME"
printf 'Repository: %s\n' "$REPO_DIR"
printf 'App directory: %s\n' "$APP_DIR"
printf 'Command directory: %s\n\n' "$BIN_DIR"

if ! command -v python3 >/dev/null 2>&1; then
    printf 'Error: python3 was not found on PATH.\n' >&2
    exit 1
fi

if ! command -v git >/dev/null 2>&1; then
    printf 'Error: git was not found on PATH. Install it with: sudo apt install git\n' >&2
    exit 1
fi

rm -rf "$APP_DIR"
mkdir -p "$APP_DIR" "$BIN_DIR"
cp -R "$REPO_DIR/src/nodiffier" "$APP_DIR/nodiffier"

cat > "$BIN_DIR/noDIFFier" <<MSG
#!/usr/bin/env sh
PYTHONPATH="$APP_DIR\${PYTHONPATH:+:\$PYTHONPATH}" exec python3 -m nodiffier.cli "\$@"
MSG

cat > "$BIN_DIR/nodiffier" <<MSG
#!/usr/bin/env sh
PYTHONPATH="$APP_DIR\${PYTHONPATH:+:\$PYTHONPATH}" exec python3 -m nodiffier.cli "\$@"
MSG

chmod +x "$BIN_DIR/noDIFFier" "$BIN_DIR/nodiffier"

cat <<MSG

✅ ${APP_NAME} installed successfully.

Try it with:

    noDIFFier --version

If your shell says "command not found", add this to your shell config and reopen the terminal:

    export PATH="\$HOME/.local/bin:\$PATH"

MSG
