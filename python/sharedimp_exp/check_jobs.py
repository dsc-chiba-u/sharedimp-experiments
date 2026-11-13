"""Compare the R and Python raw results of a job file and evaluate the checks.

    python -m sharedimp_exp.check_jobs config/02_validation_jobs.json results/raw/02_validation results/summary/02_validation

Writes (all derived from the raw files, nothing typed by hand):

    importance_long.csv     every summary table, both languages, long format
    parity.csv              max |R - Python| per job, table and column
    positive_control.csv    positive control against its closed-form target (if the job file has one)
    checks.csv              one row per check with criterion, observed value, status
    results/tables/<output directory name>_checks.md   the same as a Markdown table

The criteria are fixed in docs/experiment_plan.md (section "Phase 1 checks")
and in the job file; this script only evaluates them. Exit status 1 if any
check fails.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from .common import ROOT, find_dataset, read_json, write_csv

SUMMARY_COLS = ["feature", "importance", "importance_std", "score_full", "score_reduced", "n_splits"]
FOLD_COLS = ["feature", "fold", "n_train", "n_test", "score_full", "score_reduced", "importance"]
EXACT_COLS = {"feature", "fold", "n_train", "n_test", "n_splits"}

# Positive-control criteria (docs/experiment_plan.md)
PC_REL_TOL = 0.10  # |CV estimate - sample plug-in| / plug-in, signal-carrying features
PC_NOISE_ABS = 0.05  # |importance| of the pure-noise feature x4 (OLS)
PC_RF_NOISE_FRACTION = 0.10  # |importance(x4)| <= fraction * importance(x1) (random forest)


def load(raw: Path, lang: str, job_id: str):
    meta = read_json(raw / lang / f"{job_id}.meta.json")
    if meta["status"] != "ok":
        return meta, None, None
    imp = pd.read_csv(raw / lang / f"{job_id}.importance.csv")
    folds = pd.read_csv(raw / lang / f"{job_id}.folds.csv")
    return meta, imp, folds


def main(argv: list[str]) -> int:
    spec = read_json(Path(argv[1]))
    raw, out = Path(argv[2]), Path(argv[3])
    checks: list[dict] = []
    parity_rows: list[dict] = []
    long_rows: list[pd.DataFrame] = []
    results: dict[tuple[str, str], pd.DataFrame] = {}

    def check(check_id: str, description: str, criterion: str, observed, passed: bool | None):
        status = "reported" if passed is None else ("pass" if passed else "FAIL")
        checks.append(
            {"check": check_id, "description": description, "criterion": criterion, "observed": observed, "status": status}
        )

    for job in spec["jobs"]:
        jid = job["id"]
        (mr, ir, fr), (mp, ip, fp) = load(raw, "r", jid), load(raw, "python", jid)
        ran = mr["status"] == "ok" and mp["status"] == "ok"
        check(f"{jid}/ran", "job completed in R and Python", "status ok in both", f"r={mr['status']}, python={mp['status']}", ran)
        if not ran:
            continue
        same_input = mr["dataset_sha256"] == mp["dataset_sha256"]
        check(f"{jid}/input", "both languages read the same data file", "identical sha256", mr["dataset_sha256"][:12], same_input)
        schema = list(ir.columns) == SUMMARY_COLS and list(ip.columns) == SUMMARY_COLS
        schema = schema and all(c in fr.columns for c in FOLD_COLS) and all(c in fp.columns for c in FOLD_COLS)
        check(f"{jid}/schema", "common output schema", "summary columns equal; per-split common columns present", "", schema)
        for lang, imp in (("r", ir), ("python", ip)):
            results[(jid, lang)] = imp
            long_rows.append(imp.assign(job=jid, dataset=job["dataset"], learner=job["learner"], metric=job["metric"], language=lang))

        tol = spec["parity_classes"][job["parity"]]["tolerance"]
        worst = 0.0
        labels_equal = True
        for table, a, b, cols in (("summary", ir, ip, SUMMARY_COLS), ("per_split", fr, fp, FOLD_COLS)):
            if len(a) != len(b):
                labels_equal = False
                continue
            for col in cols:
                if col in EXACT_COLS:
                    equal = a[col].astype(str).tolist() == b[col].astype(str).tolist()
                    labels_equal = labels_equal and equal
                    continue
                diff = float(np.max(np.abs(a[col].to_numpy(float) - b[col].to_numpy(float))))
                worst = max(worst, diff)
                parity_rows.append(
                    {"job": jid, "parity_class": job["parity"], "table": table, "column": col, "max_abs_diff": diff, "tolerance": tol}
                )
        check(f"{jid}/layout", "row order, features, fold labels, split sizes", "identical in R and Python", "", labels_equal)
        check(
            f"{jid}/parity",
            f"max |R - Python| over all numeric columns of both tables ({job['parity']})",
            "reported only (language-specific learner)" if tol is None else f"<= {tol:g}",
            f"{worst:.3g}",
            None if tol is None else worst <= tol,
        )
        if job["learner"] == "linear" and mr["task"] == "regression":
            # OLS on Full_i spans the same column space for every anchor i.
            spread = max(float(f.groupby("fold")["score_full"].agg(np.ptp).max()) for f in (fr, fp))
            check(f"{jid}/full_invariance", "OLS full score identical for every anchor within a split", "<= 1e-8", f"{spread:.3g}", spread <= 1e-8)

    # ---------------------------------------------------------- positive control
    pc_rows = []
    pc_spec = spec.get("positive_control")
    if pc_spec is None:
        pass
    elif all((pc_spec["linear_job"], lang) in results for lang in ("r", "python")):
        entry, _ = find_dataset(pc_spec["dataset"])
        ref = entry["reference"]
        feats = entry["features"]
        for f in feats:
            row = {"feature": f, "population": ref["population"][f], "sample_plugin": ref["sample_plugin"][f]}
            for jid, tag in ((pc_spec["linear_job"], "linear"), (pc_spec["rand_forest_job"], "rand_forest")):
                for lang in ("r", "python"):
                    if (jid, lang) in results:
                        imp = results[(jid, lang)].set_index("feature")
                        row[f"{tag}_{lang}"] = float(imp.loc[f, "importance"])
                        row[f"{tag}_{lang}_std"] = float(imp.loc[f, "importance_std"])
            pc_rows.append(row)
        pc = pd.DataFrame(pc_rows).set_index("feature")
        signal = [f for f in feats if ref["population"][f] > 0]
        noise = [f for f in feats if ref["population"][f] == 0]
        for lang in ("r", "python"):
            est = pc[f"linear_{lang}"]
            rel = float(((est[signal] - pc.loc[signal, "sample_plugin"]).abs() / pc.loc[signal, "sample_plugin"]).max())
            check(f"pc/linear/{lang}/target", "OLS+MSE importance vs full-sample plug-in of Cov(y,x)^2/Var(x), signal features", f"relative deviation <= {PC_REL_TOL:g}", f"{rel:.3g}", rel <= PC_REL_TOL)
            nz = float(est[noise].abs().max())
            check(f"pc/linear/{lang}/noise", "OLS+MSE importance of the pure-noise feature", f"|importance| <= {PC_NOISE_ABS:g}", f"{nz:.3g}", nz <= PC_NOISE_ABS)
            order = est["x1"] > est["x2"] > max(est["x3"], est["x5"]) > min(est["x3"], est["x5"]) > est["x4"]
            check(f"pc/linear/{lang}/order", "ordering implied by the closed form", "x1 > x2 > {x3, x5} > x4", " > ".join(est.sort_values(ascending=False).index), bool(order))
            col = f"rand_forest_{lang}"
            if col in pc:
                rf = pc[col]
                ok = rf.idxmax() == "x1" and abs(rf["x4"]) <= PC_RF_NOISE_FRACTION * rf["x1"]
                check(f"pc/rand_forest/{lang}/qualitative", "random forest: x1 ranked first, noise feature near zero", f"argmax = x1 and |imp(x4)| <= {PC_RF_NOISE_FRACTION:g} * imp(x1)", f"argmax={rf.idxmax()}, imp(x4)/imp(x1)={rf['x4'] / rf['x1']:.3g}", bool(ok))
        if {"rand_forest_r", "rand_forest_python"} <= set(pc.columns):
            rho = float(pc["rand_forest_r"].corr(pc["rand_forest_python"], method="spearman"))
            check("pc/rand_forest/cross_language", "random forest, R (ranger) vs Python (scikit-learn): Spearman correlation of importances", "reported only", f"{rho:.3g}", None)
        write_csv(pc.reset_index(), out / "positive_control.csv")
    else:
        check("pc/available", "positive-control results available", "linear job ran in both languages", "missing", False)

    cols = ["job", "dataset", "learner", "metric", "language", *SUMMARY_COLS]
    if long_rows:
        write_csv(pd.concat(long_rows, ignore_index=True)[cols], out / "importance_long.csv")
    write_csv(pd.DataFrame(parity_rows), out / "parity.csv")
    table = pd.DataFrame(checks)
    write_csv(table, out / "checks.csv")
    md = ["| check | description | criterion | observed | status |", "|---|---|---|---|---|"]
    md += [f"| `{r.check}` | {r.description} | {r.criterion} | {r.observed} | {r.status} |" for r in table.itertuples()]
    tables = ROOT / "results" / "tables"
    tables.mkdir(parents=True, exist_ok=True)
    (tables / f"{out.name}_checks.md").write_text(
        f"<!-- generated by python/sharedimp_exp/check_jobs.py from {argv[1]}; do not edit -->\n" + "\n".join(md) + "\n"
    )

    counts = table["status"].value_counts().to_dict()
    print(f"[check_jobs] {out.name}: {counts}")
    for r in table[table["status"] == "FAIL"].itertuples():
        print(f"  FAIL {r.check}: {r.description} (criterion {r.criterion}; observed {r.observed})")
    return 1 if counts.get("FAIL", 0) else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
