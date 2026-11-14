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

**Status (2026-11-14): Phases 1 to 3 of 4 are complete** — environment,
runners, smoke tests and a positive control (Phase 1); a study of the
random-forest settings of the two languages, the comparison with the official
UMFI-LR code, three public data sets in R and Python (Phase 2); two
follow-up studies (duplicated rows of the Maternal Health Risk data, forest
importance under a null design) and the runtime benchmark (Phase 3), with
figures and tables. The manuscript (Phase 4) has not been started. Current
state, results and open issues: `docs/STATUS.md`.

## Layout

```
config/      pins.env (package commits, image digests, official UMFI commits), NN_*.json (run conditions)
data/        synthetic/ (generated, committed), real/ (prepared public data), derived/ (variants of real data), null_forest/, runtime/ (generated; CSVs of runtime/ git-ignored); manifest.json in each
R/           R helpers, job runner, experiment B (R side), figures
python/      sharedimp_exp/: Python helpers, job runner, checks, data generators, experiment B, summaries
workflow/    one Snakefile per stage (NN_*.smk), common.smk
scripts/     thin wrappers around the workflows
docker/      Dockerfiles of the two Phase 2 images (built by .github/workflows/docker.yml)
external/    official UMFI sources, fetched at pinned commits at run time (git-ignored)
results/     raw/ (per-run output), summary/ (derived CSV), tables/ (derived Markdown), figures/
docs/        experiment_plan.md, STATUS.md, random_forest_comparison.md, package_change_proposal.md, maternal_duplicates.md, null_forest_investigation.md, runtime_benchmark.md
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
bash scripts/01_environment.sh      # A: environment record + smoke test                     (~1 min)
bash scripts/02_validation.sh       # classification smoke tests + positive control          (~2 min)
bash scripts/02b_rf_settings.sh     # random-forest settings, ranger vs scikit-learn         (~30 min)
bash scripts/03_official_umfi.sh    # B: official UMFI-LR code vs sharedimp (needs git)      (~40 min)
bash scripts/04_real_data.sh        # C: three public data sets (downloads them)             (~5 min)
bash scripts/04b_maternal.sh        # duplicated rows of Maternal Health Risk (needs 04)     (~2 min)
bash scripts/04c_null_forest.sh     # forest importance under a null design                  (~40 min)
bash scripts/05_runtime.sh          # D: runtime benchmark, pilot + main, always 1 core      (~2 h)
bash scripts/06_figures.sh          # figures from the summaries of 01-05                    (~1 min)
```

The durations in the comments were observed with 16 cores
(`SHAREDIMP_EXP_CORES=16`; 02b and 03 took 10 and 8 minutes then).
`05_runtime.sh` runs its processes one after the other on one core whatever
the setting, and should be run while the machine is otherwise idle.

Each script runs `snakemake -s workflow/<name>.smk --use-singularity`
(4 cores unless `SHAREDIMP_EXP_CORES` is set) and passes extra arguments on:
`-n` for a dry run, `--forceall` to recompute everything. Run them one after
the other. The durations are wall-clock times on the machine described in
`results/tables/01_environment.md` and are not a benchmark.

The first run pulls the images and converts them
(`.snakemake/singularity/`, a few minutes). Singularity unpacks an image for
every job; the wrappers set `SINGULARITY_TMPDIR` to a directory in `/dev/shm`
unless it is already set (0.4–1.3 GB per running job). Processes run
single-threaded unless `--config threads=N` is given. A workflow fails if a
process is not inside its pinned image, if a job fails in either language, or
if a check with a pre-set criterion fails. Logs are in `logs/`, Snakemake
benchmarks in `benchmarks/` (both git-ignored); `bash workflow/dag.sh` and
`bash workflow/report.sh` draw the rule graphs and write the Snakemake HTML
reports.

| workflow (`workflow/`) | experiment | status | output |
|---|---|---|---|
| `01_environment.smk` | A: host, versions, commits, images (digest, revision label), threads; smoke test n = 20, p = 3 | done | `results/{raw,summary}/01_environment/`, `results/tables/01_environment*.md` |
| `02_validation.smk` | binary / multiclass smoke tests; linear-Gaussian positive control | done | `results/{raw,summary}/02_validation/`, `results/tables/02_validation_checks.md` |
| `02b_rf_settings.smk` | meaning and effect of the node-size settings of ranger and scikit-learn | done | `results/{raw,summary}/02b_rf_settings/`, `results/tables/02b_rf_settings.md`, `docs/random_forest_comparison.md` |
| `03_official_umfi.smk` | B: official UMFI-LR implementations (R package, original R script, Python) | done | `results/{raw,summary}/03_official_umfi/`, `results/tables/03_official_umfi*.md` |
| `04_real_data.smk` | C: three public data sets in R and Python | done | `data/real/`, `results/{raw,summary}/04_real_data/`, `results/tables/04_real_data*.md` |
| `04b_maternal.smk` | duplicated rows of Maternal Health Risk: random folds, group-aware folds, identical records removed | done | `data/derived/`, `results/{raw,summary}/04b_maternal/`, `results/tables/04b_maternal*.md`, `docs/maternal_duplicates.md` |
| `04c_null_forest.smk` | forest importance when the response is independent of the features, one setting changed at a time | done | `data/null_forest/`, `results/{raw,summary}/04c_null_forest/`, `results/tables/04c_null_forest.md`, `docs/null_forest_investigation.md` |
| `05_runtime.smk` | D: runtime in n, p, folds, learner, R and Python (pilot, budget of 2 h) | done; 31 of 90 cells skipped by the budget rule | `data/runtime/`, `results/{raw,summary}/05_runtime/`, `results/tables/05_runtime*.md`, `docs/runtime_benchmark.md` |
| `06_figures.smk` | E: figures of experiments B, C, D and the follow-up studies | done | `results/figures/` |

### Container images

| image | contents | used by |
|---|---|---|
| `ghcr.io/dsc-chiba-u/sharedimp-r` (tag `cf2e1cc`, by digest) | R 4.5.3, `sharedimp` (R) at the pinned commit | 01, 02, 02b, 04, 04b, 04c, 05 |
| `ghcr.io/dsc-chiba-u/sharedimp-py` (tag `bacc5d8`, by digest) | Python 3.13, `sharedimp` (Python) at the pinned commit | 01, 02, 02b, 03, 04, 04b, 04c, 05 |
| `ghcr.io/dsc-chiba-u/sharedimp-experiments-r` (by digest) | the R image plus the dependencies of the official UMFI R package and `patchwork` | 03, 06 |
| `ghcr.io/dsc-chiba-u/umfi-official-py` (by digest) | Python 3.9 with the dependencies of the official Python UMFI code at its own versions | 03 |

The last two are built from `docker/` by `.github/workflows/docker.yml`. No
official UMFI code is contained in any image or in this repository: workflow
03 fetches it at pinned commits into `external/` and runs it unmodified.

### Data

`data/synthetic/` is generated by `python -m sharedimp_exp.make_synthetic`.
`data/real/` holds prepared versions of three public data sets (UCI Concrete
Compressive Strength, Breast Cancer Wisconsin (Diagnostic), Maternal Health
Risk; all CC BY 4.0); sources, citations and the changes made are in
`data/real/README.md` and `data/real/manifest.json`. `data/derived/` holds
two variants of the Maternal Health Risk file (group-aware folds; identical
records removed) written by workflow 04b; the original file is not changed.
`data/null_forest/` and `data/runtime/` are generated by workflows 04c and
05 (the runtime CSV files are not committed; their checksums are).

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
forest: the difference is reported and never checked). Workflows 02b and 03
have their own scripts and configuration files; their criteria are written in
`config/02b_rf_settings.json` and `config/03_official_umfi.json`.

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
