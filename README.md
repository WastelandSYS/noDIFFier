# noDIFFier

noDIFFier is a tiny Python 3 CLI for Linux and Raspberry Pi OS that applies
Codex-generated unified diffs to the directory where you run it.

It intentionally does one thing: pass a pasted or file-based patch to
`git apply` in the current working directory. It does not watch folders, keep a
database, write logs, or hardcode any project path.

## Install

From this repository:

```bash
python3 -m pip install .
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
