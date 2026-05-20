<img width="1983" height="793" alt="noDIFFier Image May 13, 2026, 01_44_36 PM" src="https://github.com/user-attachments/assets/f10e1bfa-c905-4703-a2d3-c1070266eaa5" />

#

<img width="812" height="459" alt="noDIFFier" src="https://github.com/user-attachments/assets/7cdc1f9e-2ac1-4937-aa9a-085731211c90" />

# noDIFFier

A tool used for fixing / updating Codex's DIFF outputs.

noDIFFier is a tiny Python 3 command-line tool for Linux, Raspberry Pi OS, Kali,
Debian, and Ubuntu. It applies Codex-generated unified diffs to the directory
where you run it.

It stays simple on purpose:

* one Python file: `nodiffier.py`
* one installer: `install.sh`
* no hardcoded target folder
* patching is done by `git apply`

## Install

From the noDIFFier folder, run:

```bash
git clone https://github.com/WastelandSYS/noDIFFier.git
cd noDIFFier
chmod +x ./install.sh nodiffier.py
./install.sh
```

The installer copies `nodiffier.py` to:

```text
/usr/local/share/nodiffier/nodiffier.py
```

Then it creates two global shortcut commands:

```text
/usr/local/bin/noDIFFier
/usr/local/bin/nodiffier
```

Available commands:

```bash
noDIFFier
nodiffier
```

This avoids the Debian/Raspberry Pi/Kali `externally-managed-environment` error
because it does not run `sudo pip` and does not modify system Python packages.

No PATH editing or `.bashrc` modification is required because
`/usr/local/bin` is already included in standard Linux PATHs.

You can verify the install with:

```bash
nodiffier --version
```

You should see something like:

```text
noDIFFier 0.2.0
```

## Use it: paste mode

Use paste mode when Codex gives you a diff in chat.

Go to the project you want to patch:

```bash
cd /path/to/your/project
```

Run noDIFFier:

```bash
nodiffier
```

Paste the full diff into the terminal, then press `CTRL+D`.

noDIFFier will show `Applying patch…` and then either `Success` or `Failed`.

## Use it: file mode

Use file mode when you saved the diff as a `.patch` or `.diff` file.

Go to the project you want to patch:

```bash
cd /path/to/your/project
```

Apply the patch file:

```bash
nodiffier changes.patch
```

or:

```bash
nodiffier changes.diff
```

Both command styles work:

```bash
nodiffier
noDIFFier
```

## Important safety notes

* noDIFFier applies patches to the current working directory only.
* It never has a built-in target folder.
* It rejects patch headers with absolute paths or `..` path components.
* It runs `git apply --check -` first.
* It only runs `git apply -` if the check succeeds.

## Uninstall

Run the uninstaller:

```bash
/usr/local/share/nodiffier/uninstall.sh
```

Or remove manually:

```bash
sudo rm -f /usr/local/bin/nodiffier
sudo rm -f /usr/local/bin/noDIFFier
sudo rm -rf /usr/local/share/nodiffier
```
