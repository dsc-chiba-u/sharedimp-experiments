"""Run the official Python UMFI code (guanton/umfi_python), unmodified.

    python -m sharedimp_exp.official_py representations CONFIG SOURCES OUT.csv
    python -m sharedimp_exp.official_py importance      CONFIG SOURCES DESIGNS_DIR DESIGN OUT.csv
    python -m sharedimp_exp.official_py replica         CONFIG SOURCES SHAREDIMP_REPRESENTATIONS.csv OUT.csv
    python -m sharedimp_exp.official_py api             CONFIG SOURCES OUT.json

Runs in the official-UMFI image (Python 3.9, versions of the official
`umfi.yml`). The official modules are imported from external/ at the pinned
commit; nothing of them is copied. sharedimp is not available in this image.

representations  `preprocess_lr(X, anchor)` for every anchor of the
                 representation data sets (experiments B1, B2).
importance       `UMFI(X, y, ...)` on the data sets of one design
                 (B4, B6), with extra trees (the official default) and with
                 random forests (`RF=True`), after `numpy.random.seed(seed)`.
replica          B3: the official scoring rule (forest, out-of-bag score,
                 floors at 0) applied to representations computed by
                 sharedimp-py, with the same seed and the same order of model
                 fits as `UMFI()`; next to the output of `UMFI()` itself.
api              signatures of the official functions (B7).
"""

from __future__ import annotations

import inspect
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn

from .common import ROOT, load_dataset, provenance, read_json, write_csv, write_json


def official(sources: dict):
    sys.path.insert(0, str(ROOT / sources["sources"]["official_py"]["directory"]))
    from umfi.preprocess_LR import preprocess_lr  # noqa: E402  (official code)
    from umfi.UMFI import UMFI  # noqa: E402

    return preprocess_lr, UMFI


def representations(cfg, sources, out):
    preprocess_lr, _ = official(sources)
    rows = []
    for ds_id in cfg["representation_datasets"]:
        ds = load_dataset(ds_id)
        X = ds["X"]
        for anchor in X.columns:
            np.random.seed(1)  # only used by the official noise branches; whether they ran is visible in the result
            newX = preprocess_lr(X.copy(), anchor)
            assert list(newX.columns) == list(X.columns)
            for col in newX.columns:
                rows.append(pd.DataFrame({"dataset": ds_id, "implementation": "official_py", "representation": "full",
                                          "anchor": anchor, "feature": col, "position": list(newX.columns).index(col) + 1,
                                          "row": np.arange(1, len(X) + 1), "value": newX[col].to_numpy()}))
    write_csv(pd.concat(rows, ignore_index=True), Path(out))


def importance(cfg, sources, designs_dir, design, out):
    _, UMFI = official(sources)
    manifest = read_json(Path(designs_dir) / "manifest.json")["datasets"]
    call = cfg["official_py_call"]
    rows = []
    for ds_id, entry in manifest.items():
        if entry["design"] != design:
            continue
        ds = load_dataset(ds_id, Path(designs_dir))
        y = pd.Series(ds["y"], name="y")
        for rf, forest in ((False, "extra_trees"), (True, "random_forest")):
            np.random.seed(entry["seed"])
            _, detail = UMFI(ds["X"].copy(), y, RF=rf, **call)
            detail = detail.rename(columns={"Feature": "feature", "Importance": "importance", "Iteration": "iteration"})
            detail = detail[["feature", "iteration", "importance"]]
            detail.insert(0, "forest", forest)
            detail.insert(0, "seed", entry["seed"])
            detail.insert(0, "design", design)
            detail.insert(0, "dataset", ds_id)
            rows.append(detail)
        print(f"[official_py] {ds_id}", flush=True)
    res = pd.concat(rows, ignore_index=True)
    res.insert(0, "implementation", "official_py")
    write_csv(res, Path(out))


def replica(cfg, sources, reps_file, out):
    """B3. The scoring rule below restates what UMFI() does after preprocessing
    (umfi/UMFI.py: models with `oob_score=True`, `max(0, oob_score_)`, the
    difference, negative values set to 0), so that it can be applied to a
    representation that was not built by the official preprocessing."""
    from sklearn.ensemble import ExtraTreesRegressor, RandomForestRegressor

    _, UMFI = official(sources)
    reps = pd.read_csv(reps_file)
    reps = reps[(reps["implementation"] == "sharedimp_py") & (reps["representation"] == "full")]
    ic = cfg["identical_condition"]
    n_trees = cfg["official_py_call"]["n_trees"]
    rows = []
    for ds_id in (ic["dataset"], ic["contrast_dataset"]):
        ds = load_dataset(ds_id)
        X, y = ds["X"], pd.Series(ds["y"], name="y")
        for rf, forest in ((False, "extra_trees"), (True, "random_forest")):
            for seed in ic["seeds"]:
                np.random.seed(seed)
                _, detail = UMFI(X.copy(), y, preprocessing_methods=["linear regression"], niter=1, n_trees=n_trees,
                                 select_optimal_preprocessing=False, RF=rf)
                off = detail.set_index("Feature")["Importance"]
                np.random.seed(seed)
                rep = np.zeros(X.shape[1])
                for i, anchor in enumerate(X.columns):
                    block = reps[(reps["dataset"] == ds_id) & (reps["anchor"] == anchor)]
                    newX = block.pivot(index="row", columns="feature", values="value")[list(X.columns)].reset_index(drop=True)
                    newX_without = newX.drop(columns=[anchor])
                    if rf:
                        with_, without = RandomForestRegressor(n_estimators=n_trees, oob_score=True), RandomForestRegressor(n_estimators=n_trees, oob_score=True)
                    else:
                        with_ = ExtraTreesRegressor(n_estimators=n_trees, oob_score=True, bootstrap=True)
                        without = ExtraTreesRegressor(n_estimators=n_trees, oob_score=True, bootstrap=True)
                    with_.fit(newX, y)
                    without.fit(newX_without, y)
                    rep[i] = max(0, with_.oob_score_) - max(0, without.oob_score_)
                rep[rep < 0] = 0
                for i, anchor in enumerate(X.columns):
                    rows.append({"language": "python", "dataset": ds_id, "forest": forest, "seed": seed, "feature": anchor,
                                 "official": float(off[anchor]), "official_rule_on_sharedimp_representation": float(rep[i])})
    write_csv(pd.DataFrame(rows), Path(out))


def api(cfg, sources, out):
    preprocess_lr, UMFI = official(sources)
    write_json(
        {
            "implementation": "official_py",
            "signatures": {"UMFI": str(inspect.signature(UMFI)), "preprocess_lr": str(inspect.signature(preprocess_lr))},
            "versions": {"python": sys.version.split()[0], "scikit-learn": sklearn.__version__, "numpy": np.__version__, "pandas": pd.__version__},
            **{k: v for k, v in provenance("PY").items() if k in ("container", "experiments_commit", "experiments_code_dirty")},
        },
        Path(out),
    )


def main(argv: list[str]) -> int:
    mode, cfg, sources = argv[1], read_json(Path(argv[2])), read_json(Path(argv[3]))
    {"representations": representations, "importance": importance, "replica": replica, "api": api}[mode](cfg, sources, *argv[4:])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
