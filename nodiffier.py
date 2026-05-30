#!/usr/bin/env python3

# =========================================================
# noDIFFier
# AI patch workflow tool for Linux terminals.
#
# Copyright (c) 2026 WastelandSYS
# Licensed under the GNU General Public License v3.0
# SPDX-License-Identifier: GPL-3.0-only
# =========================================================

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
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Iterable

try:
    from wcwidth import wcswidth
except ImportError:  # Keep noDIFFier usable on minimal systems.
    wcswidth = None

APP_NAME = "noDIFFier"
VERSION = "0.5.0"
BACKUP_ROOT = ".nodiffier-backups"
HISTORY_ROOT = ".nodiffier-history"

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def visible_len(text: str) -> int:
    clean = ANSI_RE.sub("", text)
    if wcswidth is not None:
        width = wcswidth(clean)
        return width if width >= 0 else len(clean)
    return len(clean)


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
        char = text[i]
        char_width = visible_len(char)
        if visible + char_width > max_visible:
            break
        out.append(char)
        visible += char_width
        i += 1
    return "".join(out)


def pad_visible(text: str, width: int) -> str:
    clipped = truncate_visible(text, width)
    padding = max(0, width - visible_len(clipped))
    return clipped + (" " * padding)


def center_visible(text: str, width: int) -> str:
    length = visible_len(text)
    if length >= width:
        return text
    left = (width - length) // 2
    right = width - length - left
    return (" " * left) + text + (" " * right)


class PatchSafetyError(ValueError):
    """Raised when a patch references a path outside the working directory."""


@dataclass
class SessionStats:
    started_at: float = field(default_factory=time.monotonic)
    patches_applied: int = 0
    files_modified: set[str] = field(default_factory=set)
    backups_created: int = 0
    failed_patches: int = 0
    validation_failures: int = 0

    def duration(self) -> str:
        seconds = int(time.monotonic() - self.started_at)
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours}h {minutes}m {seconds}s"
        if minutes:
            return f"{minutes}m {seconds}s"
        return f"{seconds}s"

    def lines(self) -> list[str]:
        return [
            "Session Summary",
            "",
            f"Patches Applied     : {self.patches_applied}",
            f"Files Modified      : {len(self.files_modified)}",
            f"Backups Created     : {self.backups_created}",
            f"Failed Patches      : {self.failed_patches}",
            f"Validation Failures : {self.validation_failures}",
            f"Duration            : {self.duration()}",
        ]


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
            "Apply unified .diff/.patch files or pasted diffs to the current project. "
            "Run without files to paste diffs; press CTRL+D after each one."
        ),
    )
    cli.add_argument(
        "patch_files",
        nargs="*",
        help="Optional .diff or .patch file(s) to apply sequentially.",
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
        "--force",
        dest="allow_dirty",
        action="store_true",
        help="Do not warn when the current Git working tree already has changes.",
    )
    cli.add_argument(
        "--yes",
        action="store_true",
        help="Automatically accept patch preview and repository-root prompts.",
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
    cli.add_argument(
        "--rollback-last",
        action="store_true",
        help="Restore the newest available noDIFFier backup snapshot.",
    )
    cli.add_argument(
        "--rollback",
        action="store_true",
        help="Choose a noDIFFier backup snapshot to restore from an interactive list.",
    )
    cli.add_argument("--version", action="version", version=f"{APP_NAME} {VERSION}")
    return cli


def git_branch(cwd: str) -> str:
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    branch = result.stdout.decode("utf-8", errors="replace").strip()
    if result.returncode == 0 and branch:
        return branch
    return "N/A"


def is_git_repo(cwd: str) -> bool:
    result = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return result.returncode == 0


def display_path(path: str) -> str:
    try:
        return str(Path(path).expanduser().resolve()).replace(str(Path.home()), "~", 1)
    except OSError:
        return path


def header(style: Style, cwd: str, stats: SessionStats, backups_enabled: bool) -> None:
    width = min(terminal_width(), 140)
    inner = width - 4
    logo = [
        "███╗   ██╗ ██████╗ ██████╗ ██╗███████╗███████╗██╗███████╗██████╗",
        "████╗  ██║██╔═══██╗██╔══██╗██║██╔════╝██╔════╝██║██╔════╝██╔══██╗",
        "██╔██╗ ██║██║   ██║██║  ██║██║█████╗  █████╗  ██║█████╗  ██████╔╝",
        "██║╚██╗██║██║   ██║██║  ██║██║██╔══╝  ██╔══╝  ██║██╔══╝  ██╔══██╗",
        "██║ ╚████║╚██████╔╝██████╔╝██║██║     ██║     ██║███████╗██║  ██║",
        "╚═╝  ╚═══╝ ╚═════╝ ╚═════╝ ╚═╝╚═╝     ╚═╝     ╚═╝╚══════╝╚═╝  ╚═╝",
    ]
    logo_width = max(visible_len(line) for line in logo)
    lines = [center_visible(pad_visible(line, logo_width), inner) for line in logo]
    lines.extend(
        [
            "",
            center_visible("paste → patch → done", inner),
            center_visible(f"Version {VERSION}", inner),
            "",
            f"Working Directory : {style.paint(display_path(cwd), '36')}",
            f"Git Repository    : {'Yes' if is_git_repo(cwd) else 'No'}",
            f"Branch            : {git_branch(cwd)}",
            f"Backups           : {'Disabled' if backups_enabled is False else 'Enabled'}",
            f"Session Patches   : {stats.patches_applied}",
            f"Files Modified    : {len(stats.files_modified)}",
        ]
    )
    smooth_print(boxed(style, lines, "1;35"), enabled=True, delay=0.004)
    print()


def prompt_yes_no(question: str, default: bool, assume_yes: bool = False) -> bool:
    if assume_yes:
        print(f"{question} {'[Y/n]' if default else '[y/N]'} y")
        return True
    if not sys.stdin.isatty():
        return default
    suffix = "[Y/n]" if default else "[y/N]"
    answer = input(f"{question} {suffix} ").strip().lower()
    if not answer:
        return default
    return answer in {"y", "yes"}


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
        if posix_path.is_absolute() or ".." in posix_path.parts or not path_stays_in_cwd(path, cwd):
            unsafe.append(path)
    if unsafe:
        bad_paths = ", ".join(sorted(set(unsafe)))
        raise PatchSafetyError(f"Patch contains path(s) outside the current directory: {bad_paths}")


def git_apply(patch_data: bytes, cwd: str, *options: str) -> subprocess.CompletedProcess[bytes]:
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


def diagnostics() -> str:
    return (
        "Possible Causes:\n"
        "* File changed since patch was generated\n"
        "* Patch copied incompletely\n"
        "* Wrong project directory\n"
        "* Context lines no longer match\n"
        "* Target file missing"
    )


def with_diagnostics(message: str) -> str:
    return f"{message}\n\n{diagnostics()}"


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
    manifest = {"created_at": timestamp, "cwd": str(cwd_path), "files": []}

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


def save_history(patch_data: bytes, cwd: str, affected_files: list[str]) -> Path:
    history_root = Path(cwd) / HISTORY_ROOT
    history_root.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    safe_name = timestamp.replace(":", "").replace("+", "Z")
    history_path = history_root / f"{safe_name}.patch"
    suffix = 2
    while history_path.exists():
        history_path = history_root / f"{safe_name}-{suffix}.patch"
        suffix += 1

    metadata = [
        "# noDIFFier history entry",
        f"# timestamp: {timestamp}",
        "# status: success",
        "# affected_files:",
    ]
    metadata.extend(f"# - {path}" for path in affected_files)
    metadata.extend(["", ""])
    with open(history_path, "wb") as history_file:
        history_file.write(("\n".join(metadata)).encode("utf-8"))
        history_file.write(patch_data)
    return history_path


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


def print_backups(cwd: str, style: Style) -> int:
    backups = list_backups(cwd)
    if not backups:
        print("No backups found for this directory.")
        return 0
    rows = ["Available backup snapshots (newest first):", ""]
    for backup in backups:
        manifest = backup / "manifest.json"
        created = backup.name
        file_count = "?"
        if manifest.is_file():
            try:
                data = json.loads(manifest.read_text(encoding="utf-8"))
                created = data.get("created_at", backup.name)
                files = data.get("files", [])
                file_count = str(len(files)) if isinstance(files, list) else "?"
            except (json.JSONDecodeError, OSError):
                created = backup.name
        rows.append(f"{backup.name:<24}  UTC: {created}  Files: {file_count}")
    print(boxed(style, rows, "36"))
    return 0


def confirm_and_restore(cwd: str, snapshot: str, style: Style, args: argparse.Namespace) -> int:
    if not (backup_root(cwd) / snapshot).exists():
        print_failure(style, f"Backup snapshot not found or invalid: {snapshot}")
        return 1
    if not prompt_yes_no(f"Restore backup snapshot '{snapshot}'?", False, args.yes):
        print("Restore cancelled.")
        return 1
    ok, message = restore_backup(cwd, snapshot)
    if ok:
        print(style.paint("Success", "32"))
        print(message)
        return 0
    print_failure(style, message)
    return 1


def rollback_interactive(cwd: str, style: Style, args: argparse.Namespace) -> int:
    backups = list_backups(cwd)
    if not backups:
        print("No backups found for this directory.")
        return 1
    print("Available backup snapshots:")
    for index, backup in enumerate(backups, 1):
        print(f"{index}. {backup.name}")
    if not sys.stdin.isatty():
        print("Interactive rollback requires a terminal. Use --restore-backup SNAPSHOT instead.")
        return 1
    choice = input("Choose snapshot number to restore: ").strip()
    if not choice.isdigit() or not 1 <= int(choice) <= len(backups):
        print_failure(style, "Invalid backup selection.")
        return 1
    return confirm_and_restore(cwd, backups[int(choice) - 1].name, style, args)


def git_status(cwd: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def check_dirty_worktree(cwd: str, style: Style, args: argparse.Namespace) -> bool:
    if args.allow_dirty:
        return True
    result = git_status(cwd)
    if result.returncode != 0 or not result.stdout.strip():
        return True
    changed_count = len(result.stdout.splitlines())
    print(style.paint("Warning:", "33"))
    print("Repository contains uncommitted changes.")
    print(f"Changed files detected: {changed_count}")
    if not sys.stdin.isatty():
        print("No interactive terminal detected; continuing with dirty worktree warning.")
        print()
        return True
    print()
    return prompt_yes_no("Continue?", False)


def detect_git_root(cwd: str) -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        return None
    root = result.stdout.decode("utf-8", errors="replace").strip()
    return root or None


def choose_working_directory(original_cwd: str, args: argparse.Namespace) -> str:
    git_root = detect_git_root(original_cwd)
    if not git_root:
        return original_cwd
    try:
        same_dir = Path(git_root).resolve() == Path(original_cwd).resolve()
    except OSError:
        same_dir = git_root == original_cwd
    if same_dir:
        return original_cwd
    print("Git repository detected:")
    print(display_path(git_root))
    if not sys.stdin.isatty():
        print("No interactive terminal detected; applying patches from repository root.")
        return git_root
    if prompt_yes_no("Apply patch from repository root?", True, args.yes):
        return git_root
    return original_cwd


@dataclass
class ApplyResult:
    failure: str | None
    backup_dir: Path | None
    affected_files: list[str]
    validation_failed: bool = False


def apply_patch(patch_data: bytes, cwd: str, args: argparse.Namespace, stats: SessionStats) -> ApplyResult:
    if not patch_data.strip():
        return ApplyResult("No patch data received. Nothing was applied.", None, [], True)

    affected_files = unique_patch_paths(patch_data)
    validate_patch_paths(patch_data, cwd)
    apply_options = git_apply_options(args)

    if args.stat:
        stat_failure = patch_stat(patch_data, cwd, apply_options)
        if stat_failure:
            return ApplyResult(with_diagnostics(stat_failure), None, affected_files, True)

    print_patch_preview(affected_files)

    check_result = git_apply(patch_data, cwd, "--check", *apply_options)
    if check_result.returncode != 0:
        message = command_output(check_result) or "git apply --check rejected the patch."
        return ApplyResult(with_diagnostics(message), None, affected_files, True)

    if args.dry_run:
        return ApplyResult(None, None, affected_files)

    if not prompt_yes_no("Proceed?", True, args.yes):
        return ApplyResult("Patch cancelled by user.", None, affected_files, False)

    backup_dir = None
    if not args.no_backup:
        backup_dir = backup_existing_files(patch_data, cwd)
        if backup_dir:
            stats.backups_created += 1

    apply_result = git_apply(patch_data, cwd, *apply_options)
    if apply_result.returncode != 0:
        message = command_output(apply_result) or "git apply failed."
        return ApplyResult(with_diagnostics(message), backup_dir, affected_files, False)

    save_history(patch_data, cwd, affected_files)
    return ApplyResult(None, backup_dir, affected_files)


def print_patch_preview(affected_files: list[str]) -> None:
    print("Patch Preview")
    print()
    print("Files To Be Modified:")
    print()
    if affected_files:
        for path in affected_files:
            print(f"* {path}")
    else:
        print("* No file paths detected")
    print()


def print_success(style: Style, args: argparse.Namespace, backup_dir: Path | None) -> None:
    print(style.paint("Success", "32"))
    if args.dry_run:
        print("Dry Run Successful")
        print("No files were changed.")
    else:
        print("Patch applied cleanly in the current working directory.")
        if backup_dir:
            print(f"Backup saved to: {backup_dir}")
        elif not args.no_backup:
            print("No backup was needed because the patch only creates new files.")


def print_failure(style: Style, message: str) -> None:
    print(style.paint("Failed", "31"))
    print(message)


def run_patch(patch_data: bytes, cwd: str, style: Style, args: argparse.Namespace, stats: SessionStats) -> bool:
    if args.stat:
        print("Patch statistics:")
    action = "Checking" if args.dry_run else "Applying"
    mode = " in reverse" if args.reverse else ""
    print(f"{action} patch{mode}…")

    try:
        result = apply_patch(patch_data, cwd, args, stats)
    except PatchSafetyError as exc:
        stats.failed_patches += 1
        stats.validation_failures += 1
        print_failure(style, with_diagnostics(str(exc)))
        return False
    except OSError as exc:
        stats.failed_patches += 1
        print_failure(style, str(exc))
        return False

    if result.failure:
        stats.failed_patches += 1
        if result.validation_failed:
            stats.validation_failures += 1
        print_failure(style, result.failure)
        if result.backup_dir:
            print(f"Backup saved before failure: {result.backup_dir}")
        return False

    if not args.dry_run:
        stats.patches_applied += 1
        stats.files_modified.update(result.affected_files)
    print_success(style, args, result.backup_dir)
    return True


def print_session_summary(style: Style, stats: SessionStats) -> None:
    print()
    print(boxed(style, stats.lines(), "36"))


def run_paste_loop(cwd: str, style: Style, args: argparse.Namespace, stats: SessionStats) -> int:
    while True:
        patch_data = read_patch(None)
        if not patch_data.strip():
            print("No patch data received. Exiting.")
            print_session_summary(style, stats)
            return 0

        if not check_dirty_worktree(cwd, style, args):
            stats.failed_patches += 1
            print("Patch skipped due to dirty worktree.")
        else:
            run_patch(patch_data, cwd, style, args, stats)
        print()
        print(style.paint("Ready for another patch.", "36"))
        print()


def run_patch_files(
    patch_files: list[str],
    original_cwd: str,
    cwd: str,
    style: Style,
    args: argparse.Namespace,
    stats: SessionStats,
) -> int:
    successful = 0
    failed = 0
    batch_mode = len(patch_files) > 1
    for index, patch_file in enumerate(patch_files, 1):
        patch_path = Path(patch_file)
        if not patch_path.is_absolute():
            patch_path = Path(original_cwd) / patch_file
        print(f"Reading patch file: {style.paint(str(patch_file), '36')}")
        try:
            patch_data = read_patch(str(patch_path))
        except FileNotFoundError as exc:
            failed += 1
            stats.failed_patches += 1
            print_failure(style, f"Could not read patch file: {exc.filename}")
            if batch_mode:
                print(f"Patch {index}: Failed")
            continue
        except PermissionError as exc:
            failed += 1
            stats.failed_patches += 1
            print_failure(style, f"Permission denied while reading patch file: {exc.filename}")
            if batch_mode:
                print(f"Patch {index}: Failed")
            continue
        except OSError as exc:
            failed += 1
            stats.failed_patches += 1
            print_failure(style, str(exc))
            if batch_mode:
                print(f"Patch {index}: Failed")
            continue

        if not check_dirty_worktree(cwd, style, args):
            failed += 1
            stats.failed_patches += 1
            print("Patch skipped due to dirty worktree.")
            if batch_mode:
                print(f"Patch {index}: Failed")
            continue

        if run_patch(patch_data, cwd, style, args, stats):
            successful += 1
            if batch_mode:
                print(f"Patch {index}: Success")
        else:
            failed += 1
            if batch_mode:
                print(f"Patch {index}: Failed")
        print()

    if batch_mode:
        print("Summary:")
        print(f"{successful} Successful")
        print(f"{failed} Failed")
    print_session_summary(style, stats)
    return 0 if failed == 0 else 1


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    style = Style()
    stats = SessionStats()
    original_cwd = os.getcwd()

    if not args.no_clear and sys.stdout.isatty():
        os.system("cls" if os.name == "nt" else "clear")

    cwd = choose_working_directory(original_cwd, args)
    header(style, cwd, stats, not args.no_backup)

    if args.list_backups:
        return print_backups(cwd, style)

    if args.restore_backup:
        return confirm_and_restore(cwd, args.restore_backup, style, args)

    if args.rollback_last:
        backups = list_backups(cwd)
        if not backups:
            print("No backups found for this directory.")
            return 1
        return confirm_and_restore(cwd, backups[0].name, style, args)

    if args.rollback:
        return rollback_interactive(cwd, style, args)

    if not args.patch_files and sys.stdin.isatty():
        return run_paste_loop(cwd, style, args, stats)

    if args.patch_files:
        return run_patch_files(args.patch_files, original_cwd, cwd, style, args, stats)

    patch_data = read_patch(None)
    if not check_dirty_worktree(cwd, style, args):
        stats.failed_patches += 1
        print("Patch skipped due to dirty worktree.")
        print_session_summary(style, stats)
        return 1
    ok = run_patch(patch_data, cwd, style, args, stats)
    print_session_summary(style, stats)
    return 0 if ok else 1


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
