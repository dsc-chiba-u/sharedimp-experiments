"""Generate the data sets of experiments B4 and B6.

    python -m sharedimp_exp.official_designs config/03_official_umfi.json results/raw/03_official_umfi/sources.json results/raw/03_official_umfi/designs

Runs in the official-UMFI Python image. The four synthetic designs are
produced by the official generators (`umfi/experiments.py` of
guanton/umfi_python, imported unmodified from external/) after
`numpy.random.seed(seed)`; the null design (response independent of the
features) is generated here. Values are rounded to 6 decimals, so the CSV
text is the data read by every implementation. A `fold` column holds the
fold labels used by sharedimp (the official code does not use folds).
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from .common import ROOT, read_json, sha256, write_json

DECIMALS = 6


def null_design(seed: int, n: int) -> pd.DataFrame:
    rng = np.random.default_rng(900000 + seed)
    x1 = rng.normal(size=n)
    x2 = 0.8 * x1 + 0.6 * rng.normal(size=n)
    x3 = rng.normal(size=n)
    x4 = rng.normal(size=n)
    x5 = x3 + 0.1 * rng.normal(size=n)
    return pd.DataFrame({"x1": x1, "x2": x2, "x3": x3, "x4": x4, "x5": x5, "y": rng.normal(size=n)})


def main(argv: list[str]) -> int:
    cfg, sources, out = read_json(Path(argv[1])), read_json(Path(argv[2])), Path(argv[3])
    out.mkdir(parents=True, exist_ok=True)
    d = cfg["designs"]
    sys.path.insert(0, str(ROOT / sources["sources"]["official_py"]["directory"]))
    import umfi.experiments as official  # noqa: E402  (official code, imported unmodified)

    entries = {}
    for design in d["official_generators"] + [d["null"]["name"]]:
        for seed in d["seeds"]:
            if design == d["null"]["name"]:
                df, origin = null_design(seed, d["n"]), "python/sharedimp_exp/official_designs.py:null_design"
            else:
                np.random.seed(seed)
                df = getattr(official, f"generate_{design}_data")(d["n"])
                origin = f"umfi/experiments.py:generate_{design}_data (guanton/umfi_python @ {sources['sources']['official_py']['commit'][:7]}) after numpy.random.seed({seed})"
            features = [c for c in df.columns if c != "y"]
            fold = np.random.default_rng(700000 + seed).permutation(np.arange(len(df)) % d["folds"] + 1)
            df = pd.concat([pd.DataFrame({"fold": fold, "y": df["y"]}), df[features]], axis=1)
            name = f"{design}_seed{seed:02d}"
            df.round(DECIMALS).to_csv(out / f"{name}.csv", index=False, float_format=f"%.{DECIMALS}f", lineterminator="\n")
            entries[name] = {
                "file": f"{name}.csv",
                "design": design,
                "seed": seed,
                "n": len(df),
                "features": features,
                "target": "y",
                "fold": "fold",
                "task": "regression",
                "origin": origin,
                "sha256": sha256(out / f"{name}.csv"),
            }
    write_json({"description": "Data sets of experiments B4 and B6; see python/sharedimp_exp/official_designs.py.", "datasets": entries}, out / "manifest.json")
    print(f"[designs] {len(entries)} data sets -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
