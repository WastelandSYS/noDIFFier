# noDIFFier

noDIFFier is a tiny Python 3 CLI for Linux and Raspberry Pi OS that applies
Codex-generated unified diffs to the directory where you run it.

It intentionally does one thing: pass a pasted or file-based patch to
`git apply` in the current working directory. It does not watch folders, keep a
database, write logs, or hardcode any project path.

## Install

### Recommended install for Raspberry Pi OS, Kali, Debian, and Ubuntu

Do **not** use `sudo python3 -m pip install .` on modern Debian-based systems.
Those systems often enable Python's `externally-managed-environment` protection,
which blocks system-wide `pip` installs so your operating system Python does not
get damaged.

Instead, from this repository, run:

```bash
./install.sh
```

The installer does not use `pip` and does not modify system Python packages. It
copies noDIFFier to `~/.local/share/nodiffier/app` and creates the commands in
`~/.local/bin`.

If `noDIFFier` is not found after installing, add `~/.local/bin` to your `PATH`:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

Then verify the install:

```bash
noDIFFier --version
```

### Manual virtual environment install

If you prefer to manage a Python virtual environment yourself:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/noDIFFier --version
```

This installs two console commands:

- `noDIFFier`
- `nodiffier`

## Usage

### Paste mode

Run the tool inside the project you want to patch:

```bash
cd /path/to/project
noDIFFier
```

Paste the full unified diff into the terminal, then press `CTRL+D`. noDIFFier
will apply the patch with `git apply -`.

### File mode

Run the tool from the project directory and pass a patch file:

```bash
cd /path/to/project
noDIFFier changes.patch
```

`.diff` files work the same way:

```bash
noDIFFier changes.diff
```

## Safety model

- noDIFFier always operates in the current working directory.
- noDIFFier never hardcodes a target directory.
- noDIFFier rejects patch headers that contain absolute paths or `..` path
  components before calling `git apply`.
- noDIFFier uses `git apply --check -` first, then applies with `git apply -`
  only if the check succeeds.
- Patch application is delegated to Git.
