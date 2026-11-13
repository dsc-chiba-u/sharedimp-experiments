# Settings shared by every workflow/NN_*.smk (included, never run on its own).
#
# Every rule that computes something runs inside a container image through
# Singularity (`snakemake --use-singularity`). The images are the published
# package images, referenced by the digests pinned in config/pins.env.
import json
import subprocess
import sys
from snakemake.utils import min_version

min_version("8.10.0")


def read_pins(path="config/pins.env"):
    pins = {}
    for line in open(path):
        line = line.strip()
        if line and not line.startswith("#"):
            key, value = line.split("=", 1)
            pins[key] = value
    return pins


def git(*args):
    try:
        return subprocess.run(("git",) + args, capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return ""


def job_ids(jobs_file):
    return [job["id"] for job in json.load(open(jobs_file))["jobs"]]


PINS = read_pins()
R_IMAGE = f"{PINS['SHAREDIMP_R_IMAGE']}@{PINS['SHAREDIMP_R_IMAGE_DIGEST']}"
PY_IMAGE = f"{PINS['SHAREDIMP_PY_IMAGE']}@{PINS['SHAREDIMP_PY_IMAGE_DIGEST']}"
R_CONTAINER = f"docker://{R_IMAGE}"
PY_CONTAINER = f"docker://{PY_IMAGE}"

# One thread per process unless overridden with `--config threads=N`.
THREADS = int(config.get("threads", 1))

# State of this repository's code when the workflow starts. results/ is
# excluded so that regenerating results does not make the code look modified.
EXP_COMMIT = git("rev-parse", "HEAD")
EXP_DIRTY = bool(git("status", "--porcelain", "--", ".", ":(exclude)results"))

ENV = {
    "SHAREDIMP_EXP_ROOT": "$PWD",
    "SHAREDIMP_EXP_COMMIT": EXP_COMMIT,
    "SHAREDIMP_EXP_DIRTY": str(int(EXP_DIRTY)),
    "SHAREDIMP_EXP_THREADS": THREADS,
    "OMP_NUM_THREADS": THREADS,
    "OPENBLAS_NUM_THREADS": THREADS,
    "MKL_NUM_THREADS": THREADS,
    "R_RANGER_NUM_THREADS": THREADS,
    "SHAREDIMP_R_COMMIT": PINS["SHAREDIMP_R_COMMIT"],
    "SHAREDIMP_PY_COMMIT": PINS["SHAREDIMP_PY_COMMIT"],
    "SHAREDIMP_R_IMAGE": PINS["SHAREDIMP_R_IMAGE"],
    "SHAREDIMP_PY_IMAGE": PINS["SHAREDIMP_PY_IMAGE"],
    "SHAREDIMP_R_IMAGE_DIGEST": PINS["SHAREDIMP_R_IMAGE_DIGEST"],
    "SHAREDIMP_PY_IMAGE_DIGEST": PINS["SHAREDIMP_PY_IMAGE_DIGEST"],
    # keep the run independent of the user's own R / Python configuration
    "PYTHONPATH": "$PWD/python",
    "PYTHONNOUSERSITE": 1,
    "PYTHONDONTWRITEBYTECODE": 1,
    "R_PROFILE_USER": "/dev/null",
    "R_ENVIRON_USER": "/dev/null",
    "R_LIBS_USER": "/nonexistent",
    "LC_ALL": "C.UTF-8",
    "TZ": "UTC",
}
shell.prefix("set -euo pipefail; export " + " ".join(f'{k}="{v}"' for k, v in ENV.items()) + "; ")
