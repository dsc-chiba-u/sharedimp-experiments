"""Record the host: OS, CPU, memory, workflow tools, repository state, pins.

    python python/sharedimp_exp/host_info.py results/raw/01_environment/host.json

Runs on the host (not in a container) with the Python that runs Snakemake, so
it uses the standard library only and is executed as a script, not through the
package. What runs *inside* the images is recorded by env_info.py / env_info.R.
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(os.environ.get("SHAREDIMP_EXP_ROOT", Path(__file__).resolve().parents[2]))


def run(*cmd: str, cwd: Path | None = None) -> str | None:
    try:
        return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return None


def git_head(path: Path) -> str | None:
    return run("git", "rev-parse", "HEAD", cwd=path) if path.exists() else None


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


def docker_daemon() -> dict:
    exe = shutil.which("docker")
    if exe is None:
        return {"usable": False, "reason": "docker executable not found"}
    proc = subprocess.run([exe, "version", "--format", "{{.Server.Version}}"], capture_output=True, text=True)
    if proc.returncode == 0:
        return {"usable": True, "server_version": proc.stdout.strip()}
    return {"usable": False, "reason": (proc.stderr or proc.stdout).strip().splitlines()[-1][:300]}


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
    try:
        import snakemake

        snakemake_version = snakemake.__version__
    except Exception:
        snakemake_version = None
    pins = {"sharedimp_r": os.environ["SHAREDIMP_R_COMMIT"], "sharedimp_py": os.environ["SHAREDIMP_PY_COMMIT"]}
    siblings = {"sharedimp_r": git_head(ROOT.parent / "sharedimp-r"), "sharedimp_py": git_head(ROOT.parent / "sharedimp-py")}
    info = {
        "recorded_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "os": {"pretty_name": os_release.get("PRETTY_NAME"), "kernel": platform.release(), "machine": platform.machine()},
        "cpu": cpu(),
        "logical_cpus": os.cpu_count(),
        "memory_gb": round(mem_kb / 1024**2, 1) if mem_kb else None,
        "threads_used": int(os.environ.get("SHAREDIMP_EXP_THREADS", "1")),
        "snakemake": snakemake_version,
        "singularity": run("singularity", "--version"),
        "host_python": platform.python_version(),
        "docker_daemon": docker_daemon(),
        "experiments_repo": {
            "head": os.environ.get("SHAREDIMP_EXP_COMMIT") or None,
            "code_dirty": os.environ.get("SHAREDIMP_EXP_DIRTY") == "1",
        },
        "pins": pins,
        "images": {
            "r": f"{os.environ['SHAREDIMP_R_IMAGE']}@{os.environ['SHAREDIMP_R_IMAGE_DIGEST']}",
            "python": f"{os.environ['SHAREDIMP_PY_IMAGE']}@{os.environ['SHAREDIMP_PY_IMAGE_DIGEST']}",
        },
        # informational only: the packages come from the images, not from these checkouts
        "sibling_checkout_head": siblings,
        "sibling_head_matches_pin": {k: (None if siblings[k] is None else siblings[k] == pins[k]) for k in pins},
    }
    path = Path(out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(info, indent=2) + "\n")
    print(f"[host] {info['os']['pretty_name']} | {info['cpu'].get('model_name')} | {info['logical_cpus']} logical CPUs | {info['singularity']} | snakemake {snakemake_version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
