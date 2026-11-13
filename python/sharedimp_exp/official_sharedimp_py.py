"""sharedimp-py side of experiment B.

    python -m sharedimp_exp.official_sharedimp_py representations CONFIG OUT.csv
    python -m sharedimp_exp.official_sharedimp_py importance      CONFIG DESIGNS_DIR DESIGN OUT.csv
    python -m sharedimp_exp.official_sharedimp_py structural      CONFIG OUT.json
    python -m sharedimp_exp.official_sharedimp_py api             CONFIG OUT.json

representations  Full and Reduced representation of every anchor, fitted on
                 all rows and applied to the same rows (the condition under
                 which the official preprocessing is defined) (B1, B2).
importance       shared_importance() on the data sets of one design (B4, B6).
structural       B5a: the training matrix the learner receives for a split
                 must not change when only the assessment rows are perturbed.
api              signature of shared_importance() and the metric names (B7).
"""

from __future__ import annotations

import inspect
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import sharedimp
from sharedimp import COMMON_METRICS, AnchorResidualizer, common_scorer, shared_importance
from sklearn.linear_model import LinearRegression

from .common import load_dataset, provenance, read_json, splits_from_labels, write_csv, write_json
from .learners import make_learner


def representations(cfg, out):
    rows = []
    for ds_id in cfg["representation_datasets"]:
        X = load_dataset(ds_id)["X"]
        for anchor in X.columns:
            for name, drop in (("full", False), ("reduced", True)):
                Z = AnchorResidualizer(anchor=anchor, drop_anchor=drop).fit(X).transform(X)
                Z = pd.DataFrame(Z) if not isinstance(Z, pd.DataFrame) else Z
                if drop:
                    Z.columns = [c for c in X.columns if c != anchor]
                else:
                    Z.columns = list(X.columns)
                for pos, col in enumerate(Z.columns, start=1):
                    rows.append(pd.DataFrame({"dataset": ds_id, "implementation": "sharedimp_py", "representation": name,
                                              "anchor": anchor, "feature": col, "position": pos,
                                              "row": np.arange(1, len(X) + 1), "value": Z[col].to_numpy()}))
    write_csv(pd.concat(rows, ignore_index=True), Path(out))


def importance(cfg, designs_dir, design, out):
    manifest = read_json(Path(designs_dir) / "manifest.json")["datasets"]
    threads = int(os.environ.get("SHAREDIMP_EXP_THREADS", "1"))
    rows = []
    for ds_id, entry in manifest.items():
        if entry["design"] != design:
            continue
        ds = load_dataset(ds_id, Path(designs_dir))
        _, splits = splits_from_labels(ds["fold"])
        for job in cfg["sharedimp_jobs"]:
            est, _ = make_learner(job["learner"], "regression", None, threads)
            res = shared_importance(est, ds["X"], ds["y"], scoring=common_scorer(job["metric"]), cv=splits,
                                    on_error="error", random_state=entry["seed"])
            imp = res.importances.copy()
            imp.insert(0, "metric", job["metric"])
            imp.insert(0, "learner", job["learner"])
            imp.insert(0, "seed", entry["seed"])
            imp.insert(0, "design", design)
            imp.insert(0, "dataset", ds_id)
            rows.append(imp)
        print(f"[sharedimp_py] {ds_id}", flush=True)
    res = pd.concat(rows, ignore_index=True)
    res.insert(0, "implementation", "sharedimp_py")
    write_csv(res, Path(out))


class RecordingOLS(LinearRegression):
    """OLS that keeps a copy of every training matrix it is fitted on."""

    seen: list = []

    def fit(self, X, y, sample_weight=None):
        type(self).seen.append(np.asarray(X, dtype=float).copy())
        return super().fit(X, y)


def structural(cfg, out):
    st = cfg["structural"]
    ds = load_dataset(st["dataset"])
    X, y = ds["X"], ds["y"]
    n, k = len(X), st["assessment_rows"]
    assess = np.arange(n) < k
    idx = np.arange(n)
    splits = [(idx[~assess], idx[assess]), (idx[assess], idx[~assess])]
    Xp = X.copy()
    Xp.loc[assess, :] = 100.0 * X.loc[assess, :] + 7.0

    def recorded(data):
        RecordingOLS.seen = []
        shared_importance(RecordingOLS(), data, y, scoring=common_scorer("mse"), cv=splits, on_error="error", random_state=1)
        return [m for m in RecordingOLS.seen if m.shape[0] == n - k]  # fits of the split whose assessment rows were perturbed

    a, b = recorded(X), recorded(Xp)
    same_layout = len(a) == len(b) and all(u.shape == v.shape for u, v in zip(a, b))
    diffs = [float(np.max(np.abs(u - v))) for u, v in zip(a, b)] if same_layout else []
    write_json(
        {
            "language": "python",
            "implementation": "sharedimp_py",
            "dataset": st["dataset"],
            "perturbation": st["perturbation"],
            "n_train": int(n - k),
            "n_assessment": int(k),
            "learner_fits_compared": len(a),
            "same_layout": bool(same_layout),
            "max_abs_diff_training_representation": max(diffs) if diffs else None,
            "bit_identical": bool(same_layout and all(np.array_equal(u, v) for u, v in zip(a, b))),
        },
        Path(out),
    )


def api(cfg, out):
    write_json(
        {
            "implementation": "sharedimp_py",
            "signatures": {"shared_importance": str(inspect.signature(shared_importance)),
                           "AnchorResidualizer": str(inspect.signature(AnchorResidualizer))},
            "common_metrics": sorted(COMMON_METRICS),
            "versions": {"sharedimp": sharedimp.__version__},
            **provenance("PY"),
        },
        Path(out),
    )


def main(argv: list[str]) -> int:
    mode, cfg = argv[1], read_json(Path(argv[2]))
    {"representations": representations, "importance": importance, "structural": structural, "api": api}[mode](cfg, *argv[3:])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
