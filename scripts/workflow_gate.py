#!/usr/bin/env python3
"""Resolve the fixed GitHub event grammar and verify exact checkout identity."""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path


OPERATIONS = {"deploy", "plan", "refresh-plan", "site-status", "recover-lock"}
MAIN_REF = "refs/heads/main"


class GateFailure(Exception):
    pass


def git_directory(root: Path) -> Path:
    dot_git = root / ".git"
    if dot_git.is_file():
        pointer = dot_git.read_text(encoding="utf-8").strip()
        if not pointer.startswith("gitdir: "):
            raise GateFailure("malformed worktree pointer")
        return (root / pointer.removeprefix("gitdir: ")).resolve()
    return dot_git


def resolve_head(root: Path) -> str:
    directory = git_directory(root)
    head = (directory / "HEAD").read_text(encoding="utf-8").strip()
    if re.fullmatch(r"[0-9a-f]{40}", head):
        return head
    if not head.startswith("ref: "):
        raise GateFailure("checkout HEAD is not a commit or reference")
    reference = head.removeprefix("ref: ")
    search = [directory]
    common_pointer = directory / "commondir"
    if common_pointer.is_file():
        search.append((directory / common_pointer.read_text(encoding="utf-8").strip()).resolve())
    for candidate in search:
        loose = candidate / reference
        if loose.is_file():
            return loose.read_text(encoding="utf-8").strip()
        packed = candidate / "packed-refs"
        if packed.is_file():
            for line in packed.read_text(encoding="utf-8").splitlines():
                if line and not line.startswith(("#", "^")):
                    sha, name = line.split(" ", 1)
                    if name == reference:
                        return sha
    raise GateFailure("checkout reference cannot be resolved")


def resolve_operation(event: str, ref: str, dispatch_operation: str, sha: str, root: Path) -> str:
    if ref != MAIN_REF:
        raise GateFailure("AWS workflow requires refs/heads/main")
    if re.fullmatch(r"[0-9a-f]{40}", sha) is None:
        raise GateFailure("event source identity is invalid")
    if event == "push":
        operation = "deploy"
    elif event == "workflow_dispatch" and dispatch_operation in OPERATIONS:
        operation = dispatch_operation
    else:
        raise GateFailure("unsupported event or operation")
    if resolve_head(root) != sha:
        raise GateFailure("checkout does not match the event source identity")
    return operation


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--github-output", type=Path, required=True)
    args = parser.parse_args()
    try:
        operation = resolve_operation(
            os.environ.get("GITHUB_EVENT_NAME", ""),
            os.environ.get("GITHUB_REF", ""),
            os.environ.get("INPUT_OPERATION", ""),
            os.environ.get("GITHUB_SHA", ""),
            args.root.resolve(),
        )
        with args.github_output.open("a", encoding="utf-8") as stream:
            stream.write(f"operation={operation}\n")
    except (GateFailure, OSError, ValueError):
        print("ERROR: workflow event, ref, operation, or checkout identity was rejected", file=sys.stderr)
        return 1
    print("Workflow event and exact checkout identity accepted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
