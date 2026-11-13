"""Record the Python side of the environment as JSON.

python -m sharedimp_exp.env_info results/raw/01_environment/python.json

Exit status 1 if the process does not run inside the image pinned in
config/pins.env.
"""

from __future__ import annotations

import importlib.metadata as md
import os
import platform
import sys
from pathlib import Path

from threadpoolctl import threadpool_info

from .common import pinned_image, provenance, write_json

PACKAGES = ["sharedimp", "scikit-learn", "numpy", "scipy", "pandas", "joblib", "threadpoolctl"]
ENVS = ["OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "SHAREDIMP_EXP_THREADS"]


def version(name: str) -> str | None:
    try:
        return md.version(name)
    except md.PackageNotFoundError:
        return None


def _os_pretty_name() -> str | None:
    path = Path("/etc/os-release")
    if path.exists():
        for line in path.read_text().splitlines():
            if line.startswith("PRETTY_NAME="):
                return line.split("=", 1)[1].strip('"')
    return None


def main(out: str) -> int:
    import numpy  # noqa: F401  (loads the BLAS so that threadpoolctl can see it)
    import scipy.linalg  # noqa: F401
    import sharedimp

    prov = provenance("PY")
    direct_url = None
    try:
        direct_url = md.distribution("sharedimp").read_text("direct_url.json")
    except Exception:
        pass
    info = {
        "language": "python",
        "python_version": sys.version,
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "executable": sys.executable,
        "sharedimp": {
            "version": sharedimp.__version__,
            "commit": prov["sharedimp_commit"],
            "location": str(Path(sharedimp.__file__).parent),
            "editable": bool(direct_url and '"editable": true' in direct_url),
        },
        "container": prov["container"],
        "pinned_image": pinned_image("PY"),
        "in_pinned_image": prov["in_pinned_image"],
        "os": _os_pretty_name(),
        "packages": {p: version(p) for p in PACKAGES},
        "threadpools": threadpool_info(),
        "logical_cpus": os.cpu_count(),
        "thread_env": {k: os.environ.get(k) for k in ENVS},
    }
    write_json(info, Path(out))
    commit = (info["sharedimp"]["commit"] or "unknown")[:7]
    print(f"[python] Python {platform.python_version()} | sharedimp {sharedimp.__version__} ({commit})")
    if not prov["in_pinned_image"]:
        print(f"[python] ERROR not running inside the pinned image {pinned_image('PY')}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
