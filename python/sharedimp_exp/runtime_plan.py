"""Plans of the runtime benchmark (experiment D).

    python -m sharedimp_exp.runtime_plan pilot config/05_runtime.json results/raw/05_runtime/pilot_plan.csv
    python -m sharedimp_exp.runtime_plan main  config/05_runtime.json results/raw/05_runtime/pilot results/summary/05_runtime

"pilot": the pilot cells of the config file for every language and learner.
"main": fits, per language and learner, log(seconds) = a + b log(n) + c log(p)
+ d log(v) to the pilot runs, predicts every candidate cell and applies the
budget rule of the config file. Writes plan.csv, pilot.csv, pilot_model.csv
and budget.json into the summary directory. The fitted exponents serve the
planning only; they are not complexity estimates.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from .common import read_json, write_csv, write_json
from .runtime_data import candidate_cells, cell_id, data_id


def processes(cfg: dict) -> list[tuple[str, str]]:
    return [(lang, learner) for learner, d in cfg["learners"].items() for lang in ("r", "python") if lang in d]


def rows_for(cfg: dict, cells: list[dict]) -> pd.DataFrame:
    return pd.DataFrame([
        {"language": lang, "learner": learner, "cell": cell_id(c), "n": c["n"], "p": c["p"], "v": c["v"], "sweeps": "+".join(c.get("sweeps", [])),
         "data": data_id(c), "fold_column": f"fold_v{c['v']}"}
        for lang, learner in processes(cfg) for c in cells
    ])


def main(argv: list[str]) -> int:
    mode, cfg = argv[1], read_json(Path(argv[2]))
    if mode == "pilot":
        plan = rows_for(cfg, cfg["pilot"]["cells"])
        plan["predicted_seconds"] = np.arange(len(plan), dtype=float) % len(cfg["pilot"]["cells"])  # keeps the order of the config file
        plan["status"], plan["cap_seconds"], plan["process_planned_seconds"] = "run", np.nan, np.nan
        write_csv(plan, Path(argv[3]))
        return 0

    pilot_dir, out = Path(argv[3]), Path(argv[4])
    runs = pd.concat([pd.read_csv(pilot_dir / f"{lang}_{learner}.runs.csv") for lang, learner in processes(cfg)], ignore_index=True)
    pilot_cells = pd.concat([pd.read_csv(pilot_dir / f"{lang}_{learner}.cells.csv") for lang, learner in processes(cfg)], ignore_index=True)
    if not (pilot_cells["status"] == "measured").all():
        raise SystemExit("pilot incomplete: " + pilot_cells[pilot_cells["status"] != "measured"].to_string())
    timed = runs[runs["kind"] == "timed"]
    write_csv(timed, out / "pilot.csv")

    plan = rows_for(cfg, candidate_cells(cfg))
    models = []
    for (lang, learner), d in timed.groupby(["language", "learner"], sort=False):
        A = np.column_stack([np.ones(len(d)), np.log(d["n"]), np.log(d["p"]), np.log(d["v"])])
        coef, *_ = np.linalg.lstsq(A, np.log(d["seconds"].clip(lower=1e-3)), rcond=None)
        resid = np.log(d["seconds"].clip(lower=1e-3)) - A @ coef
        models.append({"language": lang, "learner": learner, "pilot_cells": len(d), "intercept": coef[0], "exponent_n": coef[1], "exponent_p": coef[2],
                       "exponent_v": coef[3], "largest_abs_log_residual": float(np.abs(resid).max())})
        m = (plan["language"] == lang) & (plan["learner"] == learner)
        plan.loc[m, "predicted_seconds"] = np.exp(coef[0] + coef[1] * np.log(plan.loc[m, "n"]) + coef[2] * np.log(plan.loc[m, "p"]) + coef[3] * np.log(plan.loc[m, "v"]))
    write_csv(pd.DataFrame(models), out / "pilot_model.csv")

    b, proto = cfg["budget"], cfg["protocol"]
    runs_per_cell = proto["warmup_runs"] + proto["timed_runs"]
    plan["cell_cost_seconds"] = runs_per_cell * plan["predicted_seconds"]
    overhead = b["process_overhead_seconds"] * len(processes(cfg))
    limit = b["planned_fraction"] * b["total_seconds"]
    table, chosen = [], None
    for cap in sorted(b["per_cell_cap_candidates_seconds"]):
        total = float(plan.loc[plan["cell_cost_seconds"] <= cap, "cell_cost_seconds"].sum()) + overhead
        table.append({"cap_seconds": cap, "planned_total_seconds": total, "cells_run": int((plan["cell_cost_seconds"] <= cap).sum()), "within_limit": total <= limit})
        if total <= limit:
            chosen = cap
    if chosen is None:
        raise SystemExit(f"no cap candidate keeps the planned total below {limit:.0f} s: {table}")
    plan["cap_seconds"] = chosen
    plan["status"] = np.where(plan["cell_cost_seconds"] <= chosen, "run", "skipped (budget)")
    planned = plan[plan["status"] == "run"].groupby(["language", "learner"])["cell_cost_seconds"].sum()
    plan["process_planned_seconds"] = [planned.get((r.language, r.learner), 0.0) + b["process_overhead_seconds"] for r in plan.itertuples()]
    write_csv(plan, out / "plan.csv")
    write_json({"rule": b["rule"], "abort_rule": b["abort_rule"], "total_seconds": b["total_seconds"], "planned_limit_seconds": limit,
                "runs_per_cell": runs_per_cell, "process_overhead_seconds": overhead, "candidates": table, "chosen_cap_seconds": chosen,
                "planned_total_seconds": float(plan.loc[plan["status"] == "run", "cell_cost_seconds"].sum()) + overhead,
                "cells": {"candidates": int(len(plan)), "run": int((plan["status"] == "run").sum()), "skipped": int((plan["status"] != "run").sum())}},
               out / "budget.json")
    print(f"[runtime_plan] cap {chosen} s; {int((plan['status'] == 'run').sum())} of {len(plan)} cells planned")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
