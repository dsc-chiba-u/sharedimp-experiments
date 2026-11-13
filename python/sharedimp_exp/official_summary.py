"""Evaluate experiment B (comparison with the official UMFI-LR code).

    python -m sharedimp_exp.official_summary config/03_official_umfi.json config/03_api_comparison.json results/raw/03_official_umfi results/summary/03_official_umfi

Everything is derived from the raw files. Checks with a criterion (fixed in
the config file before the run) are pass/FAIL; everything else is "reported".
Exit status 1 if a check fails.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from .common import ROOT, load_dataset, read_json, write_csv
from .rf_settings_summary import md_table

def read_raw(path: Path) -> pd.DataFrame:
    """read_csv that keeps strings such as "null" as they are (only "NA" is missing)."""
    return pd.read_csv(path, keep_default_na=False, na_values=["NA"])


LABEL = {
    "official_r": "official R (HydroML/UMFI): ranger, 100 trees, OOB R^2, floors",
    "original_r": "original R script (joej1997/UMFI): same rule",
    "official_py/extra_trees": "official Python (guanton/umfi_python): extra trees, OOB R^2, floors, mean of 10 runs",
    "official_py/random_forest": "official Python, RF=True: random forest, OOB R^2, floors, mean of 10 runs",
    "sharedimp_r/rand_forest": "sharedimp (R): built-in forest, 5-fold, r2",
    "sharedimp_py/rand_forest": "sharedimp (Python): forest of specification 8.2, 5-fold, r2",
    "sharedimp_r/linear": "sharedimp (R): OLS, 5-fold, r2",
    "sharedimp_py/linear": "sharedimp (Python): OLS, 5-fold, r2",
}


def main(argv: list[str]) -> int:
    cfg, api_cfg, raw, out = read_json(Path(argv[1])), read_json(Path(argv[2])), Path(argv[3]), Path(argv[4])
    tol = cfg["criteria"]["tolerance"]
    sources = read_json(raw / "sources.json")["sources"]
    checks: list[dict] = []

    def check(check_id, description, criterion, observed, passed):
        status = "reported" if passed is None else ("pass" if passed else "FAIL")
        checks.append({"check": check_id, "description": description, "criterion": criterion, "observed": observed, "status": status})

    # ------------------------------------------------------------ B1, B2
    reps = pd.concat(
        [read_raw(raw / f"representations_{name}.csv") for name in ("r", "official_py", "sharedimp_py")], ignore_index=True
    )
    gates = read_raw(raw / "gates.csv")
    gates["fired_official_r"] = gates["p_value"] < 0.01
    gates["fired_official_py"] = gates["r_squared"] > 0.01
    gates["fired_original_r"] = gates["fired_official_r"]
    full = reps[reps["representation"] == "full"].set_index(["implementation", "dataset", "anchor", "feature", "row"])["value"].sort_index()
    rawdata = {ds: load_dataset(ds)["X"] for ds in cfg["representation_datasets"]}
    pairs = [("official_r", "sharedimp_r"), ("original_r", "sharedimp_r"), ("official_py", "sharedimp_py")]
    rows = []
    for g in gates.itertuples():
        rawcol = rawdata[g.dataset][g.feature].to_numpy()
        for off, si in pairs:
            a = full.loc[(off, g.dataset, g.anchor, g.feature)].to_numpy()
            b = full.loc[(si, g.dataset, g.anchor, g.feature)].to_numpy()
            rows.append(
                {
                    "dataset": g.dataset, "anchor": g.anchor, "feature": g.feature, "n": g.n,
                    "official": off, "sharedimp": si, "p_value": g.p_value, "r_squared": g.r_squared,
                    "gate_fired": bool(getattr(g, f"fired_{off}")),
                    # R implementations: decided inside R (gates.csv); Python: both sides parsed by pandas
                    "official_equals_raw": bool(getattr(g, f"{off}_equals_raw")) if off.endswith("_r") else bool(np.array_equal(a, rawcol)),
                    "max_abs_diff_official_vs_sharedimp": float(np.max(np.abs(a - b))),
                    "max_abs_diff_sharedimp_vs_raw": float(np.max(np.abs(b - rawcol))),
                }
            )
    resid = pd.DataFrame(rows)
    write_csv(resid, out / "residualization.csv")
    for off, si in pairs:
        d = resid[resid["official"] == off]
        fired, not_fired = d[d["gate_fired"]], d[~d["gate_fired"]]
        check(f"B1/gate_rule/{off}", "the official column differs from the raw column exactly where the dependence test (recomputed independently) passes",
              "gate fired <=> official column != raw column", f"{len(d)} feature pairs, {int(d['gate_fired'].sum())} fired",
              bool((d["gate_fired"] != d["official_equals_raw"]).all()))
        check(f"B1/gate_fired/{off}", f"residuals of {off} vs {si}, same rows, pairs where the official test passes", f"<= {tol:g}",
              f"{fired['max_abs_diff_official_vs_sharedimp'].max():.3g} over {len(fired)} pairs", bool(fired["max_abs_diff_official_vs_sharedimp"].max() <= tol))
        check(f"B1/gate_not_fired/{si}" if off != "original_r" else "B1/gate_not_fired/original_r_vs_sharedimp_r",
              f"pairs where the official test of {off} fails: official keeps the raw column, {si} residualizes",
              "reported (design difference)",
              f"{len(not_fired)} pairs; max |official - sharedimp| = {not_fired['max_abs_diff_official_vs_sharedimp'].max():.3g}" if len(not_fired) else "0 pairs", None)
    gr, gp = gates["fired_official_r"], gates["fired_official_py"]
    check("B1/official_gates_differ", "the two official implementations use different dependence tests (p < 0.01 vs R^2 > 0.01)",
          "reported", f"{int((gr != gp).sum())} of {len(gates)} feature pairs are residualized by one official implementation and not by the other", None)
    a = full.loc["sharedimp_r"]
    b = full.loc["sharedimp_py"].reindex(a.index)
    parse = max(float(np.max(np.abs(full.loc[("sharedimp_r", ds, a_, a_)].to_numpy() - X[a_].to_numpy()))) for ds, X in rawdata.items() for a_ in X.columns)
    check("B1/number_parsing", "raw anchor column as parsed by R (read.csv) vs as parsed by pandas from the same 6-decimal text",
          "reported", f"max |difference| = {parse:.3g}", None)
    check("B1/sharedimp_r_vs_py", "Full representation of sharedimp (R) vs sharedimp (Python), fitted and applied on all rows", f"<= {tol:g}",
          f"{float((a - b).abs().max()):.3g}", bool((a - b).abs().max() <= tol))

    pos = reps.drop_duplicates(["implementation", "representation", "dataset", "anchor", "feature"]).set_index(
        ["implementation", "representation", "dataset", "anchor", "feature"])["position"]
    layout_ok, anchor_ok, reduced_ok = True, True, True
    for ds, X in rawdata.items():
        for anchor in X.columns:
            expected = {f: k + 1 for k, f in enumerate(X.columns)}
            for impl in ("official_r", "original_r", "official_py", "sharedimp_r", "sharedimp_py"):
                got = pos.loc[(impl, "full", ds, anchor)].to_dict()
                layout_ok &= got == expected
                if impl.endswith("_py"):
                    anchor_ok &= bool(np.array_equal(full.loc[(impl, ds, anchor, anchor)].to_numpy(), X[anchor].to_numpy()))
    anchor_ok &= bool(gates[[f"{impl}_anchor_equals_raw" for impl in ("official_r", "original_r", "sharedimp_r")]].to_numpy().all())
    red = reps[reps["representation"] == "reduced"].set_index(["implementation", "dataset", "anchor", "feature", "row"])["value"].sort_index()
    for impl in ("sharedimp_r", "sharedimp_py"):
        f = full.loc[impl]
        f = f[f.index.get_level_values("anchor") != f.index.get_level_values("feature")]
        r = red.loc[impl]
        reduced_ok &= bool(f.index.equals(r.index) and np.array_equal(f.to_numpy(), r.to_numpy()))
        for ds, X in rawdata.items():
            for anchor in X.columns:
                exp = {f_: k + 1 for k, f_ in enumerate(c for c in X.columns if c != anchor)}
                reduced_ok &= pos.loc[(impl, "reduced", ds, anchor)].to_dict() == exp
    check("B2/layout", "Full representation: all features, original column order, in every implementation", "identical", "", bool(layout_ok))
    check("B2/anchor", "anchor column of the Full representation equals the raw anchor, in every implementation", "exactly equal", "", bool(anchor_ok))
    check("B2/reduced", "sharedimp Reduced representation = Full representation without the anchor column (the official code drops the anchor column from its Full representation in the call to the learner)",
          "exactly equal, same order", "", bool(reduced_ok))

    # ------------------------------------------------------------ B3
    ident = pd.concat([read_raw(raw / "identical_r.csv"), read_raw(raw / "identical_python.csv")], ignore_index=True)
    ident["abs_diff"] = (ident["official"] - ident["official_rule_on_sharedimp_representation"]).abs()
    ident["abs_diff_original"] = (ident["official"] - ident["original"]).abs()
    isum = ident.groupby(["language", "dataset", "forest"], sort=False).agg(
        n_values=("abs_diff", "size"), n_seeds=("seed", "nunique"),
        max_abs_diff_official_vs_rule_on_sharedimp=("abs_diff", "max"),
        max_abs_diff_official_r_vs_original_r=("abs_diff_original", "max"),
        mean_official_importance=("official", "mean")).reset_index()
    ic = cfg["identical_condition"]
    isum["condition"] = np.where(isum["dataset"] == ic["dataset"], "every dependence test passes (identical representations)", "some dependence tests fail (representations differ)")
    write_csv(isum, out / "identical_condition.csv")
    for r in isum.itertuples():
        same = r.dataset == ic["dataset"]
        check(f"B3/{r.language}/{r.forest}/{r.dataset}", "official importance vs the official scoring rule applied to sharedimp's all-rows representation (same seed, same order of fits)",
              f"<= {tol:g}" if same else "reported (representations differ where the official test fails)",
              f"{r.max_abs_diff_official_vs_rule_on_sharedimp:.3g}", bool(r.max_abs_diff_official_vs_rule_on_sharedimp <= tol) if same else None)
    ro = isum[isum["language"] == "r"]["max_abs_diff_official_r_vs_original_r"].max()
    check("B3/official_r_vs_original_r", "HydroML/UMFI umfi() vs UMFI() of the original script, same seed", f"<= {tol:g}", f"{ro:.3g}", bool(ro <= tol))

    # ------------------------------------------------------------ B4, B6
    designs = cfg["designs"]["official_generators"] + [cfg["designs"]["null"]["name"]]
    off = pd.concat([read_raw(raw / "importance" / f"{d}.{impl}.csv") for d in designs for impl in ("official_r", "official_py")], ignore_index=True)
    off["variant"] = np.where(off["implementation"] == "official_py", off["implementation"] + "/" + off["forest"], off["implementation"])
    off_run = off.copy()  # one row per run (iteration)
    off_seed = off.groupby(["variant", "design", "seed", "feature"], sort=False)["importance"].mean().reset_index()
    si = pd.concat([read_raw(raw / "importance" / f"{d}.{impl}.csv") for d in designs for impl in ("sharedimp_r", "sharedimp_py")], ignore_index=True)
    si["variant"] = si["implementation"] + "/" + si["learner"]
    per_seed = pd.concat([off_seed, si[["variant", "design", "seed", "feature", "importance"]]], ignore_index=True)
    by_design = per_seed.groupby(["design", "feature", "variant"], sort=False).agg(
        mean=("importance", "mean"), sd_between_seeds=("importance", "std"), min=("importance", "min"), max=("importance", "max"),
        n_seeds=("seed", "nunique")).reset_index()
    by_design["description"] = by_design["variant"].map(LABEL)
    write_csv(by_design, out / "importance_by_design.csv")
    # single evaluations (one official run, one sharedimp cross-validated estimate), null design
    single = pd.concat([off_run[["variant", "design", "importance"]], si[["variant", "design", "importance"]]], ignore_index=True)
    neg = single[single["design"] == cfg["designs"]["null"]["name"]].groupby("variant", sort=False)["importance"].agg(
        n_values="size", mean="mean", min="min", max="max",
        share_negative=lambda v: float((v < 0).mean()), share_exactly_zero=lambda v: float((v == 0).mean())).reset_index()
    neg["description"] = neg["variant"].map(LABEL)
    write_csv(neg, out / "negative_importance.csv")
    for r in neg.itertuples():
        name = r.variant.split("/")[0] if r.variant.startswith("sharedimp") and r.variant.endswith("rand_forest") else r.variant
        check(f"B6/{name}", f"null design (response independent of the features), {r.description}", "reported (design difference)",
              f"{r.n_values} values: mean {r.mean:.3g}, min {r.min:.3g}, share < 0: {r.share_negative:.2f}, share == 0: {r.share_exactly_zero:.2f}", None)
    wide = by_design.pivot_table(index=["design", "feature"], columns="variant", values="mean", sort=False)
    d = (wide["official_r"] - wide["sharedimp_r/rand_forest"]).abs()
    check("B4/official_r_vs_sharedimp_r", "official R (all rows, OOB R^2, 100 trees, floors) vs sharedimp R (fold-internal, 5-fold r2, 500 trees), mean over seeds, non-null designs",
          "reported (procedures differ)", f"largest |difference of means| = {d[d.index.get_level_values('design') != cfg['designs']['null']['name']].max():.3g}", None)
    d = (wide["official_py/random_forest"] - wide["sharedimp_py/rand_forest"]).abs()
    check("B4/official_py_vs_sharedimp_py", "official Python with RF=True vs sharedimp Python, mean over seeds, non-null designs",
          "reported (procedures differ)", f"largest |difference of means| = {d[d.index.get_level_values('design') != cfg['designs']['null']['name']].max():.3g}", None)

    # ------------------------------------------------------------ B5
    st = {lang: read_json(raw / f"structural_{lang}.json") for lang in ("r", "python")}
    sr, sp = st["r"]["sharedimp_r"], st["python"]
    check("B5a/r", f"sharedimp (R): training representation passed to the learner after perturbing the {st['r']['n_assessment']} assessment rows",
          "bit-identical", f"{sr['learner_fits_compared']} fits, max |diff| = {sr['max_abs_diff_training_representation']}", bool(sr["bit_identical"]))
    check("B5a/python", f"sharedimp (Python): the same", "bit-identical",
          f"{sp['learner_fits_compared']} fits, max |diff| = {sp['max_abs_diff_training_representation']}", bool(sp["bit_identical"]))
    check("B5a/official_r", "official preprocess_lr() on all rows: residuals of the training rows after the same perturbation", "reported",
          f"max |diff| = {st['r']['official_r']['max_abs_diff_training_rows_of_representation']:.3g}", None)

    leak = read_raw(raw / "leak.csv")
    dmax = float((leak["package"] - leak["fold_internal"]).abs().max())
    check("B5b/pipeline", "step-by-step fold-internal pipeline (build_representations + lm.fit + MSE) vs shared_importance()", f"<= {tol:g}",
          f"{dmax:.3g} over {len(leak)} values", bool(dmax <= tol))
    population = {"x1": 4.0, "x2": 2.56, "x3": 1.0, "x4": 0.0, "x5": 1.0 / 1.01}
    leak["population"] = leak["feature"].map(population)
    lsum = leak.groupby(["n", "feature"], sort=False).agg(
        population=("population", "first"), fold_internal=("fold_internal", "mean"), all_rows=("all_rows", "mean"),
        all_rows_official_gate=("all_rows_official_gate", "mean"), sd_fold_internal=("fold_internal", "std"), n_seeds=("seed", "nunique")).reset_index()
    lsum["all_rows_minus_fold_internal"] = lsum["all_rows"] - lsum["fold_internal"]
    write_csv(lsum, out / "leak.csv")
    lagg = lsum[lsum["feature"] != "x4"].assign(rel=lambda t: t["all_rows_minus_fold_internal"] / t["fold_internal"]).groupby("n")["rel"].mean()
    check("B5b/all_rows_effect", "all-rows residualization vs fold-internal residualization, otherwise identical 5-fold CV (OLS, MSE): mean relative change of the importance of x1, x2, x3, x5",
          "reported", "; ".join(f"n={n}: {v:+.1%}" for n, v in lagg.items()), None)

    # ------------------------------------------------------------ B7
    api = {"official_py": read_json(raw / "api_official_py.json"), "sharedimp_py": read_json(raw / "api_sharedimp_py.json")}
    api_r = read_json(raw / "api_r.json")
    sigs = {"official_py": api["official_py"]["signatures"], "sharedimp_py": api["sharedimp_py"]["signatures"],
            "official_r": api_r["signatures"]["official_r"], "sharedimp_r": api_r["signatures"]["sharedimp_r"]}
    check_ids = {c["check"]: c["status"] for c in checks}
    api_rows, missing = [], []
    for row in api_cfg["rows"]:
        rec = {"aspect": row["aspect"]}
        for col in api_cfg["columns"]:
            cell = row[col]
            ev = []
            for e in cell.get("evidence", []):
                path = ROOT / sources[e["source"]]["directory"] / e["file"]
                lines = [k + 1 for k, line in enumerate(path.read_text().splitlines()) if e["pattern"] in line]
                if not lines:
                    missing.append(f"{e['file']}: {e['pattern']}")
                ev.append(f"{e['file']}:{lines[0] if lines else '?'}")
            if "signature" in cell:
                if cell["signature"] not in sigs[col]:
                    missing.append(f"{col}: signature {cell['signature']}")
                ev.append(f"signature of {cell['signature']}()")
            if "check" in cell:
                if cell["check"] not in check_ids:
                    missing.append(f"{col}: check {cell['check']}")
                ev.append(f"check {cell['check']}")
            rec[col] = cell["text"]
            rec[f"{col}_evidence"] = "; ".join(ev)
        api_rows.append(rec)
    api_df = pd.DataFrame(api_rows)
    write_csv(api_df, out / "api.csv")
    check("B7/evidence", "every statement of the API table is backed by a source line at the pinned commit, a recorded signature or an executed check",
          "all found", "all found" if not missing else "missing: " + " | ".join(missing), not missing)

    # ------------------------------------------------------------ output
    table = pd.DataFrame(checks)
    write_csv(table, out / "checks.csv")
    tables = ROOT / "results" / "tables"
    tables.mkdir(parents=True, exist_ok=True)
    head = "<!-- generated by python/sharedimp_exp/official_summary.py from config/03_official_umfi.json; do not edit -->"
    (tables / "03_official_umfi_checks.md").write_text(
        head + "\n" + md_table(table.assign(check=lambda t: "`" + t["check"] + "`").astype(str)) + "\n")
    src = pd.DataFrame([{"implementation": k, "repository": v["repository"], "commit": v["commit"], "license file": v["license_file"] or "none",
                         "files read": ", ".join(v["files_used"])} for k, v in sources.items()])
    gate_tab = resid.groupby(["dataset", "official", "gate_fired"], sort=False).agg(
        feature_pairs=("feature", "size"), official_equals_raw=("official_equals_raw", "all"),
        max_abs_diff_official_vs_sharedimp=("max_abs_diff_official_vs_sharedimp", "max")).reset_index()
    api_md = pd.DataFrame({"aspect": api_df["aspect"], **{api_cfg["columns"][c]: api_df[c] + " [" + api_df[f"{c}_evidence"] + "]" for c in api_cfg["columns"]}})
    imp_wide = by_design.pivot_table(index=["design", "feature"], columns="variant", values="mean", sort=False)[list(LABEL)].reset_index()
    sd_wide = by_design.pivot_table(index=["design", "feature"], columns="variant", values="sd_between_seeds", sort=False)[list(LABEL)].reset_index()
    text = [
        head, "",
        "## Sources", "", md_table(src), "",
        "## B1 Residualization (same rows; grouped by whether the official dependence test passes)", "",
        md_table(gate_tab, {"max_abs_diff_official_vs_sharedimp": ".3g"}), "",
        "## B3 Importance under a constructed identical condition", "",
        md_table(isum[["language", "dataset", "condition", "forest", "n_seeds", "max_abs_diff_official_vs_rule_on_sharedimp", "max_abs_diff_official_r_vs_original_r"]],
                 {"max_abs_diff_official_vs_rule_on_sharedimp": ".3g", "max_abs_diff_official_r_vs_original_r": ".3g"}), "",
        f"## B4 Importance on the official synthetic designs and the null design (n = {cfg['designs']['n']}, mean over {len(cfg['designs']['seeds'])} data sets)", "",
        "Columns: " + "; ".join(f"`{k}` = {v}" for k, v in LABEL.items()) + ".", "",
        md_table(imp_wide, {k: ".3f" for k in LABEL}), "",
        "Between-data-set SD of the same quantities:", "",
        md_table(sd_wide, {k: ".3f" for k in LABEL}), "",
        "## B6 Null design: sign of single evaluations", "",
        md_table(neg[["variant", "n_values", "mean", "min", "max", "share_negative", "share_exactly_zero"]], {"share_negative": ".2f", "share_exactly_zero": ".2f"}), "",
        "## B5b All-rows vs fold-internal residualization under identical 5-fold CV (OLS, MSE; mean over data sets)", "",
        md_table(lsum[["n", "feature", "population", "fold_internal", "all_rows", "all_rows_official_gate", "all_rows_minus_fold_internal", "sd_fold_internal", "n_seeds"]]), "",
        "## B7 Design differences (evidence in brackets)", "",
        md_table(api_md), "",
    ]
    (tables / "03_official_umfi.md").write_text("\n".join(text))
    counts = table["status"].value_counts().to_dict()
    print(f"[official_summary] {counts}")
    return 1 if counts.get("FAIL", 0) else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
