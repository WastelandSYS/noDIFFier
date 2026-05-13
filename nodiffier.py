#!/usr/bin/env python3
"""noDIFFier: apply unified diffs to the current working directory."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path, PurePosixPath

APP_NAME = "noDIFFier"
VERSION = "0.2.0"


class PatchSafetyError(ValueError):
    """Raised when a patch references a path outside the working directory."""


class Style:
    def __init__(self) -> None:
        self.enabled = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None

    def paint(self, text: str, code: str) -> str:
        if not self.enabled:
            return text
        return f"\033[{code}m{text}\033[0m"


def parser() -> argparse.ArgumentParser:
    cli = argparse.ArgumentParser(
        prog=APP_NAME,
        description=(
            "Apply a unified .diff/.patch to the current directory. "
            "Run without a file to paste a diff, then press CTRL+D."
        ),
    )
    cli.add_argument(
        "patch_file",
        nargs="?",
        help="Optional .diff or .patch file to apply to the current directory.",
    )
    cli.add_argument("--version", action="version", version=f"{APP_NAME} {VERSION}")
    return cli


def header(style: Style, cwd: str) -> None:

    banner = r"""
  ███╗   ██╗ ██████╗ ██████╗ ██╗███████╗███████╗██╗███████╗██████╗
  ████╗  ██║██╔═══██╗██╔══██╗██║██╔════╝██╔════╝██║██╔════╝██╔══██╗
  ██╔██╗ ██║██║   ██║██║  ██║██║█████╗  █████╗  ██║█████╗  ██████╔╝
  ██║╚██╗██║██║   ██║██║  ██║██║██╔══╝  ██╔══╝  ██║██╔══╝  ██╔══██╗
  ██║ ╚████║╚██████╔╝██████╔╝██║██║     ██║     ██║███████╗██║  ██║
  ╚═╝  ╚═══╝ ╚═════╝ ╚═════╝ ╚═╝╚═╝     ╚═╝     ╚═╝╚══════╝╚═╝  ╚═╝
"""

    print(style.paint(banner, "1;35"))

    print(style.paint(
        "                       paste → patch → done",
        "36"
    ))

    print(style.paint(
        f"                          Version {VERSION}",
        "90"
    ))

    print()

    print(
        f"     {style.paint('Working Directory:', '1;36')} "
        f"{cwd}"
    )

    print()


def read_patch(path: str | None) -> bytes:
    if path:
        with open(path, "rb") as patch_file:
            return patch_file.read()

    if sys.stdin.isatty():
        print("     Paste a unified diff below, then press CTRL+D when finished.")
        print()
    return sys.stdin.buffer.read()


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


def patch_paths(patch_text: str):
    for line in patch_text.splitlines():
        if line.startswith("diff --git "):
            parts = line.split()
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


def path_stays_in_cwd(path: str, cwd: str) -> bool:
    cwd_real = Path(cwd).resolve(strict=True)
    target_real = (cwd_real / path).resolve(strict=False)
    return os.path.commonpath([str(cwd_real), str(target_real)]) == str(cwd_real)


def validate_patch_paths(patch_data: bytes, cwd: str) -> None:
    patch_text = patch_data.decode("utf-8", errors="replace")
    unsafe = []

    for path in patch_paths(patch_text):
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
    patch_data: bytes, cwd: str, check_only: bool
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


def command_output(result: subprocess.CompletedProcess[bytes]) -> str:
    output = b"\n".join(part for part in (result.stdout, result.stderr) if part)
    return output.decode("utf-8", errors="replace").strip()


def apply_patch(patch_data: bytes, cwd: str) -> str | None:
    if not patch_data.strip():
        return "No patch data received. Nothing was applied."

    validate_patch_paths(patch_data, cwd)

    check_result = git_apply(patch_data, cwd, check_only=True)
    if check_result.returncode != 0:
        return command_output(check_result) or "git apply --check rejected the patch."

    apply_result = git_apply(patch_data, cwd, check_only=False)
    if apply_result.returncode != 0:
        return command_output(apply_result) or "git apply failed."

    return None


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    style = Style()
    cwd = os.getcwd()

    header(style, cwd)

    try:
        if args.patch_file:
            print(f"Reading patch file: {style.paint(args.patch_file, '36')}")
        patch_data = read_patch(args.patch_file)
        print("Applying patch…")
        failure = apply_patch(patch_data, cwd)
    except FileNotFoundError as exc:
        print(style.paint("Failed", "31"))
        print(f"Could not read patch file: {exc.filename}")
        return 1
    except PermissionError as exc:
        print(style.paint("Failed", "31"))
        print(f"Permission denied while reading patch file: {exc.filename}")
        return 1
    except PatchSafetyError as exc:
        print(style.paint("Failed", "31"))
        print(exc)
        return 1
    except OSError as exc:
        print(style.paint("Failed", "31"))
        print(exc)
        return 1

    if failure:
        print(style.paint("Failed", "31"))
        print(failure)
        return 1

    print(style.paint("Success", "32"))
    print("Patch applied cleanly in the current working directory.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
