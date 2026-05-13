"""Command-line interface for noDIFFier."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Iterable, Optional, Sequence

from . import __version__

APP_NAME = "noDIFFier"


class PatchSafetyError(ValueError):
    """Raised when a patch advertises a path outside the working directory."""


class Style:
    """Small ANSI styling helper that stays quiet when output is redirected."""

    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled

    def paint(self, text: str, code: str) -> str:
        if not self.enabled:
            return text
        return f"\033[{code}m{text}\033[0m"

    @property
    def title(self) -> str:
        return "1;35"

    @property
    def accent(self) -> str:
        return "36"

    @property
    def ok(self) -> str:
        return "32"

    @property
    def error(self) -> str:
        return "31"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=APP_NAME,
        description=(
            "Apply a unified .diff/.patch to the current working directory. "
            "Run without an argument to paste a diff, then press CTRL+D."
        ),
    )
    parser.add_argument(
        "patch_file",
        nargs="?",
        help="Path to a .diff or .patch file to apply in the current directory.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def supports_color() -> bool:
    return sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


def print_header(style: Style, cwd: str) -> None:
    line = "─" * 36
    print(style.paint(f"╭{line}╮", style.accent))
    print(style.paint(f"│  ✨ {APP_NAME} patch helper{' ' * 12}│", style.title))
    print(style.paint(f"╰{line}╯", style.accent))
    print(f"Working directory: {style.paint(cwd, style.accent)}")
    print()


def read_patch_from_file(path: str) -> bytes:
    with open(path, "rb") as patch_file:
        return patch_file.read()


def read_patch_from_stdin() -> bytes:
    if sys.stdin.isatty():
        print("Paste a unified diff below, then press CTRL+D when finished.")
        print()
    return sys.stdin.buffer.read()


def decode_path_token(token: str) -> Optional[str]:
    """Return a patch path from a header token, or None for /dev/null."""
    token = token.strip()
    if not token or token == "/dev/null":
        return None

    # For ---/+++ headers, ignore timestamps after a tab. Git diff paths with
    # spaces are tab-separated from metadata, so spaces are preserved here.
    token = token.split("\t", 1)[0]

    if token.startswith('"') and token.endswith('"'):
        # Git may quote unusual filenames. unicode_escape handles common C-style
        # backslash escapes well enough for validation without changing files.
        token = bytes(token[1:-1], "utf-8").decode("unicode_escape")

    if token.startswith("a/") or token.startswith("b/"):
        token = token[2:]

    return token


def iter_patch_paths(patch_text: str) -> Iterable[str]:
    for line in patch_text.splitlines():
        if line.startswith("diff --git "):
            parts = line.split()
            for token in parts[2:4]:
                path = decode_path_token(token)
                if path is not None:
                    yield path
        elif line.startswith(("--- ", "+++ ")):
            path = decode_path_token(line[4:])
            if path is not None:
                yield path
        elif line.startswith(("rename from ", "rename to ", "copy from ", "copy to ")):
            path = decode_path_token(line.split(" ", 2)[2])
            if path is not None:
                yield path


def path_resolves_inside_cwd(path: str, cwd: str) -> bool:
    cwd_real = Path(cwd).resolve(strict=True)
    target_real = (cwd_real / path).resolve(strict=False)
    return os.path.commonpath([str(cwd_real), str(target_real)]) == str(cwd_real)


def ensure_patch_stays_in_cwd(patch_data: bytes, cwd: str) -> None:
    patch_text = patch_data.decode("utf-8", errors="replace")
    unsafe_paths = []

    for path in iter_patch_paths(patch_text):
        posix_path = PurePosixPath(path)
        if (
            posix_path.is_absolute()
            or ".." in posix_path.parts
            or not path_resolves_inside_cwd(path, cwd)
        ):
            unsafe_paths.append(path)

    if unsafe_paths:
        unique_paths = ", ".join(sorted(set(unsafe_paths)))
        raise PatchSafetyError(
            "Patch contains path(s) outside the current directory: " + unique_paths
        )


def run_git_apply(
    patch_data: bytes, cwd: str, check_only: bool = False
) -> subprocess.CompletedProcess[bytes]:
    command = ["git", "apply"]
    if check_only:
        command.append("--check")
    command.append("-")
    return subprocess.run(
        command,
        input=patch_data,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def combined_output(result: subprocess.CompletedProcess[bytes]) -> str:
    output = b"\n".join(part for part in (result.stdout, result.stderr) if part)
    return output.decode("utf-8", errors="replace").strip()


def apply_patch(patch_data: bytes, cwd: str) -> Optional[str]:
    if not patch_data.strip():
        return "No patch data received. Nothing was applied."

    ensure_patch_stays_in_cwd(patch_data, cwd)

    check_result = run_git_apply(patch_data, cwd, check_only=True)
    if check_result.returncode != 0:
        return combined_output(check_result) or "git apply --check rejected the patch."

    apply_result = run_git_apply(patch_data, cwd, check_only=False)
    if apply_result.returncode != 0:
        return combined_output(apply_result) or "git apply failed."

    return None


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    style = Style(supports_color())
    cwd = os.getcwd()

    print_header(style, cwd)

    try:
        if args.patch_file:
            print(f"Reading patch file: {style.paint(args.patch_file, style.accent)}")
            patch_data = read_patch_from_file(args.patch_file)
        else:
            patch_data = read_patch_from_stdin()

        print("Applying patch…")
        failure_reason = apply_patch(patch_data, cwd)
    except FileNotFoundError as exc:
        print(style.paint("Failed", style.error))
        print(f"Could not read patch file: {exc.filename}")
        return 1
    except PermissionError as exc:
        print(style.paint("Failed", style.error))
        print(f"Permission denied while reading patch file: {exc.filename}")
        return 1
    except PatchSafetyError as exc:
        print(style.paint("Failed", style.error))
        print(str(exc))
        return 1
    except OSError as exc:
        print(style.paint("Failed", style.error))
        print(str(exc))
        return 1

    if failure_reason is not None:
        print(style.paint("Failed", style.error))
        print(failure_reason)
        return 1

    print(style.paint("Success", style.ok))
    print("Patch applied cleanly in the current working directory.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
