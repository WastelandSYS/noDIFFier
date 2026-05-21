<!-- ========================================================= -->
<!--                        HERO IMAGE                         -->
<!-- ========================================================= -->

<img width="1983" height="793" alt="noDIFFier Image May 13, 2026, 01_44_36 PM" src="https://github.com/user-attachments/assets/f10e1bfa-c905-4703-a2d3-c1070266eaa5" />

# noDIFFier

A lightweight Linux terminal tool that safely applies Codex-generated unified diffs to the current working directory using `git apply`.

---

# FEATURES

- Applies unified diffs from pasted terminal input or patch files
- Uses `git apply --check -` validation before patching
- Blocks unsafe patch paths such as absolute paths and `..` traversal
- Works directly in your current directory (no hardcoded target folder)
- Provides both `noDIFFier` and `nodiffier` global launcher commands
- Installer avoids `sudo pip` and Python package mutation
- Designed for Linux environments including Raspberry Pi OS, Kali, Debian, and Ubuntu
- Minimal footprint: one Python tool script plus install/uninstall scripts
- Simple success/failure flow for quick Codex patch application

---

# SCREENSHOTS


<img width="827" height="527" alt="nodiffier-0-4-1-1" src="https://github.com/user-attachments/assets/efc6bbe2-a2cb-4c50-98c0-a346cb8a8a62" />

---


# INSTALLATION

```bash
git clone https://github.com/WastelandSYS/noDIFFier.git
cd noDIFFier
chmod +x install.sh nodiffier.py
./install.sh
```

Launch with:

```bash
nodiffier
```

---

# UNINSTALLATION

```bash
cd noDIFFier
chmod +x uninstall.sh
./uninstall.sh
```

Optional manual cleanup:

```bash
sudo rm -f /usr/local/bin/nodiffier
sudo rm -f /usr/local/bin/noDIFFier
sudo rm -rf /usr/local/share/nodiffier
```

The uninstaller removes the global `nodiffier` and `noDIFFier` shortcuts and the installed `/usr/local/share/nodiffier` directory.

---

# USAGE

Default launch:

```bash
nodiffier
```

Paste mode (from Codex chat diff):

```bash
cd /path/to/your/project
nodiffier
# paste full diff, then press CTRL+D
```

File mode examples:

```bash
cd /path/to/your/project
nodiffier changes.patch
nodiffier changes.diff
```

Alias command:

```bash
noDIFFier
```

Version check:

```bash
nodiffier --version
```

# COMPATIBILITY

Designed primarily for Linux systems.

Tested/targeted on:

- Raspberry Pi OS
- Kali Linux
- Debian
- Ubuntu

Notes:

- Requires `git` for patch validation and application.
- Uses system Python 3 without installing global Python packages.
- Avoids `externally-managed-environment` issues by not using `sudo pip`.
- Applies patches only to the current working directory where you run it.

---

# WHY NODIFFIER?

noDIFFier was built to make Codex patch application safer, faster, and cleaner in terminal workflows.

The tool focuses on:
- safe patch preflight checks
- minimal setup complexity
- Linux-friendly installation
- predictable current-directory behavior
- practical Codex diff workflows

---

# LICENSE

MIT License (Coming soon)

---

# AUTHOR

[WastelandSYS](https://github.com/WastelandSYS)
