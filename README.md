<!-- ========================================================= -->
<!--                        HERO IMAGE                         -->
<!-- ========================================================= -->

<img width="1983" height="793" alt="noDIFFier Image May 13, 2026, 01_44_36 PM" src="https://github.com/user-attachments/assets/f10e1bfa-c905-4703-a2d3-c1070266eaa5" />

# noDIFFier

An AI-assisted patch workflow tool for Linux terminals. noDIFFier validates and applies Codex-generated unified diffs directly to your project, then immediately waits for the next patch so development never has to stop.

---

# FEATURES

### v0.5.0 Workflow Improvements

- Boxed session summary with patches applied, files modified, backups created, failures, validation failures, and session duration
- Lightweight patch history logging under `.nodiffier-history/` after every successful patch
- Rollback helpers for listing backups, restoring a chosen snapshot, restoring the newest backup, and interactive rollback
- Dry run mode that validates patch safety, checks `git apply --check`, lists affected files, and makes no changes
- Patch preview prompts that show only affected file paths before applying changes
- Dirty Git worktree warning with `--force` / `--allow-dirty` overrides
- Git root detection when launched from a repository subdirectory, while preserving patch-file paths relative to the launch directory
- Batch patch mode for applying multiple `.patch` / `.diff` files sequentially with per-patch results


### AI Patch Workflow

- Paste Codex-generated unified diffs directly into the terminal
- Apply multiple patches continuously within a single session
- No manual patch files required
- No manual file editing required
- Designed specifically for AI-assisted development workflows

### Safe Patch Application

- Validates patches using `git apply --check`
- Blocks unsafe paths, absolute paths, and directory traversal attempts
- Creates automatic backups before modifying files
- Warns before applying patches over uncommitted Git changes
- Shows a concise patch preview before changes are applied
- Supports dry runs, rollback from backups, and patch history logging
- Clear success and failure reporting
- Detects the nearest Git repository root while still allowing current-directory mode

### Linux Terminal Tooling

- Applies unified diffs from pasted terminal input or patch files
- Works directly in your current directory with no hardcoded target folder
- Provides both `noDIFFier` and `nodiffier` global launcher commands
- Installer avoids `sudo pip` and Python package mutation
- Designed for Linux environments including Raspberry Pi OS, Kali, Debian, and Ubuntu
- Minimal footprint: one Python tool script plus install/uninstall scripts

---

# SCREENSHOTS


<img width="950" height="500" alt="nodiffierMENU" src="https://github.com/user-attachments/assets/24df4210-f7c1-4389-950a-a7e808f90bcd" />

---


# INSTALLATION

```bash
git clone https://github.com/WastelandSYS/noDIFFier.git
cd noDIFFier
chmod +x install.sh nodiffier.py
sudo ./install.sh
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
sudo ./uninstall.sh
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

Primary AI-assisted workflow:

```text
cd /path/to/your/project
nodiffier
paste Codex-generated patch
CTRL+D
patch is validated and applied
paste next patch
CTRL+D
patch is validated and applied
```

Continue pasting patches until the development task is complete. noDIFFier keeps the session open after each patch, so you can apply a sequence of AI-generated changes without restarting the application.

File mode examples:

```bash
cd /path/to/your/project
nodiffier changes.patch
nodiffier changes.diff
nodiffier *.patch
```

Dry run mode validates a patch and lists affected files without changing anything:

```bash
nodiffier --dry-run changes.patch
```

Rollback helpers use the existing `.nodiffier-backups/` snapshots and never delete backup history automatically:

```bash
nodiffier --list-backups
nodiffier --rollback-last
nodiffier --rollback
nodiffier --restore-backup 20260529T120000Z
```

Workflow safety prompts can be bypassed for trusted automation:

```bash
nodiffier --yes changes.patch
nodiffier --force changes.patch
nodiffier --allow-dirty changes.patch
```

Successful patch applications are logged under `.nodiffier-history/` with the timestamp, patch content, affected files, and result status for a lightweight audit trail.

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
- Defaults to the nearest Git repository root when launched from a subdirectory, unless you decline the prompt.

---

# WHY NODIFFIER?

AI coding assistants can generate useful unified diffs, but applying each patch manually adds repetitive work to the development loop.

Traditional workflow:

```text
Copy patch
Create patch file
Run patch command
Verify changes
Repeat
```

noDIFFier workflow:

```text
Paste patch
CTRL+D
Patch applied

Paste next patch
CTRL+D
Patch applied

Paste next patch
CTRL+D
Patch applied
```

The goal is to remove friction from AI-assisted development so developers can focus on building instead of managing patch files and repeating terminal commands. noDIFFier turns patch application into a continuous workflow: launch it once inside the project directory, paste each Codex-generated diff, press `CTRL+D`, review the result, and continue with the next patch.

The tool focuses on:

- rapid AI-generated patch application
- safe patch preflight checks
- minimal setup complexity
- Linux-friendly installation
- predictable current-directory behavior
- practical Codex and AI coding assistant workflows

---

# LICENSE

GNU GPL v3 License

---

# AUTHOR

[WastelandSYS](https://github.com/WastelandSYS)
