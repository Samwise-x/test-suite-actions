#!/usr/bin/env python3
"""Prepare an isolated *local* fixture; remote mutation is explicit and separate."""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

FIXTURE = Path(__file__).resolve().parents[1] / "fixture"
REPO_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def execute(*args: str, cwd: Path) -> str:
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def provision(destination: Path, initialize_git: bool = False, remote_repository: str = "") -> dict:
    if remote_repository and (not initialize_git or not REPO_PATTERN.fullmatch(remote_repository)):
        raise ValueError("--remote-repository requires --init-git and an OWNER/REPO value")
    if destination.exists():
        raise FileExistsError("fixture destination exists; refusing to overwrite " + str(destination))
    shutil.copytree(FIXTURE, destination, symlinks=False)
    report = {"result": "PROVISIONED_LOCAL", "fixture_path": str(destination), "remote_repository": remote_repository or None}
    if initialize_git:
        execute("git", "init", "-q", "-b", "main", str(destination), cwd=destination.parent)
        execute("git", "add", "-A", cwd=destination)
        execute("git", "-c", "user.name=test-suite-actions", "-c", "user.email=test-suite-actions@users.noreply.github.com",
                "commit", "-qm", "test-fixture: establish behavior baseline", cwd=destination)
        report["base_sha"] = execute("git", "rev-parse", "HEAD", cwd=destination)
        if remote_repository:
            execute("git", "remote", "add", "origin", "https://github.com/" + remote_repository + ".git", cwd=destination)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--init-git", action="store_true")
    parser.add_argument("--remote-repository", default="")
    args = parser.parse_args()
    try:
        print(json.dumps(provision(args.output.resolve(), args.init_git, args.remote_repository), sort_keys=True))
        return 0
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print("fixture provisioning failed: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
