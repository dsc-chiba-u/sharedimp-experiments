"""Pilot of criterion E9 for the candidate multiclass data sets (docs/experiment_plan.md, section 5d).

    python -m sharedimp_exp.multiclass_pilot check  config/04a_pilot_jobs.json results/raw/04a_multiclass_pilot results/summary/04a_multiclass_pilot
    python -m sharedimp_exp.multiclass_pilot report config/04a_pilot_jobs.json results/raw/04a_multiclass_pilot results/summary/04a_multiclass_pilot results/summary/04a_multiclass_selection

check   runs check_jobs (the checker and tolerances of experiment C, unchanged).
        A failed parity check is the outcome of the pilot and does not stop
        the workflow; any other failed check does. Then, for every model of
        an accuracy job whose per-split score differs between R and Python,
        the representation is rebuilt with sharedimp's AnchorResidualizer,
        the Python learner of the job is refitted, and training rows,
        assessment rows and Python probabilities are written to <raw>/diag/
        for R/multiclass_pilot_diag.R (which refits nnet::multinom as the
        built-in R learner does).
report  reads the R probabilities and writes <summary>/{e9,flips}.csv,
        <summary>/decision.csv and results/tables/04a_multiclass_pilot.md.

The diagnosis explains a difference; it does not change the criterion.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import sharedimp

from . import check_jobs
from .common import ROOT, load_dataset, read_json, write_csv, write_json
from .learners import make_learner
from .rf_settings_summary import md_table


def differing_models(spec: dict, raw: Path) -> list[dict]:
    cells = []
    for job in spec["jobs"]:
        if job["metric"] != "accuracy":
            continue
        fr = pd.read_csv(raw / "r" / f"{job['id']}.folds.csv")
        fp = pd.read_csv(raw / "python" / f"{job['id']}.folds.csv")
        for which in ("full", "reduced"):
            d = (fr[f"score_{which}"] - fp[f"score_{which}"]).to_numpy()
            for i in np.flatnonzero(np.abs(d) > 1e-12):
                if which == "full" and any(c["job"] == job["id"] and c["fold"] == int(fr.fold[i]) and c["model"] == "full" for c in cells):
                    continue
                cells.append({"job": job["id"], "dataset": job["dataset"], "feature": fr.feature[i], "fold": int(fr.fold[i]), "model": which,
                              "n_test": int(fr.n_test[i]), "score_r": float(fr[f"score_{which}"][i]), "score_python": float(fp[f"score_{which}"][i])})
    return cells


def check(argv: list[str]) -> int:
    jobs_file, raw, out = Path(argv[2]), Path(argv[3]), Path(argv[4])
    spec = read_json(jobs_file)
    check_jobs.main(["check_jobs", str(jobs_file), str(raw), str(out)])
    checks = pd.read_csv(out / "checks.csv")
    other = checks[(checks["status"] == "FAIL") & ~checks["check"].str.endswith("/parity")]
    if len(other):
        print(f"[multiclass_pilot] failed checks other than parity: {other['check'].tolist()}")
        return 1
    diag = raw / "diag"
    diag.mkdir(parents=True, exist_ok=True)
    for old in diag.glob("*"):
        old.unlink()
    cells = differing_models(spec, raw)
    for k, c in enumerate(cells):
        ds = load_dataset(c["dataset"])
        X, y, fold = ds["X"], np.asarray(ds["y"]), np.asarray(ds["fold"])
        tr, te = fold != c["fold"], fold == c["fold"]
        res = sharedimp.AnchorResidualizer(anchor=c["feature"], drop_anchor=c["model"] == "reduced").fit(X[tr])
        rtr, rte = pd.DataFrame(np.asarray(res.transform(X[tr]))), pd.DataFrame(np.asarray(res.transform(X[te])))
        rtr.columns = rte.columns = [f"v{j + 1}" for j in range(rtr.shape[1])]
        est, description = make_learner("linear", "classification", len(np.unique(y)), 1)
        est.fit(rtr.to_numpy(), y[tr])
        prob = pd.DataFrame(est.predict_proba(rte.to_numpy()), columns=est.classes_)
        c.update({"id": f"cell{k + 1}", "python_learner": description,
                  "python_refit_accuracy": float((est.classes_[prob.to_numpy().argmax(axis=1)] == y[te]).mean())})
        rtr.assign(y=y[tr]).to_csv(diag / f"{c['id']}.train.csv", index=False, float_format="%.17g")
        rte.assign(y=y[te]).to_csv(diag / f"{c['id']}.test.csv", index=False, float_format="%.17g")
        prob.to_csv(diag / f"{c['id']}.prob_python.csv", index=False, float_format="%.17g")
    write_json({"cells": cells}, diag / "cells.json")
    print(f"[multiclass_pilot] {len(cells)} model(s) with a different per-split accuracy in R and Python")
    return 0


def report(argv: list[str]) -> int:
    jobs_file, raw, out, sel = Path(argv[2]), Path(argv[3]), Path(argv[4]), Path(argv[5])
    spec = read_json(jobs_file)
    checks, parity = pd.read_csv(out / "checks.csv"), pd.read_csv(out / "parity.csv")
    cand = pd.read_csv(sel / "candidates.csv")
    e9_rows = []
    for job in spec["jobs"]:
        p = parity[parity["job"] == job["id"]]
        meta = {lang: read_json(raw / lang / f"{job['id']}.meta.json") for lang in ("r", "python")}
        worst = p.loc[p["max_abs_diff"].idxmax()]
        e9_rows.append({"candidate": job["dataset"].removeprefix("candidate_"), "job": job["id"], "metric": job["metric"],
                        "max_abs_diff_r_python": float(worst["max_abs_diff"]), "in": f"{worst['table']} table, {worst['column']}",
                        "max_abs_diff_summary_table": float(p[p["table"] == "summary"]["max_abs_diff"].max()),
                        "tolerance": float(worst["tolerance"]), "warnings_r": len(meta["r"]["warnings"]), "warnings_python": len(meta["python"]["warnings"]),
                        "status": "pass" if float(worst["max_abs_diff"]) <= float(worst["tolerance"]) else "fail"})
    e9 = pd.DataFrame(e9_rows)
    write_csv(e9, out / "e9.csv")

    cells = read_json(raw / "diag" / "cells.json")["cells"]
    flip_rows = []
    for c in cells:
        test = pd.read_csv(raw / "diag" / f"{c['id']}.test.csv")
        pp = pd.read_csv(raw / "diag" / f"{c['id']}.prob_python.csv")
        pr = pd.read_csv(raw / "diag" / f"{c['id']}.prob_r.csv")[pp.columns]
        conv = read_json(raw / "diag" / f"{c['id']}.r.json")
        a, b = pp.to_numpy(), pr.to_numpy()
        cls = np.asarray(pp.columns)
        diff_rows = np.flatnonzero(a.argmax(axis=1) != b.argmax(axis=1))
        top2 = lambda m: np.sort(m, axis=1)[:, -1] - np.sort(m, axis=1)[:, -2]  # noqa: E731
        y = test["y"].to_numpy()
        flip_rows.append({
            "candidate": c["dataset"].removeprefix("candidate_"), "anchor": c["feature"], "fold": c["fold"], "model": c["model"], "assessment_rows": c["n_test"],
            "accuracy_r_job": c["score_r"], "accuracy_python_job": c["score_python"],
            "accuracy_r_refit": float((cls[b.argmax(axis=1)] == y).mean()), "accuracy_python_refit": c["python_refit_accuracy"],
            "r_convergence_code": conv["convergence"], "largest_abs_probability_difference": float(np.abs(a - b).max()),
            "rows_classified_differently": len(diff_rows),
            "largest_top2_margin_of_those_rows_python": float(top2(a)[diff_rows].max()) if len(diff_rows) else np.nan,
            "largest_top2_margin_of_those_rows_r": float(top2(b)[diff_rows].max()) if len(diff_rows) else np.nan,
            "accuracy_difference_of_one_row": 1.0 / c["n_test"],
        })
    flips = pd.DataFrame(flip_rows)
    write_csv(flips, out / "flips.csv")

    dec_rows = []
    for r in cand.itertuples():
        mine = e9[e9["candidate"] == r.candidate]
        if not r.eligible_E1_to_E8:
            e9_status, eligible = "not assessed", False
        else:
            e9_status = "pass" if len(mine) and (mine["status"] == "pass").all() and not mine[["warnings_r", "warnings_python"]].to_numpy().any() else "fail"
            eligible = e9_status == "pass"
        dec_rows.append({"candidate": r.candidate, "E1_to_E8": "pass" if r.eligible_E1_to_E8 else f"fail ({r.first_failed_criterion})", "E9": e9_status,
                         "eligible": eligible, "P1_purpose": r.P1_purpose, "P2": r.P2})
    dec = pd.DataFrame(dec_rows)
    n_ok = int(dec["eligible"].sum())
    outcome = ("no candidate is eligible: nothing is replaced; the group-aware Maternal analysis (maternal_grouped) stays the provisional multiclass example"
               if n_ok == 0 else f"{n_ok} eligible candidate(s): {', '.join(dec[dec['eligible']]['candidate'])}; choice by P1-P3")
    write_csv(dec, out / "decision.csv")
    write_json({"eligible": dec[dec["eligible"]]["candidate"].tolist(), "outcome": outcome}, out / "decision.json")
    text = [
        "<!-- generated by python/sharedimp_exp/multiclass_pilot.py; do not edit -->", "",
        "## Pilot of criterion E9 and outcome of the selection", "",
        "Criteria: docs/experiment_plan.md, section 5d. Pilot: the `linear` learner (unpenalized multinomial logistic regression) with log-loss and accuracy, "
        "the same file and fold column in R and Python, checker and tolerance of experiment C (`multinomial`, 1e-3; not changed).", "",
        md_table(dec), "", f"**Outcome: {outcome}.**", "",
        "## E9: R-Python difference per job", "",
        md_table(e9, {"max_abs_diff_r_python": ".3g", "max_abs_diff_summary_table": ".3g", "tolerance": "g"}), "",
        "`max_abs_diff_r_python` is the largest absolute difference over all numeric columns of the summary table and of the per-split table, as in every parity check of this repository.", "",
        "## Models whose per-split accuracy differs between R and Python", "",
        "For each such model the representation was rebuilt (sharedimp-py's AnchorResidualizer, training rows of the split), the Python learner of the job was refitted "
        "and R refitted `nnet::multinom(maxit = 500)` on the same files, as the built-in R learner does. This explains the difference; it does not alter the criterion.", "",
        md_table(flips, {"largest_abs_probability_difference": ".3g", "largest_top2_margin_of_those_rows_python": ".3g", "largest_top2_margin_of_those_rows_r": ".3g",
                         "accuracy_difference_of_one_row": ".3g", "accuracy_r_job": ".6f", "accuracy_python_job": ".6f", "accuracy_r_refit": ".6f", "accuracy_python_refit": ".6f"}) if len(flips) else "(none)", "",
        "`largest_top2_margin_*`: difference between the two largest class probabilities of the rows that the two languages classify differently.", "",
    ]
    (ROOT / "results" / "tables" / "04a_multiclass_pilot.md").write_text("\n".join(text))
    print(f"[multiclass_pilot] {outcome}")
    return 0


if __name__ == "__main__":
    raise SystemExit({"check": check, "report": report}[sys.argv[1]](sys.argv))
