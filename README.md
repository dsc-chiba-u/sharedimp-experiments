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
`workflow/NN_*.smk`.

## Reproducing

Requirements: Linux, Snakemake >= 8.10 and Singularity (both from
`environment.yml`), network access to pull the container images. R, Python and
the two `sharedimp` packages are **not** installed on the host: every
computation runs inside a container image referenced by digest in
`config/pins.env`.

```sh
conda env create -f environment.yml     # Snakemake 8.10.0 + Singularity 3.8.6
conda activate snakemake
snakemake -s workflow/01_environment.smk --use-singularity -c4   # experiment A: environment record + smoke test
snakemake -s workflow/02_validation.smk  --use-singularity -c4   # classification smoke tests + positive control
```

`bash scripts/01_environment.sh` and `bash scripts/02_validation.sh` are thin
wrappers around these two commands (cores from `SHAREDIMP_EXP_CORES`, extra
arguments passed to Snakemake: `-n` for a dry run, `--forceall` to recompute
everything). The first run pulls the images and converts them
(`.snakemake/singularity/`, a few minutes). Processes run single-threaded
unless `--config threads=N` is given. A workflow fails if a process is not
inside its pinned image, if a job fails in either language, or if a check
fails. Logs are in `logs/`, Snakemake benchmarks in `benchmarks/` (both
git-ignored); `bash workflow/dag.sh` and `bash workflow/report.sh` draw the
rule graphs and write the Snakemake HTML reports.

| workflow (`workflow/`) | experiment | status | output |
|---|---|---|---|
| `01_environment.smk` | A: host, versions, commits, images (digest, revision label), threads; smoke test n = 20, p = 3 | done | `results/{raw,summary}/01_environment/`, `results/tables/01_environment*.md` |
| `02_validation.smk` | binary / multiclass smoke tests; linear-Gaussian positive control | done | `results/{raw,summary}/02_validation/`, `results/tables/02_validation_checks.md` |
| `03_official_umfi.smk` | B: official UMFI-LR implementations | Phase 2, placeholder (fails on purpose) | — |
| `04_real_data.smk` | C: real data in R and Python | Phase 2, placeholder | — |
| `05_runtime.smk` | D: runtime in n, p, folds, learner | Phase 3, placeholder | — |
| `06_figures.smk` | E: figures and tables | Phases 2–3, placeholder | — |

### Container images

| image | contents | used by |
|---|---|---|
| `ghcr.io/dsc-chiba-u/sharedimp-r` (tag `cf2e1cc`, by digest) | R 4.5.3, `sharedimp` (R) at the pinned commit | 01, 02 |
| `ghcr.io/dsc-chiba-u/sharedimp-py` (tag `bacc5d8`, by digest) | Python 3.13, `sharedimp` (Python) at the pinned commit | 01, 02 |
| `koki/sharedimp-experiments-r` | the R image plus dependencies of the official UMFI R package and plotting | 03–06 (not built yet) |
| `koki/umfi-official-py` | dependencies of the official Python UMFI code at its own versions | 03 (not built yet) |

Dockerfiles and build commands for the last two are in `docker/`. No official
UMFI code is contained in any image.

### How a run is defined

A job file lists jobs `{id, dataset, learner, metric, seed, parity}`. Both
runners (`R/run_jobs.R`, `python -m sharedimp_exp.run_jobs`) read the same
job file and the same data file (sha256 checked against
`data/*/manifest.json`), build the splits from the `fold` column of the data
file, call `shared_importance()` with `on_error = "error"`, and write

```
results/raw/<NN_name>/<language>/<job>.importance.csv   summary table (common schema)
results/raw/<NN_name>/<language>/<job>.folds.csv        per-split table (+ fold label)
results/raw/<NN_name>/<language>/<job>.meta.json        job, container image, versions, commits, threads, time, warnings, status
```

`python -m sharedimp_exp.check_jobs` then compares the two languages and
evaluates the checks whose criteria are fixed in `docs/experiment_plan.md`.
`parity` names the tolerance class: `exact` (OLS, 1e-8), `logistic` (1e-6),
`multinomial` (1e-3) or `none` (language-specific learner such as a random
forest: the difference is reported and never checked).

### Versions

The versions that produced the committed results are in
`results/tables/01_environment.md`. Changing `config/pins.env` requires
re-running everything. Workflow 01 checks through the registry API that each
pinned digest is the image tagged with the pinned commit and carries that
commit as its `org.opencontainers.image.revision` label, and each process
checks from inside that it runs in the pinned image.

## License

MIT (see `LICENSE`). Third-party code is not vendored: the official UMFI
implementations will be fetched at pinned commits into the git-ignored
`external/` directory.
