"""Random-forest settings study, Python side (scikit-learn). See config/02b_rf_settings.json.

    python -m sharedimp_exp.rf_settings config/02b_rf_settings.json results/raw/02b_rf_settings/python

Writes single_tree.csv, single_tree_predictions.csv, bootstrap_counting.csv, forest.csv,
forest_importance.csv and meta.json (same columns as R/rf_settings.R).
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
from sharedimp import common_scorer, shared_importance
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor

from .common import load_dataset, provenance, read_json, splits_from_labels, write_csv, write_json


def predict_value(est, X, task):
    return est.predict(X) if task == "regression" else est.predict_proba(X)[:, list(est.classes_).index("b")]


def main(argv: list[str]) -> int:
    cfg, out = read_json(Path(argv[1])), Path(argv[2])
    threads = int(os.environ.get("SHAREDIMP_EXP_THREADS", "1"))
    tree_rows, pred_rows, count_rows, forest_rows, imp_rows = [], [], [], [], []
    for ds_id in cfg["datasets"]:
        ds = load_dataset(ds_id)
        task = ds["entry"]["task"]
        cls = RandomForestRegressor if task == "regression" else RandomForestClassifier
        test = ds["fold"] == cfg["test_fold"]
        Xtr, ytr, Xte, yte = ds["X"][~test], ds["y"][~test], ds["X"][test], ds["y"][test]
        rows = np.arange(1, len(test) + 1)

        # Part 1: one deterministic tree (all rows once, every feature a candidate)
        for name, setting in cfg["single_tree"]["python"].items():
            est = cls(n_estimators=1, bootstrap=False, max_features=None, random_state=1, **setting).fit(Xtr, ytr)
            tree = est.estimators_[0].tree_
            tree_rows.append({"dataset": ds_id, "setting": name, "leaves": tree.n_leaves, "depth": tree.max_depth})
            pred_rows.append(
                pd.DataFrame(
                    {
                        "dataset": ds_id,
                        "setting": name,
                        "part": ["train"] * int((~test).sum()) + ["test"] * int(test.sum()),
                        "row": np.concatenate([rows[~test], rows[test]]),
                        "prediction": np.concatenate([predict_value(est, Xtr, task), predict_value(est, Xte, task)]),
                    }
                )
            )

        # Part 2: how is the terminal-node minimum counted under bootstrap sampling?
        bc = cfg["bootstrap_counting"]
        est = cls(n_estimators=bc["trees"], max_features="sqrt", bootstrap=True, random_state=bc["seed"], n_jobs=threads, **bc["python"]).fit(Xtr, ytr)
        leaf = [t.tree_.children_left == -1 for t in est.estimators_]
        count_rows.append(
            {
                "dataset": ds_id,
                "trees": bc["trees"],
                # weighted_n_node_samples sums the bootstrap multiplicities, n_node_samples counts rows
                "smallest_leaf_in_draws": min(float(t.tree_.weighted_n_node_samples[m].min()) for t, m in zip(est.estimators_, leaf)),
                "smallest_leaf_in_distinct_rows": min(int(t.tree_.n_node_samples[m].min()) for t, m in zip(est.estimators_, leaf)),
            }
        )

        # Part 3: forests as used
        metric = cfg["forest"]["metric"][task]
        _, splits = splits_from_labels(ds["fold"])
        for name, setting in cfg["forest"]["python"].items():
            kw = {k: v for k, v in setting.items() if k != "note"}
            for seed in cfg["forest"]["seeds"]:
                make = lambda: cls(n_estimators=cfg["forest"]["trees"], max_features="sqrt", bootstrap=True, n_jobs=threads, **kw)
                est = make().set_params(random_state=seed).fit(Xtr, ytr)
                leaves = np.array([t.tree_.n_leaves for t in est.estimators_])
                depth = np.array([t.tree_.max_depth for t in est.estimators_])
                p = predict_value(est, Xte, task)
                if task == "regression":
                    score = float(np.mean((yte - p) ** 2))
                else:
                    q = np.clip(p, 1e-15, 1 - 1e-15)
                    score = float(-np.mean(np.where(yte == "b", np.log(q), np.log(1 - q))))
                t0 = time.perf_counter()
                res = shared_importance(make(), ds["X"], ds["y"], scoring=common_scorer(metric), cv=splits, on_error="error", random_state=seed)
                forest_rows.append(
                    {
                        "dataset": ds_id,
                        "setting": name,
                        "seed": seed,
                        "mtry": est.estimators_[0].max_features_,
                        "mean_leaves": leaves.mean(),
                        "mean_depth": depth.mean(),
                        "max_depth": depth.max(),
                        "test_metric": metric,
                        "test_score": score,
                        "importance_seconds": time.perf_counter() - t0,
                    }
                )
                imp = res.importances.copy()
                imp.insert(0, "seed", seed)
                imp.insert(0, "setting", name)
                imp.insert(0, "dataset", ds_id)
                imp_rows.append(imp)
                print(f"[python] {ds_id} {name} seed {seed}", flush=True)
    write_csv(pd.DataFrame(tree_rows), out / "single_tree.csv")
    write_csv(pd.concat(pred_rows, ignore_index=True), out / "single_tree_predictions.csv")
    write_csv(pd.DataFrame(count_rows), out / "bootstrap_counting.csv")
    write_csv(pd.DataFrame(forest_rows), out / "forest.csv")
    write_csv(pd.concat(imp_rows, ignore_index=True), out / "forest_importance.csv")
    write_json(
        {
            "language": "python",
            "status": "ok",
            "config": argv[1],
            "scikit_learn_version": sklearn.__version__,
            "sharedimp_version": sharedimp.__version__,
            "threads": threads,
            **provenance("PY"),
        },
        out / "meta.json",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
