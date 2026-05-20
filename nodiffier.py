#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Iterable

APP_NAME = "noDIFFier"
VERSION = "0.4.1"
BACKUP_ROOT = ".nodiffier-backups"



ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def visible_len(text: str) -> int:
    return len(ANSI_RE.sub("", text))


def truncate_visible(text: str, max_visible: int) -> str:
    if max_visible <= 0:
        return ""
    out: list[str] = []
    visible = 0
    i = 0
    while i < len(text) and visible < max_visible:
        if text[i] == "\x1b":
            end = text.find("m", i)
            if end != -1:
                out.append(text[i:end + 1])
                i = end + 1
                continue
        out.append(text[i])
        visible += 1
        i += 1
    return "".join(out)


def pad_visible(text: str, width: int) -> str:
    clipped = truncate_visible(text, width)
    padding = max(0, width - visible_len(clipped))
    return clipped + (" " * padding)

class PatchSafetyError(ValueError):
    """Raised when a patch references a path outside the working directory."""


class Style:
    def __init__(self) -> None:
        self.enabled = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None

    def paint(self, text: str, code: str) -> str:
        if not self.enabled:
            return text
        return f"\033[{code}m{text}\033[0m"


def terminal_width(default: int = 100) -> int:
    return max(60, shutil.get_terminal_size((default, 30)).columns)


def boxed(style: Style, lines: list[str], color: str | None = "36") -> str:
    width = min(terminal_width(), 140)
    inner = width - 4
    top_raw = f"╔{'═' * (width - 2)}╗"
    bottom_raw = f"╚{'═' * (width - 2)}╝"
    side_left = "║ "
    side_right = " ║"

    if color:
        top = style.paint(top_raw, color)
        bottom = style.paint(bottom_raw, color)
        left = style.paint(side_left, color)
        right = style.paint(side_right, color)
    else:
        top = top_raw
        bottom = bottom_raw
        left = side_left
        right = side_right

    body = [f"{left}{pad_visible(line, inner)}{right}" for line in lines]
    return "\n".join([top, *body, bottom])


def smooth_print(text: str, enabled: bool = True, delay: float = 0.01) -> None:
    if enabled and sys.stdout.isatty():
        for line in text.splitlines():
            print(line)
            time.sleep(delay)
    else:
        print(text)


def parser() -> argparse.ArgumentParser:
    cli = argparse.ArgumentParser(
        prog=APP_NAME,
        description=(
            "Apply a unified .diff/.patch to the current directory. "
            "Run without a file to paste diffs; press CTRL+D after each one."
        ),
    )
    cli.add_argument(
        "patch_file",
        nargs="?",
        help="Optional .diff or .patch file to apply to the current directory.",
    )
    cli.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate that the patch applies cleanly without changing files.",
    )
    cli.add_argument(
        "--stat",
        action="store_true",
        help="Print git apply statistics before applying the patch.",
    )
    cli.add_argument(
        "--3way",
        dest="three_way",
        action="store_true",
        help="Try a three-way merge when a patch does not apply cleanly.",
    )
    cli.add_argument(
        "--reverse",
        action="store_true",
        help="Apply the patch in reverse, useful for undoing a saved patch.",
    )
    cli.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip automatic backups of existing files before applying.",
    )
    cli.add_argument(
        "--allow-dirty",
        action="store_true",
        help="Do not warn when the current Git working tree already has changes.",
    )
    cli.add_argument(
        "--no-clear",
        action="store_true",
        help="Do not clear the terminal before showing the noDIFFier banner.",
    )
    cli.add_argument(
        "--list-backups",
        action="store_true",
        help="List saved noDIFFier backup snapshots for the current directory.",
    )
    cli.add_argument(
        "--restore-backup",
        metavar="SNAPSHOT",
        help="Restore files from a backup snapshot (timestamp from --list-backups).",
    )
    cli.add_argument("--version", action="version", version=f"{APP_NAME} {VERSION}")
    return cli


def header(style: Style, cwd: str) -> None:
    banner = [
        "███╗   ██╗ ██████╗ ██████╗ ██╗███████╗███████╗██╗███████╗██████╗",
        "████╗  ██║██╔═══██╗██╔══██╗██║██╔════╝██╔════╝██║██╔════╝██╔══██╗",
        "██╔██╗ ██║██║   ██║██║  ██║██║█████╗  █████╗  ██║█████╗  ██████╔╝",
        "██║╚██╗██║██║   ██║██║  ██║██║██╔══╝  ██╔══╝  ██║██╔══╝  ██╔══██╗",
        "██║ ╚████║╚██████╔╝██████╔╝██║██║     ██║     ██║███████╗██║  ██║",
        "╚═╝  ╚═══╝ ╚═════╝ ╚═════╝ ╚═╝╚═╝     ╚═╝     ╚═╝╚══════╝╚═╝  ╚═╝",
        "",
        "paste → patch → done",
        f"Version {VERSION}",
        f"Working Directory: {style.paint(cwd, "36")}",
    ]
    smooth_print(boxed(style, banner, "1;35"), enabled=True, delay=0.004)
    print()


def read_patch(path: str | None) -> bytes:
    if path:
        with open(path, "rb") as patch_file:
            return patch_file.read()

    if sys.stdin.isatty():
        print("     Paste a unified diff below, then press CTRL+D when finished.")
        print("     Press CTRL+D on an empty prompt to quit.")
        print()
    return sys.stdin.buffer.read()


def split_git_header(line: str) -> list[str]:
    try:
        return shlex.split(line)
    except ValueError:
        return line.split()


def clean_patch_path(token: str) -> str | None:
    token = token.strip()
    if not token or token == "/dev/null":
        return None

    # File headers may include timestamps after a tab. Preserve spaces in names.
    token = token.split("\t", 1)[0]

    if token.startswith('"') and token.endswith('"'):
        token = bytes(token[1:-1], "utf-8").decode("unicode_escape")

    if token.startswith("a/") or token.startswith("b/"):
        token = token[2:]

    return token


def patch_paths(patch_text: str) -> Iterable[str]:
    for line in patch_text.splitlines():
        if line.startswith("diff --git "):
            parts = split_git_header(line)
            for token in parts[2:4]:
                path = clean_patch_path(token)
                if path:
                    yield path
        elif line.startswith(("--- ", "+++ ")):
            path = clean_patch_path(line[4:])
            if path:
                yield path
        elif line.startswith(("rename from ", "rename to ", "copy from ", "copy to ")):
            path = clean_patch_path(line.split(" ", 2)[2])
            if path:
                yield path


def unique_patch_paths(patch_data: bytes) -> list[str]:
    patch_text = patch_data.decode("utf-8", errors="replace")
    return sorted(set(patch_paths(patch_text)))


def path_stays_in_cwd(path: str, cwd: str) -> bool:
    cwd_real = Path(cwd).resolve(strict=True)
    target_real = (cwd_real / path).resolve(strict=False)
    return os.path.commonpath([str(cwd_real), str(target_real)]) == str(cwd_real)


def validate_patch_paths(patch_data: bytes, cwd: str) -> None:
    unsafe = []

    for path in unique_patch_paths(patch_data):
        posix_path = PurePosixPath(path)
        if (
            posix_path.is_absolute()
            or ".." in posix_path.parts
            or not path_stays_in_cwd(path, cwd)
        ):
            unsafe.append(path)

    if unsafe:
        bad_paths = ", ".join(sorted(set(unsafe)))
        raise PatchSafetyError(
            f"Patch contains path(s) outside the current directory: {bad_paths}"
        )


def git_apply(
    patch_data: bytes, cwd: str, *options: str
) -> subprocess.CompletedProcess[bytes]:
    command = ["git", "apply", *options, "-"]
    return subprocess.run(
        command,
        input=patch_data,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def git_apply_options(args: argparse.Namespace) -> list[str]:
    options: list[str] = []
    if args.reverse:
        options.append("--reverse")
    if args.three_way:
        options.append("--3way")
    return options


def command_output(result: subprocess.CompletedProcess[bytes]) -> str:
    output = b"\n".join(part for part in (result.stdout, result.stderr) if part)
    return output.decode("utf-8", errors="replace").strip()


def patch_stat(patch_data: bytes, cwd: str, apply_options: list[str]) -> str | None:
    stat_options = [option for option in apply_options if option != "--3way"]
    stat_result = git_apply(patch_data, cwd, "--stat", *stat_options)
    if stat_result.returncode != 0:
        return command_output(stat_result) or "git apply --stat could not read the patch."

    stat_output = command_output(stat_result)
    if stat_output:
        print(stat_output)
    return None


def backup_existing_files(patch_data: bytes, cwd: str) -> Path | None:
    cwd_path = Path(cwd)
    paths = unique_patch_paths(patch_data)
    existing_files = [path for path in paths if (cwd_path / path).is_file()]

    if not existing_files:
        return None

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_dir = cwd_path / BACKUP_ROOT / timestamp
    suffix = 2
    while backup_dir.exists():
        backup_dir = cwd_path / BACKUP_ROOT / f"{timestamp}-{suffix}"
        suffix += 1

    files_dir = backup_dir / "files"
    files_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "created_at": timestamp,
        "cwd": str(cwd_path),
        "files": [],
    }

    for relative_path in existing_files:
        source = cwd_path / relative_path
        destination = files_dir / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        manifest["files"].append(relative_path)

    with open(backup_dir / "manifest.json", "w", encoding="utf-8") as manifest_file:
        json.dump(manifest, manifest_file, indent=2)
        manifest_file.write("\n")

    return backup_dir


def backup_root(cwd: str) -> Path:
    return Path(cwd) / BACKUP_ROOT


def list_backups(cwd: str) -> list[Path]:
    root = backup_root(cwd)
    if not root.exists():
        return []
    return sorted((entry for entry in root.iterdir() if entry.is_dir()), key=lambda p: p.name, reverse=True)


def restore_backup(cwd: str, snapshot: str) -> tuple[bool, str]:
    root = backup_root(cwd)
    backup_dir = root / snapshot
    files_dir = backup_dir / "files"
    manifest_path = backup_dir / "manifest.json"

    if not files_dir.is_dir() or not manifest_path.is_file():
        return False, f"Backup snapshot not found or invalid: {snapshot}"

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return False, f"Could not read backup manifest: {exc}"

    files = manifest.get("files", [])
    if not isinstance(files, list):
        return False, "Backup manifest is invalid: 'files' must be a list."

    restored = 0
    cwd_path = Path(cwd)
    for relative in files:
        if not isinstance(relative, str):
            continue
        source = files_dir / relative
        destination = cwd_path / relative
        if not source.is_file():
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        restored += 1

    return True, f"Restored {restored} file(s) from backup snapshot: {snapshot}"


def git_status(cwd: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def dirty_worktree_warning(cwd: str) -> str | None:
    result = git_status(cwd)
    if result.returncode != 0:
        return None
    if result.stdout.strip():
        changed_count = len(result.stdout.splitlines())
        return (
            f"Warning: Git working tree already has {changed_count} changed "
            "file(s). Consider committing/stashing before applying patches."
        )
    return None


def apply_patch(
    patch_data: bytes,
    cwd: str,
    args: argparse.Namespace,
) -> tuple[str | None, Path | None]:
    if not patch_data.strip():
        return "No patch data received. Nothing was applied.", None

    validate_patch_paths(patch_data, cwd)
    apply_options = git_apply_options(args)

    if args.stat:
        stat_failure = patch_stat(patch_data, cwd, apply_options)
        if stat_failure:
            return stat_failure, None

    check_result = git_apply(patch_data, cwd, "--check", *apply_options)
    if check_result.returncode != 0:
        return command_output(check_result) or "git apply --check rejected the patch.", None

    if args.dry_run:
        return None, None

    backup_dir = None
    if not args.no_backup:
        backup_dir = backup_existing_files(patch_data, cwd)

    apply_result = git_apply(patch_data, cwd, *apply_options)
    if apply_result.returncode != 0:
        return command_output(apply_result) or "git apply failed.", backup_dir

    return None, backup_dir


def print_success(style: Style, args: argparse.Namespace, backup_dir: Path | None) -> None:
    print(style.paint("Success", "32"))
    if args.dry_run:
        print("Patch validates cleanly. No files were changed.")
    else:
        print("Patch applied cleanly in the current working directory.")
        if backup_dir:
            print(f"Backup saved to: {backup_dir}")
        elif not args.no_backup:
            print("No backup was needed because the patch only creates new files.")


def print_failure(style: Style, message: str) -> None:
    print(style.paint("Failed", "31"))
    print(message)


def run_patch(patch_data: bytes, cwd: str, style: Style, args: argparse.Namespace) -> bool:
    if args.stat:
        print("Patch statistics:")
    action = "Checking" if args.dry_run else "Applying"
    mode = " in reverse" if args.reverse else ""
    print(f"{action} patch{mode}…")

    try:
        failure, backup_dir = apply_patch(patch_data, cwd, args)
    except PatchSafetyError as exc:
        print_failure(style, str(exc))
        return False
    except OSError as exc:
        print_failure(style, str(exc))
        return False

    if failure:
        print_failure(style, failure)
        if backup_dir:
            print(f"Backup saved before failure: {backup_dir}")
        return False

    print_success(style, args, backup_dir)
    return True


def run_paste_loop(cwd: str, style: Style, args: argparse.Namespace) -> int:
    while True:
        patch_data = read_patch(None)
        if not patch_data.strip():
            print("No patch data received. Exiting.")
            return 0

        run_patch(patch_data, cwd, style, args)
        print()
        print(style.paint("Ready for another patch.", "36"))
        print()


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    style = Style()
    cwd = os.getcwd()

    if not args.no_clear and sys.stdout.isatty():
        os.system("cls" if os.name == "nt" else "clear")

    header(style, cwd)

    if args.list_backups:
        backups = list_backups(cwd)
        if not backups:
            print("No backups found for this directory.")
            return 0
        rows = ["Available backup snapshots (newest first):", ""]
        for backup in backups:
            manifest = backup / "manifest.json"
            created = backup.name
            if manifest.is_file():
                try:
                    created = json.loads(manifest.read_text(encoding="utf-8")).get("created_at", backup.name)
                except Exception:
                    created = backup.name
            rows.append(f"{backup.name:<24}  UTC: {created}")
        print(boxed(style, rows, "36"))
        return 0

    if args.restore_backup:
        ok, message = restore_backup(cwd, args.restore_backup)
        if ok:
            print(style.paint("Success", "32"))
            print(message)
            return 0
        print_failure(style, message)
        return 1

    if not args.allow_dirty:
        warning = dirty_worktree_warning(cwd)
        if warning:
            print(style.paint(warning, "33"))
            print()

    if not args.patch_file and sys.stdin.isatty():
        return run_paste_loop(cwd, style, args)

    try:
        if args.patch_file:
            print(f"Reading patch file: {style.paint(args.patch_file, '36')}")
        patch_data = read_patch(args.patch_file)
    except FileNotFoundError as exc:
        print_failure(style, f"Could not read patch file: {exc.filename}")
        return 1
    except PermissionError as exc:
        print_failure(style, f"Permission denied while reading patch file: {exc.filename}")
        return 1
    except OSError as exc:
        print_failure(style, str(exc))
        return 1

    return 0 if run_patch(patch_data, cwd, style, args) else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        st = Style()
        print()
        print(boxed(st, ["Interrupted with CTRL+C", "Closing noDIFFier gracefully."], "33"))
        time.sleep(1)
        if st.enabled:
            os.system("cls" if os.name == "nt" else "clear")
        raise SystemExit(130)
