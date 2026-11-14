"""Summary of the runtime benchmark (experiment D).

    python -m sharedimp_exp.runtime_summary config/05_runtime.json results/raw/05_runtime results/summary/05_runtime

Reads the raw files of the main benchmark (and the pilot for the fit count)
and the plan; writes cells.csv (median, quartiles, minimum per cell),
comparisons.csv (R next to Python per comparison and cell), environment.csv,
checks.csv and results/tables/05_runtime{,_checks}.md. Exit status 1 if a
check with a criterion fails. Nothing here estimates an order of complexity.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from .common import ROOT, read_json, write_csv
from .rf_settings_summary import md_table
from .runtime_plan import processes


def main(argv: list[str]) -> int:
    cfg, raw, out = read_json(Path(argv[1])), Path(argv[2]), Path(argv[3])
    procs = processes(cfg)
    plan, budget = pd.read_csv(out / "plan.csv"), read_json(out / "budget.json")

    def read(path: Path) -> pd.DataFrame:
        try:  # a process whose cells were all skipped writes empty tables
            return pd.read_csv(path)
        except pd.errors.EmptyDataError:
            return pd.DataFrame()

    rd = lambda stage, name: pd.concat([read(raw / stage / f"{lang}_{learner}.{name}.csv") for lang, learner in procs], ignore_index=True)
    runs, status, imp = rd("main", "runs"), rd("main", "cells"), rd("main", "importance")
    meta = {(stage, lang, learner): read_json(raw / stage / f"{lang}_{learner}.meta.json") for stage in ("pilot", "main") for lang, learner in procs}
    checks = []

    def check(check_id, description, criterion, observed, passed):
        checks.append({"check": check_id, "description": description, "criterion": criterion, "observed": observed,
                       "status": "reported" if passed is None else ("pass" if passed else "FAIL")})

    key = ["language", "learner", "cell"]
    timed = runs[runs["kind"] == "timed"]
    q = lambda p: (lambda s: float(np.percentile(s, p)))
    stats = timed.groupby(key, sort=False)["seconds"].agg(median="median", q1=q(25), q3=q(75), minimum="min", maximum="max", mean="mean", timed_runs_found="count").reset_index()
    stats["iqr"] = stats["q3"] - stats["q1"]
    warm = runs[runs["kind"] == "warmup"].groupby(key, sort=False)["seconds"].first().rename("warmup_seconds").reset_index()
    load = runs.groupby(key, sort=False)["loadavg_1min_before"].max().rename("largest_loadavg_1min").reset_index()
    cells = plan[key + ["n", "p", "v", "sweeps", "predicted_seconds"]].merge(status[key + ["status", "reason", "timed_runs", "data", "fold_column", "data_sha256"]], on=key, how="left")
    cells = cells.merge(stats, on=key, how="left").merge(warm, on=key, how="left").merge(load, on=key, how="left")
    cells["learner_fits"] = 2 * cells["p"] * cells["v"]
    cells["median_seconds_per_fit"] = cells["median"] / cells["learner_fits"]
    cells["status"] = cells["status"].fillna("missing")
    write_csv(cells, out / "cells.csv")

    # ---- checks (criteria: config file)
    need = cfg["protocol"]["timed_runs"]
    measured = cells["status"] == "measured"
    accounted = (measured & (cells["timed_runs_found"] == need)) | cells["status"].str.startswith("skipped")
    check("accounted", "every candidate cell is measured with the planned number of timed runs or recorded as skipped", f"all {len(cells)} cells",
          f"measured {int(measured.sum())}, skipped {int(cells['status'].str.startswith('skipped').sum())}, other {int((~accounted).sum())}", bool(accounted.all()))
    sha = cells[measured].groupby("cell")[["data_sha256", "fold_column"]].nunique()
    check("same_data", "one data file and one fold column per cell, whatever the language and learner", "1 sha256 and 1 fold column per cell",
          f"{len(sha)} cells, at most {int(sha.max().max()) if len(sha) else 0}", bool((sha == 1).all().all()))
    lin = imp[imp["learner"] == "linear"].pivot_table(index=["cell", "feature"], columns="language", values=["importance", "score_full", "score_reduced"], sort=False)
    both = lin.dropna()
    worst = float(max((both[c]["r"] - both[c]["python"]).abs().max() for c in ("importance", "score_full", "score_reduced"))) if len(both) else float("nan")
    n_both = both.index.get_level_values("cell").nunique()
    check("same_work_linear", "linear learner: largest |R - Python| of importance and scores over the cells measured in both languages", "<= 1e-8",
          f"{worst:.3g} ({n_both} cells)", bool(n_both > 0 and worst <= 1e-8))
    for lang in ("r", "python"):
        fc = meta[("pilot", lang, "linear")]["fit_count"]
        check(f"fit_count/{lang}", f"learner fits in one call (n = {fc['n']}, p = {fc['p']}, v = {fc['v']})", f"2 x p x v = {fc['expected']}", fc["fits"], fc["fits"] == fc["expected"])
    threads = {m["threads"] for m in meta.values()} | {str(v) for m in meta.values() for v in m["thread_env"].values() if v is not None}
    check("threads", "threads recorded by every process (setting and environment variables)", "1", ", ".join(sorted(map(str, threads))), threads <= {1, "1"})
    total = sum(m["process_seconds"] for (stage, _, _), m in meta.items() if stage == "main")
    check("budget", "wall time of the processes of the main benchmark, in total", f"<= {cfg['budget']['total_seconds']} s", f"{total:.0f} s", total <= cfg["budget"]["total_seconds"])
    pinned = all(m["in_pinned_image"] for m in meta.values())
    check("pinned_image", "every process ran in the pinned image", "all", f"{sum(m['in_pinned_image'] for m in meta.values())} of {len(meta)}", pinned)
    dirty = sorted({str(m["experiments_code_dirty"]) for m in meta.values()})
    check("code_state", "uncommitted code changes when the processes ran", "reported only", ", ".join(dirty), None)
    check("load", "largest 1-minute load average seen before a timed run", "reported only", f"{runs['loadavg_1min_before'].max():.2f}", None)
    failed = cells[cells["status"].isin(["failed", "missing"])]
    check("failed", "cells that failed", "0", len(failed), len(failed) == 0)

    # ---- R next to Python
    comp_rows = []
    for cid, c in cfg["comparisons"].items():
        a = cells[(cells["language"] == "r") & (cells["learner"] == c["r"])].set_index("cell")
        b = cells[(cells["language"] == "python") & (cells["learner"] == c["python"])].set_index("cell")
        for cell in a.index:
            ra, rb = a.loc[cell], b.loc[cell]
            comp_rows.append({"comparison": cid, "cell": cell, "n": ra["n"], "p": ra["p"], "v": ra["v"], "sweeps": ra["sweeps"], "learner_fits": ra["learner_fits"],
                              "r_learner": c["r"], "python_learner": c["python"], "r_status": ra["status"], "python_status": rb["status"],
                              "r_median": ra["median"], "r_q1": ra["q1"], "r_q3": ra["q3"], "r_min": ra["minimum"],
                              "python_median": rb["median"], "python_q1": rb["q1"], "python_q3": rb["q3"], "python_min": rb["minimum"],
                              "python_over_r_median": rb["median"] / ra["median"]})
    comp = pd.DataFrame(comp_rows)
    write_csv(comp, out / "comparisons.csv")

    env = pd.DataFrame([{
        "stage": stage, "language": lang, "learner": learner, "learner_description": m["learner_description"], "process_seconds": m["process_seconds"],
        "runtime": m.get("r_version") or "Python " + m["python_version"].split()[0],
        "packages": "; ".join(f"{k} {v}" for k, v in m["packages"].items() if v),
        "blas": m.get("la_library") or "; ".join(sorted({f"{t.get('internal_api')} {t.get('version')} ({t.get('num_threads')} thread)" for t in m.get("threadpools", [])})),
        "cpu": m["cpu"], "logical_cpus": m["logical_cpus"], "threads": m["threads"], "timer": m["timer"],
        "image": (m["container"] or {}).get("image"), "sharedimp_commit": m["sharedimp_commit"], "experiments_commit": m["experiments_commit"],
        "experiments_code_dirty": m["experiments_code_dirty"], "started_utc": m["started_utc"],
    } for (stage, lang, learner), m in meta.items()])
    write_csv(env, out / "environment.csv")

    table = pd.DataFrame(checks)
    write_csv(table, out / "checks.csv")
    tables = ROOT / "results" / "tables"
    md = ["| check | description | criterion | observed | status |", "|---|---|---|---|---|"]
    md += [f"| `{r.check}` | {r.description} | {r.criterion} | {r.observed} | {r.status} |" for r in table.itertuples()]
    (tables / "05_runtime_checks.md").write_text("<!-- generated by python/sharedimp_exp/runtime_summary.py; do not edit -->\n" + "\n".join(md) + "\n")

    sec = {c: ".3g" for c in ("r_median", "r_q1", "r_q3", "r_min", "python_median", "python_q1", "python_q3", "python_min", "python_over_r_median",
                              "median", "q1", "q3", "minimum", "predicted_seconds", "warmup_seconds", "process_seconds", "planned_total_seconds")}
    proto = cfg["protocol"]
    main_env = env[env["stage"] == "main"]
    text = ["<!-- generated by python/sharedimp_exp/runtime_summary.py; do not edit -->", "",
            "## Runtime of `shared_importance()` (experiment D)", "",
            f"Timed: {proto['timed']}. {proto['warmup_runs']} warm-up run (discarded) and {proto['timed_runs']} timed runs per cell, {proto['threads']} thread; "
            f"{proto['order']}. Data: {cfg['data']['model']}; metric {cfg['data']['metric']}; the same file and fold column in both languages. "
            f"Sweeps: {cfg['sweep_rule']}. One call fits the learner 2 x p x v times (`learner_fits`).", "",
            "Seconds are wall-clock seconds; `q1`, `q3` are the quartiles of the timed runs (IQR = q3 - q1). Differences between R and Python include the learner "
            "implementations, the linear-algebra libraries and the overhead of each framework; they are not differences \"between the languages\".", "",
            "## Processes", "",
            md_table(main_env[["language", "learner", "learner_description", "runtime", "packages", "blas", "threads", "timer", "process_seconds"]], sec), "",
            f"CPU: {main_env['cpu'].iloc[0]} ({main_env['logical_cpus'].iloc[0]} logical CPUs). Images: " + "; ".join(sorted(set(main_env["image"].astype(str)))) + ". "
            f"sharedimp commits: R {main_env.loc[main_env['language'] == 'r', 'sharedimp_commit'].iloc[0]}, Python {main_env.loc[main_env['language'] == 'python', 'sharedimp_commit'].iloc[0]}; "
            f"this repository: {main_env['experiments_commit'].iloc[0]} (uncommitted code changes: {', '.join(dirty)}).", "",
            "## Budget", "",
            f"{budget['rule']} {budget['abort_rule']}", "",
            md_table(pd.DataFrame(budget["candidates"]), sec), "",
            f"Chosen cap: {budget['chosen_cap_seconds']} s per cell ({budget['runs_per_cell']} runs); planned total {budget['planned_total_seconds']:.0f} s of at most "
            f"{budget['planned_limit_seconds']:.0f} s planned ({budget['total_seconds']} s allowed); measured total of the main processes {total:.0f} s.", "",
            "Cells by status:", "",
            md_table(cells.groupby(["language", "learner", "status"], sort=False).size().rename("cells").reset_index()), ""]
    for cid, c in cfg["comparisons"].items():
        text += [f"## {c['title']}", "", f"R: {cfg['learners'][c['r']]['r']}. Python: {cfg['learners'][c['python']]['python']}.", ""]
        d = comp[comp["comparison"] == cid]
        for factor in cfg["sweeps"]:
            s = d[d["sweeps"].str.split("+").apply(lambda parts: factor in parts)].sort_values(factor)
            show = s[["n", "p", "v", "learner_fits", "r_median", "r_q1", "r_q3", "r_min", "python_median", "python_q1", "python_q3", "python_min", "python_over_r_median"]].copy()
            for lang in ("r", "python"):
                skipped = s[f"{lang}_status"] != "measured"
                show[f"{lang}_median"] = show[f"{lang}_median"].map(lambda x: format(x, ".3g")).where(~skipped.to_numpy(), s[f"{lang}_status"].to_numpy())
            text += [f"Sweep over {factor}:", "", md_table(show.astype(object).fillna("-"), sec), ""]
    skipped = cells[cells["status"] != "measured"]
    text += ["## Cells not measured", "",
             md_table(skipped[["language", "learner", "cell", "status", "reason", "predicted_seconds"]], sec) if len(skipped) else "None.", "",
             "## Pilot", "", f"{cfg['pilot']['runs']}. {cfg['pilot']['prediction']}.", "",
             md_table(pd.read_csv(out / "pilot.csv").pivot_table(index=["n", "p", "v"], columns=["language", "learner"], values="seconds", sort=False)
                      .pipe(lambda t: t.set_axis([f"{a}/{b}" for a, b in t.columns], axis=1)).reset_index(), {}), ""]
    (tables / "05_runtime.md").write_text("\n".join(text))
    counts = table["status"].value_counts().to_dict()
    print(f"[runtime_summary] {counts}")
    for r in table[table["status"] == "FAIL"].itertuples():
        print(f"  FAIL {r.check}: {r.description} (criterion {r.criterion}; observed {r.observed})")
    return 1 if counts.get("FAIL", 0) else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
