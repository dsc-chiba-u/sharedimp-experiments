"""Summarise the random-forest settings study (workflow 02b).

    python -m sharedimp_exp.rf_settings_summary config/02b_rf_settings.json results/raw/02b_rf_settings results/summary/02b_rf_settings

Writes single_tree_pairs.csv, bootstrap_counting.csv, forest_settings.csv,
forest_importance.csv, forest_importance_contrasts.csv and
results/tables/02b_rf_settings.md. Nothing is asserted about forests; the only
pass/fail statement is whether a pair of single-tree settings meets the
equivalence criterion written in the config file.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from .common import ROOT, read_json, write_csv

TOL = 1e-8


def md_table(df: pd.DataFrame, fmt: dict | None = None) -> str:
    fmt = fmt or {}
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, row in df.iterrows():
        cells = []
        for c in cols:
            v = row[c]
            if isinstance(v, (float, np.floating)):
                cells.append(format(v, fmt.get(c, ".4g")))
            else:
                cells.append(str(v))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    cfg, raw, out = read_json(Path(argv[1])), Path(argv[2]), Path(argv[3])
    rd = lambda lang, name: pd.read_csv(raw / lang / name)
    meta = {lang: read_json(raw / lang / "meta.json") for lang in ("r", "python")}

    # ---- Part 1: single deterministic trees
    shape = {lang: rd(lang, "single_tree.csv").set_index(["dataset", "setting"]) for lang in ("r", "python")}
    pred = {lang: rd(lang, "single_tree_predictions.csv") for lang in ("r", "python")}
    rows = []
    for ds in cfg["datasets"]:
        for pair in cfg["single_tree"]["pairs"]:
            a = pred["r"].query("dataset == @ds and setting == @pair['r']").set_index(["part", "row"])["prediction"]
            b = pred["python"].query("dataset == @ds and setting == @pair['python']").set_index(["part", "row"])["prediction"]
            assert a.index.equals(b.index), "row layout differs between languages"
            diff = (a - b).abs()
            sr, sp = shape["r"].loc[(ds, pair["r"])], shape["python"].loc[(ds, pair["python"])]
            dtrain, dtest = float(diff.loc["train"].max()), float(diff.loc["test"].max())
            rows.append(
                {
                    "dataset": ds,
                    "question": pair["question"],
                    "ranger": pair["r"],
                    "sklearn": pair["python"],
                    "leaves_ranger": int(sr["leaves"]),
                    "leaves_sklearn": int(sp["leaves"]),
                    "depth_ranger": int(sr["depth"]),
                    "depth_sklearn": int(sp["depth"]),
                    "max_abs_diff_train": dtrain,
                    "max_abs_diff_test": dtest,
                    "share_identical_test": float((diff.loc["test"] <= TOL).mean()),
                    "equivalent": bool(sr["leaves"] == sp["leaves"] and sr["depth"] == sp["depth"] and max(dtrain, dtest) <= TOL),
                }
            )
    pairs = pd.DataFrame(rows)
    write_csv(pairs, out / "single_tree_pairs.csv")

    # ---- Part 2: counting under bootstrap sampling
    counting = pd.concat([rd(lang, "bootstrap_counting.csv").assign(implementation=name)
                          for lang, name in (("r", "ranger, min.bucket = 5"), ("python", "scikit-learn, min_samples_leaf = 5"))], ignore_index=True)
    counting = counting[["dataset", "implementation", "trees", "smallest_leaf_in_draws", "smallest_leaf_in_distinct_rows"]]
    write_csv(counting, out / "bootstrap_counting.csv")

    # ---- Part 3: forests as used
    forest = pd.concat([rd(lang, "forest.csv").assign(language=lang) for lang in ("r", "python")], ignore_index=True)
    settings = (
        forest.groupby(["dataset", "language", "setting"], sort=False)
        .agg(
            mtry=("mtry", "first"),
            leaves_per_tree=("mean_leaves", "mean"),
            depth_per_tree=("mean_depth", "mean"),
            test_metric=("test_metric", "first"),
            test_score_mean=("test_score", "mean"),
            test_score_sd=("test_score", "std"),
            n_seeds=("seed", "nunique"),
            seconds_per_importance_run=("importance_seconds", "median"),
        )
        .reset_index()
    )
    write_csv(settings, out / "forest_settings.csv")

    imp = pd.concat([rd(lang, "forest_importance.csv").assign(language=lang) for lang in ("r", "python")], ignore_index=True)
    imp_sum = (
        imp.groupby(["dataset", "feature", "language", "setting"], sort=False)
        .agg(importance_mean=("importance", "mean"), importance_seed_sd=("importance", "std"), n_seeds=("seed", "nunique"))
        .reset_index()
    )
    write_csv(imp_sum, out / "forest_importance.csv")

    # contrasts between settings: difference of seed means, with the seed SD as yardstick
    contrasts = [
        ("R: spec_node5 vs bucket5", ("r", "spec_node5"), ("r", "bucket5")),
        ("Python: spec_leaf5 vs split6", ("python", "spec_leaf5"), ("python", "split6")),
        ("specification 8.2 as written: R spec_node5 vs Python spec_leaf5", ("r", "spec_node5"), ("python", "spec_leaf5")),
        ("split rule aligned: R spec_node5 vs Python split6", ("r", "spec_node5"), ("python", "split6")),
        ("leaf rule aligned: R bucket5 vs Python spec_leaf5", ("r", "bucket5"), ("python", "spec_leaf5")),
    ]
    key = imp_sum.set_index(["dataset", "language", "setting", "feature"])
    crow = []
    for ds in cfg["datasets"]:
        for label, a, b in contrasts:
            da, db = key.loc[(ds, *a)], key.loc[(ds, *b)]
            d = (da["importance_mean"] - db["importance_mean"]).abs()
            crow.append(
                {
                    "dataset": ds,
                    "contrast": label,
                    "max_abs_diff_of_seed_means": float(d.max()),
                    "feature": d.idxmax(),
                    "largest_seed_sd": float(max(da["importance_seed_sd"].max(), db["importance_seed_sd"].max())),
                    "largest_importance": float(max(da["importance_mean"].max(), db["importance_mean"].max())),
                    "same_ranking": bool(list(da["importance_mean"].sort_values().index) == list(db["importance_mean"].sort_values().index)),
                }
            )
    contrast = pd.DataFrame(crow)
    write_csv(contrast, out / "forest_importance_contrasts.csv")

    wide = imp_sum.assign(col=imp_sum["language"] + ":" + imp_sum["setting"]).pivot_table(
        index=["dataset", "feature"], columns="col", values="importance_mean", sort=False
    ).reset_index()
    tables = ROOT / "results" / "tables"
    tables.mkdir(parents=True, exist_ok=True)
    text = [
        "<!-- generated by python/sharedimp_exp/rf_settings_summary.py from config/02b_rf_settings.json; do not edit -->",
        f"ranger {meta['r']['ranger_version']} (parsnip {meta['r']['parsnip_version']}), scikit-learn {meta['python']['scikit_learn_version']}; "
        f"{meta['r']['threads']} thread.",
        "",
        "## Single deterministic tree (no bootstrap, all features as candidates)",
        "",
        f"Equivalence criterion: {cfg['single_tree']['equivalence_criterion']}.",
        "",
        md_table(pairs, {"max_abs_diff_train": ".3g", "max_abs_diff_test": ".3g", "share_identical_test": ".3f"}),
        "",
        "## Terminal-node minimum under bootstrap sampling (smallest leaf over all trees, training rows in the bag)",
        "",
        md_table(counting, {"smallest_leaf_in_draws": ".0f"}),
        "",
        "## Forests as used (500 trees, bootstrap, sqrt(p) candidates), mean over seeds",
        "",
        md_table(settings, {"leaves_per_tree": ".1f", "depth_per_tree": ".2f", "seconds_per_importance_run": ".1f"}),
        "",
        "## Importance by setting (mean over seeds)",
        "",
        md_table(wide),
        "",
        "## Differences between settings",
        "",
        md_table(contrast),
        "",
    ]
    (tables / "02b_rf_settings.md").write_text("\n".join(text))
    print(f"[rf_settings_summary] pairs equivalent: {int(pairs['equivalent'].sum())} of {len(pairs)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
