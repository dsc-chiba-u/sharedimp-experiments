"""Run shared_importance() for every job of a job file (Python side).

    python -m sharedimp_exp.run_jobs config/01_smoke_jobs.json results/raw/01_environment/python

For each job three files are written: <id>.importance.csv, <id>.folds.csv and
<id>.meta.json. Any failure makes the process exit with a non-zero status
after the remaining jobs have run; a failed job leaves a meta file with
"status": "failed" and no result tables.
"""

from __future__ import annotations

import os
import sys
import time
import traceback
import warnings
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import sharedimp
from sharedimp import common_scorer, shared_importance

from .common import load_dataset, read_json, splits_from_labels, write_csv, write_json
from .learners import make_learner


def run_job(job: dict, out: Path, provenance: dict) -> bool:
    meta = {"job": job, "language": "python", "status": "failed", **provenance}
    try:
        ds = load_dataset(job["dataset"])
        task = ds["entry"]["task"]
        n_classes = None if task == "regression" else len(np.unique(ds["y"]))
        threads = int(os.environ.get("SHAREDIMP_EXP_THREADS", "1"))
        est, label = make_learner(job["learner"], task, n_classes, threads)
        labels, splits = splits_from_labels(ds["fold"])
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            t0 = time.perf_counter()
            res = shared_importance(
                est,
                ds["X"],
                ds["y"],
                scoring=common_scorer(job["metric"]),
                cv=splits,
                on_error="error",
                random_state=job["seed"],
            )
            elapsed = time.perf_counter() - t0
        folds = res.fold_results.copy()
        folds.insert(2, "fold", [labels[s] for s in folds["split"]])
        write_csv(res.importances, out / f"{job['id']}.importance.csv")
        write_csv(folds, out / f"{job['id']}.folds.csv")
        meta.update(
            status="ok",
            dataset_sha256=ds["sha256"],
            task=task,
            learner_description=label,
            scoring=str(res.scoring),
            n=int(ds["X"].shape[0]),
            p=int(ds["X"].shape[1]),
            n_splits=len(splits),
            elapsed_seconds=elapsed,
            warnings=[f"{w.category.__name__}: {w.message}" for w in caught],
        )
    except Exception as exc:  # recorded, never swallowed: exit status is non-zero
        meta["error"] = f"{type(exc).__name__}: {exc}"
        meta["traceback"] = traceback.format_exc()
        for suffix in ("importance.csv", "folds.csv"):
            (out / f"{job['id']}.{suffix}").unlink(missing_ok=True)
    write_json(meta, out / f"{job['id']}.meta.json")
    print(f"[python] {job['id']}: {meta['status']}" + (f" ({meta.get('error')})" if meta["status"] != "ok" else ""))
    return meta["status"] == "ok"


def main(argv: list[str]) -> int:
    jobs_file, out = Path(argv[1]), Path(argv[2])
    out.mkdir(parents=True, exist_ok=True)
    manifest_path = os.environ.get("SHAREDIMP_INSTALL_MANIFEST", "")
    manifest = read_json(Path(manifest_path)) if manifest_path and Path(manifest_path).exists() else {}
    provenance = {
        "jobs_file": str(jobs_file),
        "sharedimp_version": sharedimp.__version__,
        "sharedimp_commit": manifest.get("sharedimp_py", {}).get("commit"),
        "threads": int(os.environ.get("SHAREDIMP_EXP_THREADS", "1")),
        "run_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    ok = [run_job(job, out, provenance) for job in read_json(jobs_file)["jobs"]]
    return 0 if all(ok) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
