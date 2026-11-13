"""Record the Python side of the environment as JSON.

python -m sharedimp_exp.env_info results/raw/environment/python.json
"""

from __future__ import annotations

import importlib.metadata as md
import os
import platform
import sys
from pathlib import Path

from threadpoolctl import threadpool_info

from .common import read_json, write_json

PACKAGES = ["sharedimp", "scikit-learn", "numpy", "scipy", "pandas", "joblib", "threadpoolctl", "matplotlib"]
ENVS = ["OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "SHAREDIMP_EXP_THREADS"]


def version(name: str) -> str | None:
    try:
        return md.version(name)
    except md.PackageNotFoundError:
        return None


def main(out: str) -> None:
    import numpy  # noqa: F401  (loads the BLAS so that threadpoolctl can see it)
    import scipy.linalg  # noqa: F401
    import sharedimp

    mpath = os.environ.get("SHAREDIMP_INSTALL_MANIFEST", "")
    manifest = read_json(Path(mpath)) if mpath and Path(mpath).exists() else {}
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
            "commit": manifest.get("sharedimp_py", {}).get("commit"),
            "install": manifest.get("sharedimp_py"),
            "location": str(Path(sharedimp.__file__).parent),
            "editable": bool(direct_url and '"editable": true' in direct_url),
        },
        "packages": {p: version(p) for p in PACKAGES},
        "threadpools": threadpool_info(),
        "logical_cpus": os.cpu_count(),
        "thread_env": {k: os.environ.get(k) for k in ENVS},
    }
    write_json(info, Path(out))
    commit = (info["sharedimp"]["commit"] or "unknown")[:7]
    print(f"[python] Python {platform.python_version()} | sharedimp {sharedimp.__version__} ({commit})")


if __name__ == "__main__":
    main(sys.argv[1])
