# CLAUDE.md — sharedimp-experiments

## What this repository is

Experiments, benchmarks and the manuscript for the SoftwareX paper on
`sharedimp`: the R package (`../sharedimp-r`, tidymodels) and the Python
package (`../sharedimp-py`, scikit-learn), both implementing UMFI-LR
(Janssen, Guan & Robeva, AISTATS 2023) according to one specification
(`../sharedimp-r/docs/specification.md`).

Read first: `docs/STATUS.md` (state, open issues), `docs/experiment_plan.md`
(what each experiment is for and its pre-set criteria), then the two package
`CLAUDE.md` files and the common specification.

## Positioning (keep consistent in code comments, docs and the paper)

- UMFI-LR is an existing method. We report software, not a new importance
  measure. The contributions to *verify* are: fold-internal residualization,
  paired cross-validated evaluation, tidymodels / scikit-learn integration
  with free choice of learner and metric, R–Python agreement under one
  specification, reproducible environment.
- Having implemented something is not evidence that it is better. Claims
  against the official UMFI code need an executed comparison.
- A numerical difference from the official implementation is not a bug when
  the evaluation procedures differ. Claim equality only under a constructed
  identical condition.
- Properties that follow from the definition of UMFI-LR (correlated features
  sharing credit, etc.) are not findings of sharedimp.
- Importances are out-of-sample predictive gains. Never describe them as
  causal or conditional effects. No confidence intervals or p-values;
  `importance_std` is a descriptive between-split SD.
- Measured runtime and complexity arguments are kept apart; R-vs-Python
  timing differences include learner and BLAS differences.

## Hard rules

- **The sibling repositories are read-only.** Never edit `../sharedimp-r`,
  `../sharedimp-py` or the reference repositories (`../fbrglm-experiments`,
  `../FbSQL-experiments`). If a package needs a change, write it down in
  `docs/STATUS.md` and tell the user.
- **No fabricated or hand-edited results.** Everything under `results/` is
  written by a script. A run that failed or was skipped is recorded as such.
  If something cannot be run (e.g. Docker, an official implementation), record
  the reason; do not substitute numbers from elsewhere.
- **No official UMFI code in this repository** (two of the three upstream
  repositories have no license). Clone at pinned commits into `external/`
  (git-ignored) and record commit and checksums.
- **The manuscript lives only in `paper/`.** No number, DOI, release or
  conclusion goes into it before it exists. Manuscript text is English;
  progress reports to the user are in Japanese.
- **Do not start a later phase, or a large benchmark, without being asked.**
  Run a pilot first and set a time budget.
- Criteria for a check are written in `docs/experiment_plan.md` before the
  run. Do not loosen a tolerance to make a check pass; understand the
  difference first.

## Environment and execution

Snakemake + Singularity, in the style of `../ImageRegistration-experiments`:
one Snakefile per stage in `workflow/`, a `container:` directive on every
computing rule, `benchmark:` and `log:` per rule.

```sh
conda activate snakemake      # Snakemake 8.10.0 + Singularity 3.8.6 (environment.yml)
snakemake -s workflow/01_environment.smk --use-singularity -c4
snakemake -s workflow/02_validation.smk  --use-singularity -c4
snakemake -s workflow/<stage>.smk -n                      # dry run
snakemake -s workflow/02_validation.smk --use-singularity -c4 results/raw/02_validation/r/pc_linear_mse.meta.json
```

`bash scripts/NN_*.sh [snakemake args]` wraps the same commands and finds the
`snakemake` conda environment without activation. Use `--forceall` to
recompute. Logs: `logs/<stage>/<rule>.log`.

- R, Python and sharedimp are **not** on the host. They come from the images
  pinned by digest in `config/pins.env` (`ghcr.io/dsc-chiba-u/sharedimp-r`,
  `…/sharedimp-py`, built by the package CI and tagged with the 7-character
  commit). `workflow/common.smk` builds the `docker://image@sha256:…`
  references and exports thread, pin and locale variables to every rule.
- To change a package version: set commit **and** digest in `config/pins.env`,
  then re-run everything. Workflow 01 fails if a process is not in the pinned
  image or if the registry says the digest is not the pinned commit.
- Only `host_info` runs on the host (standard library only, with the Python
  that runs Snakemake).
- The Docker daemon is not usable by this account (root-owned snap socket), so
  images cannot be *built* here. New images are defined in `docker/` and built
  and pushed by the user; then their digest goes into `config/pins.env`.
  To try something in an image by hand:
  `singularity exec docker://<image>@<digest> <command>`.
- Never state that something ran in a container unless the result's
  `container.image` field says so.

## Layout and conventions

- `config/pins.env`, `config/NN_*.json` — run conditions (machine readable).
- `data/synthetic/` — generated by `python -m sharedimp_exp.make_synthetic`,
  committed, described by `manifest.json` (sha256, generator, references).
  Values are rounded to 6 decimals so both languages parse identical doubles.
  `data/real/` — Phase 2, same manifest format, with source and license.
- The `fold` column of a data file is the only source of splits: one split
  per label in increasing order, in both languages. Never let each language
  draw its own folds when results are to be compared.
- `R/common.R`, `R/run_jobs.R`, `R/env_info.R`; `python/sharedimp_exp/`
  (`common`, `learners`, `run_jobs`, `check_jobs`, `make_synthetic`,
  `env_info`, `host_info`, `docker_info`, `env_summary`). Scripts take
  positional arguments in the order of the Snakemake rule.
- `workflow/NN_*.smk` writes `results/raw/NN_*/` and `results/summary/NN_*/`;
  Markdown tables go to `results/tables/`, figures to `results/figures/`.
  One rule per (language, job), so jobs run in parallel and a failed job
  leaves no output. `workflow/common.smk` is included by all of them.
- `docker/<name>/Dockerfile` — images this repository needs beyond the
  package images; `docker/README.md` lists every image and its status.
- Raw CSVs carry 17 significant digits. Summaries are derived from raw files
  only.
- Parity classes (`exact` 1e-8, `logistic` 1e-6, `multinomial` 1e-3, `none`)
  are declared per job. Random forests and other language-specific learners
  are `none`: report the difference, never assert on it.
- Learner mapping lives in `python/sharedimp_exp/learners.py` (Python) and in
  the R package's built-in names (R). Parity on rank-deficient designs needs
  an aliasing OLS in Python (common specification §8.1); avoid exact
  duplicates in parity data unless that learner is used.
- Stage numbers: `01` environment (experiment A), `02`
  validation / positive control, `03` official UMFI (B), `04` real data (C),
  `05` runtime (D), `06` figures (E). Placeholder workflows raise an error when parsed.

## Before committing

Commit code first, then run `bash scripts/01_environment.sh --forceall` and
`bash scripts/02_validation.sh --forceall` (about 3 minutes together once the
images are cached) and commit the regenerated results, so that the results
record a clean code commit. Update `docs/STATUS.md`. Small, focused commits
with imperative messages. Never report a workflow as passing without having
run it.
