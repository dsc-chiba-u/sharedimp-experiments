"""Download and prepare the public data sets of experiment C.

    python -m sharedimp_exp.real_data config/04_real_data.json

For every data set of the config file: download the source file into
data/real/downloads/ (git-ignored; reused if its sha256 matches), verify the
sha256 pinned in the config, apply the documented preprocessing and write
data/real/<id>.csv (columns: fold, y, features) and data/real/manifest.json.

Preprocessing, identical for all data sets:
  - keep the listed feature columns and the target; drop rows with a missing
    value in any of them (the number of dropped rows is recorded);
  - standardize every feature (all rows, ddof = 1) and round to 6 decimals,
    so that the CSV text is the data read by R and Python;
  - draw fold labels 1..v from a seeded permutation (stratified by class).

A classification data set on which unpenalized (multinomial) logistic
regression separates a training fold completely has no maximum-likelihood
estimate; it cannot be used with the "linear" learner and is recorded under
"rejected" instead of being written.
"""

from __future__ import annotations

import sys
import urllib.request
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from .common import DATA, read_json, sha256, write_json
from .make_synthetic import balanced_folds

OUT = DATA / "real"


def fetch(url: str, digest: str, path: Path) -> None:
    if not (path.exists() and sha256(path) == digest):
        path.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(url, headers={"User-Agent": "sharedimp-experiments"})
        path.write_bytes(urllib.request.urlopen(req, timeout=120).read())
    got = sha256(path)
    if got != digest:
        raise RuntimeError(f"{url}: sha256 {got} != pinned {digest} (the source file changed)")


def separation_check(X: np.ndarray, y: np.ndarray, fold: np.ndarray) -> dict:
    """Training accuracy of unpenalized logistic regression in every training fold."""
    acc = []
    for lab in sorted(np.unique(fold)):
        tr = fold != lab
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model = LogisticRegression(C=np.inf, tol=1e-10, max_iter=20000).fit(X[tr], y[tr])
        acc.append(float(model.score(X[tr], y[tr])))
    return {"training_accuracy_per_fold": acc, "completely_separated_in_some_fold": bool(max(acc) >= 1.0)}


def main(argv: list[str]) -> int:
    cfg = read_json(Path(argv[1]))
    OUT.mkdir(parents=True, exist_ok=True)
    datasets, rejected = {}, {}
    for ds_id, spec in cfg["datasets"].items():
        raw_path = OUT / "downloads" / f"{ds_id}.csv"
        fetch(spec["url"], spec["sha256"], raw_path)
        raw = pd.read_csv(raw_path, encoding="utf-8-sig")
        cols = list(spec["features"]) + [spec["target"]]
        df = raw[cols].dropna()
        X = df[list(spec["features"])].astype(float).rename(columns=spec["features"])
        if spec["task"] == "regression":
            y = df[spec["target"]].astype(float).round(cfg["decimals"])
            strata = None
        else:
            y = df[spec["target"]].astype(str).str.strip().str.replace(" ", "_")
            strata = y.to_numpy()
        Z = ((X - X.mean()) / X.std(ddof=1)).round(cfg["decimals"])
        fold = balanced_folds(np.random.default_rng(spec["seed"]), len(df), cfg["folds"], strata=strata)
        corr = np.corrcoef(Z.to_numpy().T)
        info = {
            "title": spec["title"],
            "task": spec["task"],
            "source": spec["source"],
            "url": spec["url"],
            "landing_page": spec["landing_page"],
            "doi": spec["doi"],
            "citation": spec["citation"],
            "license": spec["license"],
            "retrieved": cfg["retrieved"],
            "source_sha256": spec["sha256"],
            "source_rows": int(len(raw)),
            "rows_dropped_for_missing_values": int(len(raw) - len(df)),
            "duplicated_rows": int(df.duplicated().sum()),
            "preprocessing": f"columns selected and renamed; rows with missing values dropped; features standardized (all rows, ddof = 1) and rounded to {cfg['decimals']} decimals; fold labels from numpy default_rng({spec['seed']})"
            + ("" if strata is None else ", stratified by class"),
            "largest_abs_feature_correlation": float(np.abs(corr - np.eye(corr.shape[0])).max()),
        }
        if strata is not None:
            info["classes"] = {str(k): int(v) for k, v in y.value_counts().sort_index().items()}
            info["separation_check"] = separation_check(Z.to_numpy(), y.to_numpy(), fold)
            if info["separation_check"]["completely_separated_in_some_fold"]:
                rejected[ds_id] = {**info, "reason": "complete separation: the unpenalized logistic maximum-likelihood estimate does not exist"}
                (OUT / f"{ds_id}.csv").unlink(missing_ok=True)
                print(f"[real_data] {ds_id}: REJECTED (complete separation)")
                continue
        out = pd.concat([pd.DataFrame({"fold": fold, "y": y.to_numpy()}), Z.reset_index(drop=True)], axis=1)
        path = OUT / f"{ds_id}.csv"
        out.to_csv(path, index=False, float_format=f"%.{cfg['decimals']}f", lineterminator="\n")
        datasets[ds_id] = {
            "file": path.name,
            "task": spec["task"],
            "target": "y",
            "fold": "fold",
            "features": list(Z.columns),
            "n": int(len(out)),
            "p": int(Z.shape[1]),
            "n_folds": cfg["folds"],
            "sha256": sha256(path),
            "original_target": spec["target"],
            "original_features": spec["features"],
            **info,
        }
        print(f"[real_data] {ds_id}: n={len(out)} p={Z.shape[1]} sha256={datasets[ds_id]['sha256'][:12]}")
    write_json(
        {
            "description": "Public data sets of experiment C, prepared by python/sharedimp_exp/real_data.py from config/04_real_data.json.",
            "standardization": cfg["standardize"],
            "separation_rule": cfg["separation_rule"],
            "datasets": datasets,
            "rejected": rejected,
        },
        OUT / "manifest.json",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
