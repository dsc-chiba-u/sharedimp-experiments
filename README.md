# sharedimp-experiments

Reproducible experiments and the manuscript for the SoftwareX paper on
`sharedimp`, a pair of packages that implement the linear-regression variant
of ultra-marginal feature importance (UMFI-LR; Janssen, Guan & Robeva,
AISTATS 2023) with fold-internal residualization and paired cross-validated
evaluation:

- R / tidymodels: <https://github.com/dsc-chiba-u/sharedimp-r>
- Python / scikit-learn: <https://github.com/dsc-chiba-u/sharedimp-py>

UMFI-LR is an existing method. This repository evaluates *software*: it does
not propose or benchmark a new importance measure, and the importances it
reports are out-of-sample predictive gains, not causal or conditional effects.

**Status (2026-11-13): Phase 1 of 4 is complete** — environment, runners,
smoke tests and a positive control. The comparison with the official UMFI
code, the real-data examples, the runtime benchmark and the manuscript are
planned (`docs/experiment_plan.md`) but not run; their scripts are
placeholders that exit with an error. Current state and open issues:
`docs/STATUS.md`.

## Layout

```
config/      pins.env (package commits), NN_*.json (job files = run conditions)
data/        synthetic/ (generated, committed, with manifest.json), real/ (Phase 2)
R/           R helpers and the R job runner
python/      sharedimp_exp/: Python helpers, job runner, checks, data generator
scripts/     numbered entry points (run from anywhere; they cd to the repository root)
results/     raw/ (per-run output), summary/ (derived CSV), tables/ (derived Markdown), figures/
docs/        experiment_plan.md, STATUS.md
paper/       manuscript (skeleton), references.bib
```

Every file under `results/` is written by a script; nothing there is edited by
hand. `results/raw/NN_*` and `results/summary/NN_*` belong to
`scripts/NN_*.sh`.

## Reproducing

Requirements: Linux, conda or mamba, git, network access (conda-forge; GitHub
if the sibling checkouts `../sharedimp-r` and `../sharedimp-py` are absent).

```sh
mamba env create -f environment.yml        # R 4.5 + Python 3.13, one OpenBLAS for both
bash scripts/00_install_sharedimp.sh       # installs the commits pinned in config/pins.env
bash scripts/01_validate_environment.sh    # experiment A: environment record + smoke test (~20 s)
bash scripts/02_validate_implementations.sh  # classification smoke tests + positive control (~2 min)
```

The scripts find the environment at `<conda base>/envs/sharedimp-exp` (or use
the active one, or `SHAREDIMP_EXP_ENV=/path/to/env`); activation is not
needed. They run single-threaded unless `SHAREDIMP_EXP_THREADS` is set. Each
script exits with a non-zero status if a job fails in either language or a
check fails.

| script | experiment | status | output |
|---|---|---|---|
| `00_install_sharedimp.sh` | install pinned package commits (non-editable `git archive` snapshots) | done | install manifest inside the environment |
| `01_validate_environment.sh` | A: versions, commits, OS/CPU/threads, image digests; smoke test n = 20, p = 3 | done | `results/{raw,summary}/01_environment/`, `results/tables/01_environment*.md` |
| `02_validate_implementations.sh` | binary / multiclass smoke tests; linear-Gaussian positive control | done | `results/{raw,summary}/02_validation/`, `results/tables/02_validation_checks.md` |
| `03_compare_official_umfi.sh` | B: official UMFI-LR implementations | Phase 2, placeholder | — |
| `04_real_data.sh` | C: real data in R and Python | Phase 2, placeholder | — |
| `05_runtime_benchmark.sh` | D: runtime in n, p, folds, learner | Phase 3, placeholder | — |
| `06_generate_figures.sh` | E: figures and tables | Phases 2–3, placeholder | — |

### How a run is defined

A job file lists jobs `{id, dataset, learner, metric, seed, parity}`. Both
runners (`R/run_jobs.R`, `python -m sharedimp_exp.run_jobs`) read the same
job file and the same data file (sha256 checked against
`data/*/manifest.json`), build the splits from the `fold` column of the data
file, call `shared_importance()` with `on_error = "error"`, and write

```
results/raw/<NN_name>/<language>/<job>.importance.csv   summary table (common schema)
results/raw/<NN_name>/<language>/<job>.folds.csv        per-split table (+ fold label)
results/raw/<NN_name>/<language>/<job>.meta.json        job, versions, commit, threads, time, warnings, status
```

`python -m sharedimp_exp.check_jobs` then compares the two languages and
evaluates the checks whose criteria are fixed in `docs/experiment_plan.md`.
`parity` names the tolerance class: `exact` (OLS, 1e-8), `logistic` (1e-6),
`multinomial` (1e-3) or `none` (language-specific learner such as a random
forest: the difference is reported and never checked).

### Versions

The versions that produced the committed results are in
`results/tables/01_environment.md`. Changing `config/pins.env` or the
environment requires re-running everything.

Docker: the packages publish images (`ghcr.io/dsc-chiba-u/sharedimp-r`,
`ghcr.io/dsc-chiba-u/sharedimp-py`). Script 01 records their digests and
whether `latest` is the pinned commit. The committed results were **not**
produced inside these images (see `docs/STATUS.md`).

## License

MIT (see `LICENSE`). Third-party code is not vendored: the official UMFI
implementations will be fetched at pinned commits into the git-ignored
`external/` directory.
