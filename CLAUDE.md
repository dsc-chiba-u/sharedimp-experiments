# CLAUDE.md — sharedimp-experiments

## What this repository is

Experiments, benchmarks and the manuscript for the SoftwareX paper on
`sharedimp`: the R package (`../sharedimp-r`, tidymodels) and the Python
package (`../sharedimp-py`, scikit-learn), both implementing UMFI-LR
(Janssen, Guan & Robeva, AISTATS 2023) according to one specification
(`../sharedimp-r/docs/specification.md`).

Read first: `docs/STATUS.md` (state, results, open issues),
`docs/experiment_plan.md` (what each experiment is for and its pre-set
criteria), `docs/random_forest_comparison.md` (why forests are never compared
numerically across languages), `docs/runtime_benchmark.md` (what the timings
do and do not show), `docs/maternal_duplicates.md` and
`docs/null_forest_investigation.md` (two results that must not be quoted
naively), then the two package
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
- **No official UMFI code in this repository or in any image** (two of the
  three upstream repositories have no license). `fetch_official` clones them
  at the commits in `config/pins.env` into `external/` (git-ignored) and
  records commit and checksums; the code is sourced / imported unmodified.
  Do not paste official code into scripts, docs or commit messages.
- **The manuscript lives only in `paper/`.** No number, DOI, release or
  conclusion goes into it before it exists. Numbers are never typed into
  `paper/manuscript.Rmd`: they are computed in its `setup` chunk from
  `results/` with `num()` / `reg()` (`paper/README.md`). Journal
  requirements and their sources: `docs/softwarex_requirements.md`; items
  marked `TO BE COMPLETED BY THE AUTHOR` are not to be guessed. Limits
  checked by workflow 07: 4000 words for the five main sections, six
  figures. Manuscript text is English;
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
snakemake -s workflow/<stage>.smk -n                      # dry run (other stages: 02b_rf_settings, 03_official_umfi, 04_real_data, 04a_multiclass_selection, 04b_maternal, 04c_null_forest, 05_runtime, 06_figures, 07_manuscript)
snakemake -s workflow/02_validation.smk --use-singularity -c4 results/raw/02_validation/r/pc_linear_mse.meta.json
```

`bash scripts/NN_*.sh [snakemake args]` wraps the same commands and finds the
`snakemake` conda environment without activation. Use `--forceall` to
recompute. Logs: `logs/<stage>/<rule>.log`.

- R, Python and sharedimp are **not** on the host. They come from the images
  pinned by digest in `config/pins.env`: `ghcr.io/dsc-chiba-u/sharedimp-r` and
  `…/sharedimp-py` (built by the package CI, tagged with the 7-character
  commit), `…/sharedimp-experiments-r` (the R image + official UMFI R
  dependencies + patchwork; `EXP_R_CONTAINER`) and `…/umfi-official-py`
  (Python 3.9, official UMFI Python dependencies, no sharedimp;
  `UMFI_PY_CONTAINER`). `workflow/common.smk` builds the `docker://image@sha256:…`
  references and exports thread, pin and locale variables to every rule.
- To change a package version: set commit **and** digest in `config/pins.env`,
  then re-run everything. Workflow 01 fails if a process is not in the pinned
  image or if the registry says the digest is not the pinned commit.
- Only `host_info` runs on the host (standard library only, with the Python
  that runs Snakemake).
- The Docker daemon is not usable by this account (root-owned snap socket), so
  images cannot be *built* here. `docker/<name>/Dockerfile` is built and
  pushed to GHCR by `.github/workflows/docker.yml` on a push to `main` that
  changes a Dockerfile; then set digest and `PHASE2_IMAGES_COMMIT` in
  `config/pins.env` (workflow 01 verifies them against the registry). Docker
  Hub is pushed too only if the repository has the secrets `DOCKER_USERNAME`
  and `DOCKER_PASSWORD` (it does not, as of 2026-11-13).
- `05_runtime` needs `-c1` (its rules claim all cores so that nothing runs
  beside a timed process) and about 2 hours; do not run anything else on the
  machine meanwhile. `scripts/05_runtime.sh` forces one core. Target `pilot`
  runs the pilot and the plan only.
- `EXP_DIRTY` is computed when a workflow is parsed: do not edit tracked
  files (outside `results/`) while a run that is to be committed is going.
- The system disk was 81 % full on 2026-11-14 (88 GB free; `/data2` has
  3.4 TB, and `~/.singularity/cache` is a symlink to it). Singularity unpacks an image per job;
  `scripts/_snakemake.sh` sets `SINGULARITY_TMPDIR` to `/dev/shm/…`. When
  calling `snakemake` directly, export it yourself, and do not start several
  workflows at once without it (jobs die with empty logs: "No space left").
- Snakemake does not see changes in `R/` or `python/` (they are not rule
  inputs): after changing code, re-run the affected workflow with
  `--forceall`.
  To try something in an image by hand:
  `singularity exec docker://<image>@<digest> <command>`.
- Never state that something ran in a container unless the result's
  `container.image` field says so.

## Layout and conventions

- `config/pins.env`, `config/NN_*.json` — run conditions (machine readable).
- `data/synthetic/` — generated by `python -m sharedimp_exp.make_synthetic`,
  committed, described by `manifest.json` (sha256, generator, references).
  Values are rounded to 6 decimals so that the CSV text is the data. R's
  `read.csv` and pandas still parse a few of these values to doubles that
  differ in the last bit (1e-16): never test cross-language equality with
  `==`, and do "equals the raw data exactly" checks inside one language.
  `data/real/` — prepared by `python -m sharedimp_exp.real_data` from
  `config/04_real_data.json`; same manifest format plus source, DOI, license.
  Classification data on which unpenalized logistic regression separates a
  training fold are rejected (recorded under `rejected`).
- Strings such as `null` or `NA` are read as missing by pandas; do not use
  them as identifiers in result files.
- The `fold` column of a data file is the only source of splits: one split
  per label in increasing order, in both languages. Never let each language
  draw its own folds when results are to be compared.
- `R/common.R`, `R/run_jobs.R`, `R/env_info.R`; `python/sharedimp_exp/`
  (`common`, `learners`, `run_jobs`, `check_jobs`, `make_synthetic`,
  `env_info`, `host_info`, `docker_info`, `env_summary`; `rf_settings*` for
  02b; `official_*` and `R/official_umfi.R` for experiment B; `real_data*`
  for C; `maternal_*` for 04b; `null_forest*` and `R/null_forest.R` for 04c;
  `runtime*` and `R/runtime.R` for D; `R/figures.R`, `R/figures_phase3.R`).
  `data/derived/`, `data/null_forest/`, `data/runtime/` are written by 04b,
  04c and 05; `data/candidates/` is written by 04a and used by no experiment.
  `find_dataset` searches synthetic, real, derived and candidates. Scripts take
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
  are `none`: report the difference, never assert on it. The forest settings
  of the two languages are not equivalent and cannot be made identical
  (`docs/random_forest_comparison.md`).
- Learner mapping lives in `python/sharedimp_exp/learners.py` (Python) and in
  the R package's built-in names (R). Parity on rank-deficient designs needs
  an aliasing OLS in Python (common specification §8.1); avoid exact
  duplicates in parity data unless that learner is used.
- Stage numbers: `01` environment (experiment A), `02`
  validation / positive control, `02b` random-forest settings, `03` official UMFI (B), `04` real data (C),
  `04a` multiclass data-set selection (screening + pilot; outcome in `docs/multiclass_dataset_selection.md`), `04b` Maternal duplicates, `04c` null-design forest, `05` runtime (D), `06` figures (E), `07` manuscript (paper figures, PDF, checks; image `MANUSCRIPT_IMAGE` in `config/pins.env`, defined in the workflow itself).

## Before committing

Commit code first, then run the workflows with `--forceall`, one after the
other (01, 02, 02b, 03, 04, 04b, 04c, 05, 06; about 3 hours together with 16
cores, 2 of them for 05; 04b needs 04, 06 needs all), and commit the regenerated results, so that the results record a
clean code commit. Update `docs/STATUS.md`; numbers quoted in `docs/` are
copied from `results/tables/` and must be re-checked after a re-run. Small,
focused commits with imperative messages. Never report a workflow as passing
without having run it.
