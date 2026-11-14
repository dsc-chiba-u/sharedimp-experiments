"""Maternal Health Risk: original folds vs group-aware folds vs identical records removed.

    python -m sharedimp_exp.maternal_summary config/04b_maternal.json config/04b_maternal_jobs.json results/raw/04b_maternal results/summary/04b_maternal

Reads the results of experiment C for the original file (results/raw/04_real_data,
results/summary/04_real_data) and those of workflow 04b for the two derived
files. Writes variants.csv, scores.csv, importance_by_variant.csv,
rank_agreement.csv, checks.csv (job checks of check_jobs plus the data checks
of config/04b_maternal.json) and results/tables/04b_maternal{,_checks}.md.
Exit status 1 if a check fails.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from .common import DATA, ROOT, read_json, write_csv
from .rf_settings_summary import md_table

VARIANT_LABEL = {
    "maternal": "original: all rows, random stratified folds (experiment C)",
    "maternal_grouped": "all rows, group-aware folds",
    "maternal_dedup": "identical records removed, group-aware folds",
}


def main(argv: list[str]) -> int:
    cfg, spec, raw, out = read_json(Path(argv[1])), read_json(Path(argv[2])), Path(argv[3]), Path(argv[4])
    dup = read_json(raw / "duplicates.json")
    derived = read_json(DATA / "derived" / "manifest.json")["datasets"]
    source = read_json(DATA / "real" / "manifest.json")["datasets"][cfg["source_dataset"]]
    checks = pd.read_csv(out / "checks_jobs.csv").to_dict("records")

    def check(check_id, description, criterion, observed, passed):
        checks.append({"check": check_id, "description": description, "criterion": criterion, "observed": observed,
                       "status": "reported" if passed is None else ("pass" if passed else "FAIL")})

    # ---- data checks (criteria in the config file), recomputed from the files themselves
    feats = source["features"]
    src = pd.read_csv(DATA / "real" / source["file"], dtype={c: str for c in feats})
    var_rows = [{"variant": "maternal", "description": VARIANT_LABEL["maternal"], "rows": len(src),
                 "distinct_feature_vectors": src[feats].drop_duplicates().shape[0],
                 "feature_vectors_in_more_than_one_fold": int((src.groupby(feats)["fold"].nunique() > 1).sum()),
                 "assessment_rows_with_feature_vector_in_training": dup["random_folds_of_experiment_C"]["assessment_rows_whose_feature_vector_is_also_in_the_training_rows"],
                 "classes": "; ".join(f"{k}: {v}" for k, v in source["classes"].items()), "sha256": source["sha256"][:12]}]
    for vid, e in derived.items():
        d = pd.read_csv(DATA / "derived" / e["file"], dtype={c: str for c in feats})
        split = int((d.groupby(feats)["fold"].nunique() > 1).sum())
        check(f"{vid}/group_integrity", "no feature vector occurs in more than one fold", "0 groups split", split, split == 0)
        if e["rows"] == "all":
            same = len(d) == len(src) and (d[["y"] + feats].to_numpy() == src[["y"] + feats].to_numpy()).all()
            check(f"{vid}/rows", "rows are those of the source file, in the same order", "identical", f"{len(d)} rows", bool(same))
        else:
            expect = src[["y"] + feats].drop_duplicates()
            same = len(d) == len(expect) and (d[["y"] + feats].to_numpy() == expect.to_numpy()).all() and not d[["y"] + feats].duplicated().any()
            check(f"{vid}/rows", "exactly one row per identical record of the source file", "identical to the distinct records", f"{len(d)} rows", bool(same))
        sep = e["separation_check"]
        check(f"{vid}/separation", "unpenalized multinomial logistic regression does not separate a training fold", "training accuracy < 1 in every fold",
              f"max {max(sep['training_accuracy_per_fold']):.3f}", not sep["completely_separated_in_some_fold"])
        var_rows.append({"variant": vid, "description": VARIANT_LABEL[vid], "rows": len(d),
                         "distinct_feature_vectors": d[feats].drop_duplicates().shape[0],
                         "feature_vectors_in_more_than_one_fold": split, "assessment_rows_with_feature_vector_in_training": 0 if split == 0 else None,
                         "classes": "; ".join(f"{k}: {v}" for k, v in e["classes"].items()), "sha256": e["sha256"][:12]})
    variants = pd.DataFrame(var_rows)
    write_csv(variants, out / "variants.csv")

    # ---- scores and importances: experiment C (original) next to the derived files
    ref = pd.read_csv(ROOT / "results" / "summary" / "04_real_data" / "importance_long.csv")
    imp = pd.concat([ref[ref["dataset"] == cfg["source_dataset"]], pd.read_csv(out / "importance_long.csv")], ignore_index=True)
    imp["variant"] = pd.Categorical(imp["dataset"], categories=list(VARIANT_LABEL))
    scores = (imp.groupby(["learner", "metric", "language", "variant"], observed=True, sort=False)
              .agg(full_score=("score_full", "mean"), reduced_score_mean_over_anchors=("score_reduced", "mean"),
                   largest_importance=("importance", "max"), smallest_importance=("importance", "min")).reset_index())
    write_csv(scores, out / "scores.csv")
    wide = imp.pivot_table(index=["learner", "metric", "language", "feature"], columns="variant", values="importance", observed=True, sort=False).reset_index()
    sd = imp.pivot_table(index=["learner", "metric", "language", "feature"], columns="variant", values="importance_std", observed=True, sort=False).reset_index()
    for v in VARIANT_LABEL:
        wide[f"sd_{v}"] = sd[v]
    write_csv(wide, out / "importance_by_variant.csv")
    rank_rows = []
    for (learner, metric, lang), d in wide.groupby(["learner", "metric", "language"], sort=False):
        for v in ("maternal_grouped", "maternal_dedup"):
            rank_rows.append({"learner": learner, "metric": metric, "language": lang, "variant": v,
                              "spearman_with_original": d["maternal"].corr(d[v], method="spearman"),
                              "top_feature_original": d.loc[d["maternal"].idxmax(), "feature"], "top_feature_variant": d.loc[d[v].idxmax(), "feature"],
                              "largest_abs_change_of_importance": float((d[v] - d["maternal"]).abs().max())})
    rank = pd.DataFrame(rank_rows)
    write_csv(rank, out / "rank_agreement.csv")
    for r in rank.itertuples():
        check(f"{r.variant}/{r.learner}_{r.metric}/{r.language}/rank", "Spearman correlation of the importances with those of the original analysis", "reported only",
              f"{r.spearman_with_original:.3f}", None)

    table = pd.DataFrame(checks)
    write_csv(table, out / "checks.csv")
    tables = ROOT / "results" / "tables"
    md = ["| check | description | criterion | observed | status |", "|---|---|---|---|---|"]
    md += [f"| `{r.check}` | {r.description} | {r.criterion} | {r.observed} | {r.status} |" for r in table.itertuples()]
    (tables / "04b_maternal_checks.md").write_text("<!-- generated by python/sharedimp_exp/maternal_summary.py; do not edit -->\n" + "\n".join(md) + "\n")

    ir, fv, cg = dup["identical_record"], dup["identical_features"], dup["conflicting_groups"]
    counts = pd.DataFrame([
        {"quantity": "rows", "value": dup["rows"]},
        {"quantity": "distinct records (features and label)", "value": ir["distinct_records"]},
        {"quantity": "rows that repeat an earlier record", "value": ir["rows_that_repeat_an_earlier_record"]},
        {"quantity": "rows whose record occurs more than once", "value": ir["rows_whose_record_occurs_more_than_once"]},
        {"quantity": "largest number of copies of one record", "value": ir["largest_multiplicity"]},
        {"quantity": "distinct feature vectors (label ignored)", "value": fv["distinct_feature_vectors"]},
        {"quantity": "rows that repeat an earlier feature vector", "value": fv["rows_that_repeat_an_earlier_feature_vector"]},
        {"quantity": "feature vectors with more than one label", "value": cg["groups"]},
        {"quantity": "rows with such a feature vector", "value": cg["rows_in_them"]},
        {"quantity": "assessment rows (random folds of experiment C) whose feature vector is also in the training rows",
         "value": dup["random_folds_of_experiment_C"]["assessment_rows_whose_feature_vector_is_also_in_the_training_rows"]},
        {"quantity": "assessment rows (random folds of experiment C) whose record is also in the training rows",
         "value": dup["random_folds_of_experiment_C"]["assessment_rows_whose_record_is_also_in_the_training_rows"]},
    ])
    classes = pd.DataFrame({"class": list(dup["classes_all_rows"]), "all rows": list(dup["classes_all_rows"].values()),
                            "distinct records": [dup["classes_distinct_records"][k] for k in dup["classes_all_rows"]]})
    text = [
        "<!-- generated by python/sharedimp_exp/maternal_summary.py; do not edit -->", "",
        "## Duplicated rows in the Maternal Health Risk data", "",
        f"Source: `{dup['source_file']}` (sha256 `{dup['source_sha256'][:12]}`). Definitions: *identical record* = {ir['definition']}; "
        f"*identical features* = {fv['definition']}.", "",
        md_table(counts), "", md_table(classes), "",
        "Copies per record:", "", md_table(pd.read_csv(raw / "multiplicity.csv")), "",
        "Records not seen before, per block of 100 rows in file order:", "", md_table(pd.read_csv(raw / "first_occurrence.csv")), "",
        "## Files compared", "", md_table(variants.fillna("-")), "",
        "The feature values are identical in the three files (standardized once, with all rows); only rows and fold labels differ. "
        "Learners: as in experiment C (`linear`: multinomial logistic regression, checked between R and Python; `rand_forest`: language-specific settings, reported only).", "",
        "## Score of the Full model (mean over anchors and 5 splits; larger is better, losses are negated)", "",
        md_table(scores.astype({"variant": str})), "",
        "## Importance by file", "", md_table(wide), "",
        "## Agreement of the importances with the original analysis", "", md_table(rank, {"spearman_with_original": ".3f"}), "",
    ]
    (tables / "04b_maternal.md").write_text("\n".join(text))
    counts_status = table["status"].value_counts().to_dict()
    print(f"[maternal_summary] {counts_status}")
    return 1 if counts_status.get("FAIL", 0) else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
