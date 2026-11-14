"""Null-design forest study, Python side (one design and one variant per call).

    python -m sharedimp_exp.null_forest config/04c_null_forest.json results/raw/04c_null_forest/python null_p5 baseline

Writes <out>/<design>__<variant>.csv (one row per data set, fold and anchor:
MSE of the Full, the Reduced and the null model on the assessment rows) and
<out>/<design>__<variant>.meta.json. Representations come from sharedimp's
AnchorResidualizer, fitted on the training rows of the split.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import sharedimp
import sklearn
from sharedimp import AnchorResidualizer
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression

from .common import DATA, provenance, read_json, sha256, write_csv, write_json


def settings(cfg: dict, variant: str, lang: str) -> dict:
    s = {k: v for k, v in cfg["baseline"].items() if k not in ("r", "python", "note")}
    s["node"] = dict(cfg["baseline"][lang])
    for k, v in cfg["variants"][variant]["change"].items():
        if k in ("r", "python"):
            if k == lang:
                s["node"] = dict(v)
        else:
            s[k] = v
    return s


def mtry(rule: str, q: int, p: int) -> int:
    return {"sqrt": max(1, int(np.sqrt(q))), "as_full": max(1, int(np.sqrt(p))), "all": q, "one": 1}[rule]


def main(argv: list[str]) -> int:
    cfg, out, design, variant = read_json(Path(argv[1])), Path(argv[2]), argv[3], argv[4]
    out.mkdir(parents=True, exist_ok=True)
    entry = read_json(DATA / "null_forest" / "manifest.json")["designs"][design]
    path = DATA / "null_forest" / entry["file"]
    if sha256(path) != entry["sha256"]:
        raise RuntimeError(f"{path}: sha256 differs from the manifest")
    data = pd.read_csv(path)
    s = settings(cfg, variant, "python")
    feats, p = entry["features"], entry["p"]
    rows = []
    t0 = time.perf_counter()
    for d, df in data.groupby("dataset", sort=True):
        X, y, z, fold = df[feats].to_numpy(float), df["y"].to_numpy(float), df["z"].to_numpy(float), df["fold"].to_numpy(int)
        for f in sorted(np.unique(fold)):
            tr, te = fold != f, fold == f
            null_mse = float(np.mean((y[te] - y[tr].mean()) ** 2))
            for a in range(p):
                full = AnchorResidualizer(anchor=a).fit(X[tr])
                red = AnchorResidualizer(anchor=a, drop_anchor=True).fit(X[tr])
                reps = {0: (np.asarray(full.transform(X[tr])), np.asarray(full.transform(X[te]))),
                        1: (np.asarray(red.transform(X[tr])), np.asarray(red.transform(X[te])))}
                if s["representation"] == "padded_reduced":
                    reps[1] = (np.column_stack([reps[1][0], z[tr]]), np.column_stack([reps[1][1], z[te]]))
                elif s["representation"] == "placebo_full":
                    reps[0] = (np.column_stack([reps[1][0], z[tr]]), np.column_stack([reps[1][1], z[te]]))
                mse, cand = {}, {}
                for m, (A, B) in reps.items():
                    q = A.shape[1]
                    if s["learner"] == "ols":
                        est, cand[m] = LinearRegression(), q
                    else:
                        cand[m] = mtry(s["mtry"], q, p)
                        est = RandomForestRegressor(n_estimators=s["trees"], max_features=cand[m], max_depth=s["max_depth"], bootstrap=s["bootstrap"],
                                                    n_jobs=1, random_state=100000 * int(d) + 1000 * int(f) + 10 * (a + 1) + m, **s["node"])
                    mse[m] = float(np.mean((y[te] - est.fit(A, y[tr]).predict(B)) ** 2))
                rows.append({"design": design, "variant": variant, "dataset": int(d), "fold": int(f), "anchor": feats[a], "columns_full": reps[0][0].shape[1],
                             "columns_reduced": reps[1][0].shape[1], "candidates_full": cand[0], "candidates_reduced": cand[1],
                             "mse_full": mse[0], "mse_reduced": mse[1], "mse_null_model": null_mse})
    write_csv(pd.DataFrame(rows), out / f"{design}__{variant}.csv")
    write_json({"language": "python", "status": "ok", "design": design, "variant": variant, "settings": s, "data_sha256": entry["sha256"],
                "seconds": time.perf_counter() - t0, "scikit_learn_version": sklearn.__version__, "sharedimp_version": sharedimp.__version__,
                "threads": int(os.environ.get("SHAREDIMP_EXP_THREADS", "1")), **provenance("PY")}, out / f"{design}__{variant}.meta.json")
    print(f"[python] {design} {variant}: {len(rows)} rows, {time.perf_counter() - t0:.0f} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
