"""Record OS, CPU, repository state and the package pins; verify the pins.

python -m sharedimp_exp.system_info results/raw/01_environment/system.json

Exit status 1 if the installed sharedimp packages are not the commits pinned
in config/pins.env (i.e. scripts/00_install_sharedimp.sh has to be re-run).
"""

from __future__ import annotations

import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from .common import ROOT, read_json, write_json


def run(*cmd: str, cwd: Path | None = None) -> str | None:
    try:
        return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return None


def git_state(path: Path) -> dict | None:
    head = run("git", "rev-parse", "HEAD", cwd=path) if path.exists() else None
    if head is None:
        return None
    return {
        "head": head,
        "dirty": bool(run("git", "status", "--porcelain", cwd=path)),
        "branch": run("git", "rev-parse", "--abbrev-ref", "HEAD", cwd=path),
    }


def cpu() -> dict:
    """CPU description from /proc/cpuinfo (lscpu output is locale dependent)."""
    info: dict = {"architecture": platform.machine()}
    path = Path("/proc/cpuinfo")
    if path.exists():
        text = path.read_text()
        models = [line.split(":", 1)[1].strip() for line in text.splitlines() if line.startswith("model name")]
        cores = {
            tuple(line.split(":", 1)[1].strip() for line in block.splitlines() if line.startswith(("physical id", "core id")))
            for block in text.strip().split("\n\n")
        }
        info.update(model_name=models[0] if models else None, logical_cpus=len(models), physical_cores=len(cores))
    return info


def main(out: str) -> int:
    os_release = {}
    if Path("/etc/os-release").exists():
        for line in Path("/etc/os-release").read_text().splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                os_release[k] = v.strip('"')
    mem_kb = None
    if Path("/proc/meminfo").exists():
        mem_kb = int(Path("/proc/meminfo").read_text().split("MemTotal:")[1].split()[0])
    mpath = Path(os.environ.get("SHAREDIMP_INSTALL_MANIFEST", ""))
    manifest = read_json(mpath) if mpath.is_file() else None
    pins = {"sharedimp_r": os.environ["SHAREDIMP_R_COMMIT"], "sharedimp_py": os.environ["SHAREDIMP_PY_COMMIT"]}
    siblings = {"sharedimp_r": git_state(ROOT.parent / "sharedimp-r"), "sharedimp_py": git_state(ROOT.parent / "sharedimp-py")}
    problems = []
    for key, pin in pins.items():
        got = (manifest or {}).get(key, {}).get("commit")
        if got != pin:
            problems.append(f"{key}: installed commit {got} != pinned {pin}")
    info = {
        "recorded_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "os": {"pretty_name": os_release.get("PRETTY_NAME"), "kernel": platform.release(), "machine": platform.machine()},
        "cpu": cpu(),
        "logical_cpus": os.cpu_count(),
        "memory_gb": round(mem_kb / 1024**2, 1) if mem_kb else None,
        "threads_used": int(os.environ.get("SHAREDIMP_EXP_THREADS", "1")),
        "conda_env": Path(os.environ.get("SHAREDIMP_EXP_ENV", "")).name,
        "in_container": Path("/.dockerenv").exists(),
        "experiments_repo": git_state(ROOT),
        "pins": pins,
        "install_manifest": manifest,
        "installed_matches_pins": not problems,
        "sibling_checkouts": siblings,
        "sibling_head_matches_pin": {
            k: (None if siblings[k] is None else siblings[k]["head"] == pins[k]) for k in pins
        },
    }
    write_json(info, Path(out))
    print(f"[system] {info['os']['pretty_name']} | {info['cpu'].get('model_name')} | {info['logical_cpus']} logical CPUs | threads used: {info['threads_used']}")
    for p in problems:
        print(f"[system] ERROR {p}", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
