"""Fetch the official UMFI sources at the pinned commits into external/.

    python python/sharedimp_exp/official_fetch.py config/03_official_umfi.json results/raw/03_official_umfi/sources.json

Runs on the host with git (standard library only, executed as a script).
external/ is git-ignored: no official code is copied into this repository or
into any image. The record lists commit, license file and the sha256 of every
file the experiment reads.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def git(*args: str, cwd: Path) -> str:
    return subprocess.run(("git",) + args, cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()


def main(config: str, out: str) -> int:
    cfg = json.loads(Path(config).read_text())
    record = {"fetched_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "sources": {}}
    for name, src in cfg["sources"].items():
        repo, commit = os.environ[f"{src['repo_key']}_REPO"], os.environ[f"{src['repo_key']}_COMMIT"]
        path = Path(src["dir"])
        have = path.is_dir() and (path / ".git").is_dir() and git("rev-parse", "HEAD", cwd=path) == commit
        if not have or git("status", "--porcelain", cwd=path):
            shutil.rmtree(path, ignore_errors=True)
            path.mkdir(parents=True)
            git("init", "-q", cwd=path)
            git("fetch", "-q", "--depth", "1", repo, commit, cwd=path)
            git("checkout", "-q", "FETCH_HEAD", cwd=path)
        head = git("rev-parse", "HEAD", cwd=path)
        if head != commit:
            print(f"error: {name}: got {head}, pinned {commit}", file=sys.stderr)
            return 1
        lic = src["license_file"]
        record["sources"][name] = {
            "repository": repo,
            "commit": head,
            "directory": src["dir"],
            "license_file": lic if lic and (path / lic).is_file() else None,
            "license_first_line": (path / lic).read_text().splitlines()[0].strip() if lic and (path / lic).is_file() else None,
            "top_level_files": sorted(p.name for p in path.iterdir() if p.name != ".git"),
            "files_used": {f: hashlib.sha256((path / f).read_bytes()).hexdigest() for f in src["files"]},
        }
        print(f"[fetch] {name}: {repo} @ {head[:7]} license file: {record['sources'][name]['license_file']}")
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(record, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1], sys.argv[2]))
