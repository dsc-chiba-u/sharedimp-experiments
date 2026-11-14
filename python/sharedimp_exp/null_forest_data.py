"""Data of the null-design forest study (workflow 04c).

    python -m sharedimp_exp.null_forest_data config/04c_null_forest.json

Writes data/null_forest/<design>.csv (columns dataset, fold, y, z, x1..xp;
6 decimals) and data/null_forest/manifest.json (sha256, generator).
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from .common import DATA, read_json, sha256, write_json
from .make_synthetic import balanced_folds

OUT = DATA / "null_forest"


def main(argv: list[str]) -> int:
    cfg = read_json(Path(argv[1]))
    OUT.mkdir(parents=True, exist_ok=True)
    designs = {}
    for name, d in cfg["designs"].items():
        rng = np.random.default_rng(d["seed"])
        n, p, rho = d["n"], d["p"], cfg["feature_correlation"]
        chol = np.linalg.cholesky(np.full((p, p), rho) + (1 - rho) * np.eye(p))
        parts = []
        for k in range(1, cfg["datasets_per_design"] + 1):
            X = rng.normal(size=(n, p)) @ chol.T
            df = pd.DataFrame({"dataset": k, "fold": balanced_folds(rng, n, cfg["folds"]), "y": rng.normal(size=n), "z": rng.normal(size=n)})
            parts.append(pd.concat([df, pd.DataFrame(X, columns=[f"x{j}" for j in range(1, p + 1)])], axis=1))
        out = pd.concat(parts, ignore_index=True)
        path = OUT / f"{name}.csv"
        out.to_csv(path, index=False, float_format="%.6f", lineterminator="\n")
        designs[name] = {"file": path.name, "sha256": sha256(path), "n": n, "p": p, "datasets": cfg["datasets_per_design"], "folds": cfg["folds"],
                         "features": [f"x{j}" for j in range(1, p + 1)], "generator": {"script": "python/sharedimp_exp/null_forest_data.py", "seed": d["seed"], "model": cfg["model"],
                                                                                      "feature_correlation": rho}}
        print(f"[null_forest_data] {name}: {len(out)} rows sha256={designs[name]['sha256'][:12]}")
    write_json({"description": "Simulated data of workflow 04c (response independent of the features).", "designs": designs}, OUT / "manifest.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
