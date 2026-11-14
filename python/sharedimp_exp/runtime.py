"""Runtime benchmark, Python side: one process per learner (experiment D).

    python -m sharedimp_exp.runtime config/05_runtime.json <plan.csv> <out dir> <learner> <pilot|main>

Same outputs as R/runtime.R with the prefix python_<learner>. Timed region:
the shared_importance() call only. Timer: time.perf_counter().
"""

from __future__ import annotations

import gc
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import sharedimp
import sklearn
from sharedimp import common_scorer, shared_importance
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from threadpoolctl import threadpool_info

from .common import DATA, provenance, read_json, sha256, splits_from_labels, write_csv, write_json


class CountingOLS(LinearRegression):
    """LinearRegression that counts how often it is fitted (all clones together)."""

    fits = 0

    def fit(self, X, y, sample_weight=None):
        type(self).fits += 1
        return super().fit(X, y)


def make_learner(name: str):
    if name == "linear":
        return LinearRegression()
    if name == "rf_aligned":
        return RandomForestRegressor(n_estimators=500, min_samples_split=6, min_samples_leaf=1, max_features="sqrt", bootstrap=True, n_jobs=1)
    if name == "rf_customary":
        return RandomForestRegressor()
    raise ValueError(f"no Python learner '{name}'")


def loadavg() -> float:
    return float(Path("/proc/loadavg").read_text().split()[0])


def main(argv: list[str]) -> int:
    cfg, plan_path, out, learner, mode = read_json(Path(argv[1])), argv[2], Path(argv[3]), argv[4], argv[5]
    out.mkdir(parents=True, exist_ok=True)
    started, started_utc = time.perf_counter(), datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    plan = pd.read_csv(plan_path)
    plan = plan[(plan["language"] == "python") & (plan["learner"] == learner)].sort_values(["predicted_seconds", "n", "p", "v"])
    if plan.empty:
        raise SystemExit(f"no cells for python/{learner} in {plan_path}")
    manifest = read_json(DATA / "runtime" / "manifest.json")["files"]
    scorer = common_scorer(cfg["data"]["metric"])

    def load_cell(data: str, fold_column: str) -> dict:
        entry = manifest[data]
        path = DATA / "runtime" / entry["file"]
        digest = sha256(path)
        if digest != entry["sha256"]:
            raise RuntimeError(f"{path}: sha256 differs from the manifest")
        df = pd.read_csv(path)
        _, splits = splits_from_labels(df[fold_column].to_numpy(dtype=int))
        return {"X": df[entry["features"]].astype(float), "y": df["y"].to_numpy(dtype=float), "splits": splits, "sha256": digest}

    def timed_call(d: dict, est=None):
        est = make_learner(learner) if est is None else est
        gc.collect()
        t0 = time.perf_counter()
        res = shared_importance(est, d["X"], d["y"], scoring=scorer, cv=d["splits"], on_error="error", random_state=1)
        return time.perf_counter() - t0, res

    runs, cells, imps = [], [], []

    def add_run(row, kind, rep, seconds, load_before):
        runs.append({"language": "python", "learner": learner, "cell": row.cell, "n": row.n, "p": row.p, "v": row.v, "kind": kind, "run": rep,
                     "seconds": seconds, "loadavg_1min_before": load_before})

    def add_cell(row, status, reason="", digest=None, timed=0):
        cells.append({"language": "python", "learner": learner, "cell": row.cell, "n": row.n, "p": row.p, "v": row.v, "status": status, "reason": reason,
                      "timed_runs": timed, "predicted_seconds": row.predicted_seconds, "data": row.data, "fold_column": row.fold_column, "data_sha256": digest})
        print(f"[python/{learner}] {row.cell}: {status} {reason}", flush=True)

    n_warm, n_timed = cfg["protocol"]["warmup_runs"], 1 if mode == "pilot" else cfg["protocol"]["timed_runs"]
    for k, row in enumerate(plan.itertuples()):
        if row.status != "run":
            add_cell(row, row.status, "per-cell cap of the plan")
            continue
        if mode == "main" and time.perf_counter() - started > 1.25 * row.process_planned_seconds:
            add_cell(row, "skipped (budget, process allowance)", f"process had used more than 1.25 x {row.process_planned_seconds:.0f} s")
            continue
        try:
            d = load_cell(row.data, row.fold_column)
            seconds = None
            if mode == "main" or k == 0:
                for w in range(1, n_warm + 1):
                    load = loadavg()
                    seconds, _ = timed_call(d)
                    add_run(row, "warmup", w, seconds, load)
                if mode == "main" and (n_warm + n_timed) * seconds > cfg["budget"]["abort_factor"] * row.cap_seconds:
                    add_cell(row, "skipped (budget, after warm-up)", f"warm-up run took {seconds:.1f} s", d["sha256"])
                    continue
            for i in range(1, n_timed + 1):
                load = loadavg()
                seconds, res = timed_call(d)
                add_run(row, "timed", i, seconds, load)
            imp = res.importances.copy()
            imp.insert(0, "cell", row.cell)
            imp.insert(0, "learner", learner)
            imp.insert(0, "language", "python")
            imps.append(imp)
            add_cell(row, "measured", "", d["sha256"], n_timed)
        except Exception as exc:  # recorded per cell; the summary fails on it
            add_cell(row, "failed", f"{type(exc).__name__}: {exc}")
    fit_count = None
    if mode == "pilot" and learner == "linear":
        fc = cfg["pilot"]["fit_count_cell"]
        d = load_cell(f"rt_n{fc['n']}_p{fc['p']}", f"fold_v{fc['v']}")
        CountingOLS.fits = 0
        timed_call(d, CountingOLS())
        fit_count = {**fc, "fits": CountingOLS.fits, "expected": 2 * fc["p"] * fc["v"]}

    prefix = f"python_{learner}"
    write_csv(pd.DataFrame(runs), out / f"{prefix}.runs.csv")
    write_csv(pd.DataFrame(cells), out / f"{prefix}.cells.csv")
    write_csv(pd.concat(imps, ignore_index=True) if imps else pd.DataFrame(), out / f"{prefix}.importance.csv")
    cpu = [line.split(":", 1)[1].strip() for line in Path("/proc/cpuinfo").read_text().splitlines() if line.startswith("model name")]
    envs = ["OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "SHAREDIMP_EXP_THREADS"]
    write_json(
        {
            "language": "python", "learner": learner, "mode": mode, "status": "ok", "learner_description": cfg["learners"][learner]["python"],
            "learner_repr": repr(make_learner(learner)), "plan": plan_path, "started_utc": started_utc, "process_seconds": time.perf_counter() - started,
            "timer": "time.perf_counter()",
            "python_version": sys.version,
            "packages": {"sharedimp": sharedimp.__version__, "scikit-learn": sklearn.__version__, "numpy": np.__version__, "pandas": pd.__version__},
            "threadpools": threadpool_info(),
            "cpu": cpu[0] if cpu else None, "logical_cpus": len(cpu),
            "threads": int(os.environ.get("SHAREDIMP_EXP_THREADS", "1")), "thread_env": {k: os.environ.get(k) for k in envs},
            "loadavg_1min_end": loadavg(), "fit_count": fit_count,
            **provenance("PY"),
        },
        out / f"{prefix}.meta.json",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
