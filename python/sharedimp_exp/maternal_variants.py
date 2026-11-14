"""Duplicated rows of the Maternal Health Risk data: counts and two derived files.

    python -m sharedimp_exp.maternal_variants config/04b_maternal.json results/raw/04b_maternal

Reads data/real/maternal.csv (experiment C; never modified) and writes

    data/derived/maternal_grouped.csv   all rows, folds that keep identical feature vectors together
    data/derived/maternal_dedup.csv     one row per identical record, same kind of folds
    data/derived/manifest.json          same format as data/real/manifest.json, plus the derivation
    <out>/duplicates.json               counts (definitions in the config file)
    <out>/multiplicity.csv              how often identical records occur
    <out>/first_occurrence.csv          new records per block of 100 rows of the source file
    <out>/conflicting_groups.csv        feature vectors that carry more than one label

The feature values are those of the source file (standardized with all 1014
rows, 6 decimals); they are not standardized again, so that the three files
differ in rows and folds only. If the downloaded original is present its row
order is checked against the prepared file.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
from sklearn.model_selection import StratifiedGroupKFold

from .common import DATA, ROOT, find_dataset, read_json, sha256, write_csv, write_json
from .real_data import separation_check

OUT = DATA / "derived"


def group_folds(y: np.ndarray, groups: np.ndarray, v: int, seed: int) -> np.ndarray:
    fold = np.zeros(len(y), dtype=int)
    cv = StratifiedGroupKFold(n_splits=v, shuffle=True, random_state=seed)
    for k, (_, test) in enumerate(cv.split(np.zeros(len(y)), y, groups), start=1):
        fold[test] = k
    assert fold.min() >= 1
    return fold


def main(argv: list[str]) -> int:
    cfg, out = read_json(Path(argv[1])), Path(argv[2])
    out.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    entry, path = find_dataset(cfg["source_dataset"])
    if sha256(path) != entry["sha256"]:
        raise RuntimeError(f"{path}: sha256 differs from the manifest")
    src = pd.read_csv(path, dtype={c: str for c in entry["features"]})  # text: the 6-decimal strings are the data
    feats = entry["features"]
    n = len(src)

    record = src.groupby(feats + ["y"], sort=False).ngroup().to_numpy()
    group = src.groupby(feats, sort=False).ngroup().to_numpy()
    first_record = ~pd.Series(record).duplicated().to_numpy()
    labels_per_group = src.groupby(group)["y"].nunique()
    size_per_group = pd.Series(group).value_counts().sort_index()
    conflicting = labels_per_group[labels_per_group > 1].index
    dup = {
        "source_file": str(path.relative_to(ROOT)),
        "source_sha256": entry["sha256"],
        "rows": n,
        "identical_record": {
            "definition": cfg["definitions"]["identical record"],
            "distinct_records": int(first_record.sum()),
            "rows_that_repeat_an_earlier_record": int(n - first_record.sum()),
            "rows_whose_record_occurs_more_than_once": int((pd.Series(record).map(pd.Series(record).value_counts()) > 1).sum()),
            "largest_multiplicity": int(pd.Series(record).value_counts().max()),
        },
        "identical_features": {
            "definition": cfg["definitions"]["identical features"],
            "distinct_feature_vectors": int(group.max() + 1),
            "rows_that_repeat_an_earlier_feature_vector": int(n - (group.max() + 1)),
        },
        "conflicting_groups": {
            "definition": cfg["definitions"]["conflicting group"],
            "groups": int(len(conflicting)),
            "rows_in_them": int(size_per_group[conflicting].sum()),
            "groups_with_three_labels": int((labels_per_group == 3).sum()),
        },
        "classes_all_rows": {k: int(v) for k, v in src["y"].value_counts().sort_index().items()},
        "classes_distinct_records": {k: int(v) for k, v in src.loc[first_record, "y"].value_counts().sort_index().items()},
        "random_folds_of_experiment_C": {
            "assessment_rows_whose_feature_vector_is_also_in_the_training_rows": int(
                sum(np.isin(group[src["fold"] == f], group[src["fold"] != f]).sum() for f in sorted(src["fold"].unique()))
            ),
            "assessment_rows_whose_record_is_also_in_the_training_rows": int(
                sum(np.isin(record[src["fold"] == f], record[src["fold"] != f]).sum() for f in sorted(src["fold"].unique()))
            ),
        },
    }
    download = ROOT / cfg["source_download"]
    if download.exists():
        raw = pd.read_csv(download, encoding="utf-8-sig")
        raw_cols = list(entry["original_features"]) + [entry["original_target"]]
        same = raw.groupby(raw_cols, sort=False).ngroup().to_numpy()
        dup["download_check"] = {
            "file": cfg["source_download"],
            "sha256": sha256(download),
            "rows": int(len(raw)),
            "identical_record_pattern_equals_prepared_file": bool(len(raw) == n and (same == record).all()),
        }
    else:
        dup["download_check"] = {"file": cfg["source_download"], "status": "not present; row pattern of the prepared file not compared with the original"}
    write_json(dup, out / "duplicates.json")

    mult = pd.Series(record).value_counts().value_counts().sort_index()
    write_csv(pd.DataFrame({"copies_of_a_record": mult.index, "distinct_records": mult.to_numpy(), "rows": mult.index * mult.to_numpy()}), out / "multiplicity.csv")
    blocks = [(i + 1, min(i + 100, n), int(first_record[i : i + 100].sum()), int(min(i + 100, n) - i)) for i in range(0, n, 100)]
    write_csv(pd.DataFrame(blocks, columns=["first_row", "last_row", "records_not_seen_before", "rows"]), out / "first_occurrence.csv")
    conf = src.assign(group=group)
    conf = conf[conf["group"].isin(conflicting)].groupby(["group"] + feats, sort=False)["y"].value_counts().unstack(fill_value=0).reset_index()
    write_csv(conf, out / "conflicting_groups.csv")

    datasets = {}
    for vid, spec in cfg["variants"].items():
        keep = np.ones(n, dtype=bool) if spec["rows"] == "all" else first_record
        sub = src[keep].reset_index(drop=True)
        g = group[keep]
        fold = group_folds(sub["y"].to_numpy(), g, cfg["folds"], spec["seed"])
        sub = sub.assign(fold=fold)[["fold", "y"] + feats]
        file = OUT / f"{vid}.csv"
        sub.to_csv(file, index=False, lineterminator="\n")  # features are the source strings, unchanged
        split_groups = int((pd.Series(fold).groupby(g).nunique() > 1).sum())
        X = sub[feats].astype(float).to_numpy()
        datasets[vid] = {
            "file": file.name,
            "task": "classification",
            "target": "y",
            "fold": "fold",
            "features": feats,
            "n": int(len(sub)),
            "p": len(feats),
            "n_folds": cfg["folds"],
            "sha256": sha256(file),
            "derived_from": {"dataset": cfg["source_dataset"], "file": str(path.relative_to(ROOT)), "sha256": entry["sha256"]},
            "rows": spec["rows"],
            "folds": spec["folds"],
            "seed": spec["seed"],
            "fold_sizes": {str(k): int(v) for k, v in pd.Series(fold).value_counts().sort_index().items()},
            "classes": {k: int(v) for k, v in sub["y"].value_counts().sort_index().items()},
            "classes_per_fold": {str(f): {k: int(v) for k, v in sub.loc[sub["fold"] == f, "y"].value_counts().sort_index().items()} for f in sorted(set(fold))},
            "feature_vectors_in_more_than_one_fold": split_groups,
            "identical_records_removed": int(n - keep.sum()),
            "separation_check": separation_check(X, sub["y"].to_numpy(), fold),
            "title": f"{entry['title']} ({vid})",
            "source": entry["source"],
            "doi": entry["doi"],
            "citation": entry["citation"],
            "license": entry["license"],
        }
        print(f"[maternal_variants] {vid}: n={len(sub)} groups split={split_groups} sha256={datasets[vid]['sha256'][:12]}")
    write_json(
        {
            "description": "Files derived from data sets of data/real/ by python/sharedimp_exp/maternal_variants.py (config/04b_maternal.json). Modified versions of a CC BY 4.0 data set; see data/derived/README.md.",
            "scikit_learn_version": sklearn.__version__,
            "datasets": datasets,
        },
        OUT / "manifest.json",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
