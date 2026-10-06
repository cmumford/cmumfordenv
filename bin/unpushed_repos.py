#!/usr/bin/env python3
"""Recursively find Git repositories with unpushed commits.

Directories named by ``--ignore`` are not descended into. A repository is
reported when HEAD contains commits that are not on any remote. Detached
HEAD at a commit already on a remote is not reported. Uncommitted working-tree
changes are reported separately and do not, by themselves, count as unpushed.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def run_git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        capture_output=True,
        text=True,
    )


def find_repos(root: Path, ignore: set[str]) -> list[Path]:
    repos: list[Path] = []
    for dirpath, dirnames, _filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name not in ignore]
        git_dir = Path(dirpath) / ".git"
        if git_dir.is_dir() or git_dir.is_file():
            repos.append(Path(dirpath))
    return repos


def unpushed_count(repo: Path) -> tuple[int, str | None]:
    """Return commits reachable from HEAD but not from any remote.

    Detached HEAD at a commit already on a remote counts as zero. A branch
    with no upstream still counts only commits that no remote has.
    """
    head = run_git(repo, "rev-parse", "--verify", "HEAD")
    if head.returncode != 0:
        return 0, "unborn branch"

    count = run_git(repo, "rev-list", "--count", "HEAD", "--not", "--remotes")
    if count.returncode != 0:
        return 0, count.stderr.strip() or "could not count unpushed commits"
    ahead = int(count.stdout.strip() or "0")

    notes: list[str] = []
    if branch_name(repo) == "HEAD":
        notes.append("detached HEAD")
    upstream = run_git(repo, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    if upstream.returncode != 0:
        notes.append("no upstream")
    return ahead, ", ".join(notes) or None


def dirty(repo: Path) -> bool:
    status = run_git(repo, "status", "--porcelain")
    return bool(status.stdout.strip())


def branch_name(repo: Path) -> str:
    result = run_git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    return result.stdout.strip() or "(unknown)"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "root",
        nargs="?",
        default=".",
        type=Path,
        help="directory to search (default: .)",
    )
    parser.add_argument(
        "--ignore",
        action="append",
        default=[],
        metavar="NAME",
        help="directory name not to descend into (repeatable)",
    )
    parser.add_argument(
        "--dirty",
        action="store_true",
        help="also list repositories with uncommitted changes",
    )
    args = parser.parse_args(argv)

    root = args.root.resolve()
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2

    found = False
    for repo in find_repos(root, set(args.ignore)):
        ahead, note = unpushed_count(repo)
        is_dirty = dirty(repo) if args.dirty else False
        if ahead == 0 and not is_dirty:
            continue

        found = True
        details: list[str] = []
        if ahead:
            label = "commit" if ahead == 1 else "commits"
            details.append(f"{ahead} unpushed {label}")
        if note:
            details.append(note)
        if is_dirty:
            details.append("uncommitted changes")
        details.append(f"branch {branch_name(repo)}")
        print(f"{repo}: {', '.join(details)}")

    if not found:
        print("no repositories with unpushed changes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
