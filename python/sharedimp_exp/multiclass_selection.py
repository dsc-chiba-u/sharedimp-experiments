"""Screening of the candidate multiclass data sets of experiment C.

    python -m sharedimp_exp.multiclass_selection config/04a_multiclass_selection.json results/raw/04a_multiclass_selection results/summary/04a_multiclass_selection

Criteria: docs/experiment_plan.md, section 5d (fixed before any candidate was
downloaded). E1, E2 and P1 are documentary and are copied from the config;
E3-E8 and P2 are computed here. The criteria are assessed in order; after
the first failure the later ones are recorded as "not assessed". Candidates
that fail E7 on the provider's metadata are not downloaded. No importance is
computed. Preprocessing and fold labels are those of real_data.py
(standardized features rounded to 6 decimals; seeded stratified folds), so
that E8 and P2 refer to the file workflow 04 would write.

For every candidate that passes E1-E8 the prepared file is written to
data/candidates/candidate_<id>.csv (with data/candidates/manifest.json) for
the pilot of criterion E9; these files are not used by any experiment.

Writes <raw>/screening.json, <summary>/criteria.csv (one row per candidate
and criterion), <summary>/candidates.csv and
results/tables/04a_multiclass_selection.md. Downloads go to
data/real/downloads/candidates/ (git-ignored).
"""

from __future__ import annotations

import io
import sys
import warnings
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss

from .common import DATA, ROOT, read_json, sha256, write_csv, write_json
from .make_synthetic import balanced_folds
from .real_data import fetch
from .rf_settings_summary import md_table

ORDER = ["E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8"]


def load(cid: str, spec: dict) -> pd.DataFrame:
    path = DATA / "real" / "downloads" / "candidates" / (cid + (".zip" if spec["format"].startswith("zip") else ".csv"))
    fetch(spec["url"], spec["sha256"], path)
    if spec["format"] == "csv":
        return pd.read_csv(path, encoding="utf-8-sig")
    with zipfile.ZipFile(path) as z:
        return pd.read_csv(io.BytesIO(z.read(spec["zip_member"])), sep=r"\s+", header=None, names=spec["columns"])


def fit_folds(Z: np.ndarray, y: np.ndarray, fold: np.ndarray) -> dict:
    """Unpenalized multinomial logistic regression per training fold: separation, warnings, CV scores."""
    classes = np.unique(y)
    acc_train, n_warn, ll, ll_prior, correct = [], 0, 0.0, 0.0, 0
    for lab in sorted(np.unique(fold)):
        tr, te = fold != lab, fold == lab
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            model = LogisticRegression(C=np.inf, tol=1e-10, max_iter=20000).fit(Z[tr], y[tr])
        n_warn += len(w)
        acc_train.append(float(model.score(Z[tr], y[tr])))
        prob = model.predict_proba(Z[te])
        prior = np.tile([(y[tr] == c).mean() for c in classes], (te.sum(), 1))
        ll += log_loss(y[te], prob, labels=classes, normalize=False)
        ll_prior += log_loss(y[te], prior, labels=classes, normalize=False)
        correct += int((model.predict(Z[te]) == y[te]).sum())
    n = len(y)
    return {"training_accuracy_per_fold": acc_train, "optimizer_warnings": n_warn, "cv_log_loss": ll / n,
            "cv_log_loss_of_class_proportions": ll_prior / n, "cv_accuracy": correct / n,
            "largest_class_share": float(max((y == c).mean() for c in classes))}


def screen(cid: str, spec: dict, cfg: dict) -> tuple[list[dict], dict]:
    th = cfg["thresholds"]
    rows, facts = [], {"downloaded": spec.get("download", True)}
    state = {"failed": False}

    def add(crit: str, status: str, observed: str) -> None:
        if state["failed"]:
            status, observed = "not assessed", "-"
        rows.append({"candidate": cid, "criterion": crit, "status": status, "observed": observed})
        if status == "fail":
            state["failed"] = True

    add("E1", spec["E1"]["status"], spec["E1"]["evidence"])
    add("E2", spec["E2"]["status"], spec["E2"]["evidence"])
    if not facts["downloaded"]:
        # only the provider's metadata are used: E7 is decided first, E3-E6 and E8 need the file
        n, p = spec["provider_n"], spec["provider_p"]
        ok = n <= th["E7_max_n"] and p <= th["E7_max_p"]
        for crit in ("E3", "E4", "E5", "E6"):
            rows.append({"candidate": cid, "criterion": crit, "status": "not assessed", "observed": "file not downloaded: E7 fails on the provider's metadata"})
        add("E7", "pass" if ok else "fail", f"provider: n = {n}, p = {p}")
        if ok:
            raise RuntimeError(f"{cid}: passes E7 on the metadata, so it must be downloaded and screened")
        add("E8", "not assessed", "-")
        facts.update({"n": n, "p": p})
        return rows, facts

    raw = load(cid, spec)
    feats = dict(spec["features"])
    df = raw[list(feats) + [spec["target"]]]
    n_raw = len(df)
    df = df.dropna()
    dropped_note = ""
    comb = spec.get("defined_combination")
    if comb:
        resid = float((df[comb["feature"]] - df[comb["equals"]].sum(axis=1)).abs().max())
        facts["defined_combination_max_abs_residual"] = resid
        if resid <= comb["tolerance"]:
            feats.pop(comb["feature"])
            dropped_note = f"; `{comb['feature']}` dropped ({comb['definition']}; largest deviation in the file {resid:.1e})"
    X = df[list(feats)].astype(float).rename(columns=feats)
    y = df[spec["target"]].astype(str).str.strip().str.replace(" ", "_").to_numpy()
    Z = ((X - X.mean()) / X.std(ddof=1)).round(cfg["decimals"])
    corr = np.abs(np.corrcoef(Z.to_numpy().T) - np.eye(Z.shape[1]))
    rank = int(np.linalg.matrix_rank(Z.to_numpy()))
    n, p = Z.shape
    largest = float(corr.max())
    facts.update({"n": n, "p": p, "features": list(Z.columns), "largest_abs_feature_correlation": largest, "rank": rank,
                  "condition_number": float(np.linalg.cond(Z.to_numpy())), "classes": {str(k): int(v) for k, v in pd.Series(y).value_counts().sort_index().items()}})
    add("E3", "pass" if p >= th["E3_min_features"] and largest >= th["E3_min_largest_abs_correlation"] and rank == p else "fail",
        f"{p} features, largest |correlation| {largest:.3f}, rank {rank}{dropped_note}")
    share_missing = (n_raw - n) / n_raw
    add("E4", "pass" if share_missing <= th["E4_max_share_rows_missing"] else "fail", f"{n_raw - n} of {n_raw} rows with a missing value")
    shared = int(X.duplicated(keep=False).sum())
    facts["rows_with_shared_feature_vector"] = shared
    facts["identical_records"] = int(pd.concat([X, pd.Series(y, index=X.index, name="y")], axis=1).duplicated().sum())
    add("E5", "pass" if shared / n <= th["E5_max_share_rows_with_shared_feature_vector"] else "fail",
        f"{shared} of {n} rows share their feature vector with another row")
    smallest = min(facts["classes"].values())
    add("E6", "pass" if smallest >= th["E6_min_rows_per_class"] else "fail", "; ".join(f"{k}: {v}" for k, v in facts["classes"].items()))
    add("E7", "pass" if n <= th["E7_max_n"] and p <= th["E7_max_p"] else "fail", f"n = {n}, p = {p}")
    if not state["failed"]:
        if shared:
            raise RuntimeError(f"{cid}: rows share a feature vector; group-aware folds (E5) are not implemented here")
        fold = balanced_folds(np.random.default_rng(spec["seed"]), n, cfg["folds"], strata=y)
        fit = fit_folds(Z.to_numpy(), y, fold)
        facts["fit"] = fit
        facts["prepared"] = pd.concat([pd.DataFrame({"fold": fold, "y": y}), Z.reset_index(drop=True)], axis=1)
        acc = fit["training_accuracy_per_fold"]
        ok = max(acc) < 1.0 and fit["optimizer_warnings"] == 0
        add("E8", "pass" if ok else "fail",
            f"training accuracy per fold {', '.join(f'{a:.4f}' for a in acc)}; {fit['optimizer_warnings']} optimizer warnings (scikit-learn; the R side is checked in workflow 04)")
    else:
        add("E8", "not assessed", "-")
    return rows, facts


def main(argv: list[str]) -> int:
    cfg, raw_dir, out = read_json(Path(argv[1])), Path(argv[2]), Path(argv[3])
    rows, cand, record, pilot = [], [], {}, {}
    cdir = DATA / "candidates"
    cdir.mkdir(parents=True, exist_ok=True)
    for old in cdir.glob("candidate_*.csv"):
        old.unlink()
    for cid, spec in cfg["candidates"].items():
        r, facts = screen(cid, spec, cfg)
        prepared = facts.pop("prepared", None)
        if prepared is not None and not any(x["status"] == "fail" for x in r):
            path = cdir / f"candidate_{cid}.csv"
            prepared.to_csv(path, index=False, float_format=f"%.{cfg['decimals']}f", lineterminator="\n")
            pilot[f"candidate_{cid}"] = {
                "file": path.name, "task": "classification", "target": "y", "fold": "fold", "features": facts["features"],
                "n": facts["n"], "p": facts["p"], "n_folds": cfg["folds"], "sha256": sha256(path), "title": spec["title"],
                "source": spec["source"], "url": spec["url"], "landing_page": spec["landing_page"], "doi": spec["doi"], "license": spec["license"],
                "retrieved": cfg["verified"], "source_sha256": spec["sha256"], "original_target": spec["target"], "original_features": spec["features"],
                "classes": facts["classes"],
                "preprocessing": f"columns selected and renamed; features standardized (all rows, ddof = 1) and rounded to {cfg['decimals']} decimals; fold labels from numpy default_rng({spec['seed']}), stratified by class",
            }
        rows += r
        failed = [x for x in r if x["status"] == "fail"]
        eligible = not failed
        rec = {"candidate": cid, "title": spec["title"], "source": spec["source"], "doi": spec["doi"], "license": spec["license"],
               "n": facts.get("n"), "p": facts.get("p"), "eligible_E1_to_E8": eligible,
               "first_failed_criterion": failed[0]["criterion"] if failed else "-",
               "P1_purpose": spec["P1"]["status"], "P2_cv_log_loss": None, "P2_cv_log_loss_of_class_proportions": None,
               "P2_cv_accuracy": None, "P2_largest_class_share": None, "P2": "not assessed"}
        if eligible:
            f = facts["fit"]
            rec.update({"P2_cv_log_loss": f["cv_log_loss"], "P2_cv_log_loss_of_class_proportions": f["cv_log_loss_of_class_proportions"],
                        "P2_cv_accuracy": f["cv_accuracy"], "P2_largest_class_share": f["largest_class_share"],
                        "P2": "pass" if f["cv_log_loss"] < f["cv_log_loss_of_class_proportions"] and f["cv_accuracy"] < 1 else "fail"})
        cand.append(rec)
        record[cid] = {"spec": {k: v for k, v in spec.items() if k not in ("E1", "E2", "P1")}, "facts": facts,
                       "documentary": {k: spec[k] for k in ("E1", "E2", "P1")}}
        print(f"[multiclass_selection] {cid}: {'eligible (E1-E8)' if eligible else 'fails ' + failed[0]['criterion']}")
    write_json({"description": "Candidate data sets that passed criteria E1-E8 of docs/experiment_plan.md, section 5d, prepared for the pilot of criterion E9 by "
                               "python/sharedimp_exp/multiclass_selection.py. Not used by any experiment. Modified versions of the originals (CC BY 4.0).",
                "datasets": pilot}, cdir / "manifest.json")
    criteria, cand = pd.DataFrame(rows), pd.DataFrame(cand)
    write_json({"config": argv[1], "verified": cfg["verified"], "thresholds": cfg["thresholds"], "candidates": record}, raw_dir / "screening.json")
    write_csv(criteria, out / "criteria.csv")
    write_csv(cand, out / "candidates.csv")
    wide = criteria.pivot(index="candidate", columns="criterion", values="status").reindex(index=list(cfg["candidates"]), columns=ORDER).reset_index()
    text = [
        "<!-- generated by python/sharedimp_exp/multiclass_selection.py; do not edit -->", "",
        "## Candidates for the multiclass data set of experiment C", "",
        "Criteria: docs/experiment_plan.md, section 5d. E1, E2 and P1 are documentary (evidence read on "
        f"{cfg['verified']}; {cfg['license_evidence']}); E3-E8 and P2 are computed from the downloaded files. "
        "Criteria are assessed in order; after the first failure the later ones are not assessed. E9 (R-Python agreement) "
        "is checked by workflow 04 for the data set that is used. No importance is computed here.", "",
        md_table(cand.astype(object).fillna("-").astype({"n": str, "p": str}), {"P2_cv_log_loss": ".4f", "P2_cv_log_loss_of_class_proportions": ".4f", "P2_cv_accuracy": ".4f", "P2_largest_class_share": ".4f"}), "",
        "P2: scores of unpenalized multinomial logistic regression on the features, 5 folds (the folds of the file workflow 04 writes), "
        "against predicting the class proportions of the training rows.", "",
        "## Status per criterion", "", md_table(wide), "",
        "## Observed values", "", md_table(criteria), "",
    ]
    (ROOT / "results" / "tables" / "04a_multiclass_selection.md").write_text("\n".join(text))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
