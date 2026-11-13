# Experiment plan — sharedimp SoftwareX paper

Status: **Phase 1 complete (2026-11-13). Phases 2–4 are planned, not run.**
This file states what each experiment is for, what is run, what is checked and
which criteria were fixed *before* looking at the results. Results live in
`results/`; this file contains no result numbers except where a section is
explicitly marked "observed".

## 0. Scope and claims

The paper reports software: two packages (`sharedimp` for R/tidymodels and
for Python/scikit-learn) that implement the linear-regression variant of
ultra-marginal feature importance (UMFI-LR; Janssen, Guan & Robeva,
AISTATS 2023). It does **not** propose an importance measure.

Software contributions to be *verified*, not merely asserted:

| # | contribution | verified by |
|---|---|---|
| S1 | fold-internal residualization (no leakage of assessment rows) | B5; package tests (cited, not repeated) |
| S2 | paired cross-validated out-of-sample evaluation | B4, C |
| S3 | integration with tidymodels and scikit-learn; any learner / metric / resampling | B7, C (language-specific learners) |
| S4 | one specification, numerically agreeing R and Python implementations | A, 02, C (deterministic learner) |
| S5 | reproducible environment (pinned commits, Docker images) | A |

Rules that apply to every experiment:

- A difference from the official UMFI code is not a bug when the evaluation
  procedures differ; numerical agreement is claimed only under conditions
  constructed to be identical.
- Expected properties of UMFI-LR (e.g. correlated features sharing credit) are
  not presented as findings of sharedimp.
- Importances are out-of-sample predictive gains; no causal or conditional
  interpretation, no inference.
- Measured runtimes and complexity arguments are reported separately.
- A failed or skipped run is recorded as such; nothing is filled in by hand.

## 1. Infrastructure (Phase 1, done)

- Execution: Snakemake (>= 8.10) workflows `workflow/NN_*.smk`, run with
  `--use-singularity`. Every computing rule has a `container:` directive;
  nothing but Snakemake and Singularity is installed on the host
  (`environment.yml`). `scripts/NN_*.sh` are thin wrappers.
- `config/pins.env`: commits of the two packages and the digests of the
  package images built from exactly these commits
  (`ghcr.io/dsc-chiba-u/sharedimp-{r,py}`). Images are referenced by digest.
  Each process reads the image reference from inside the container and
  workflow 01 fails if it is not the pinned one; the registry is asked
  whether the pinned digest carries the pinned commit as revision label.
- Additional images (`docker/`): `koki/sharedimp-experiments-r` (the R image
  plus the dependencies of the official UMFI R package and plotting) and
  `koki/umfi-official-py` (dependencies of the official Python code at the
  versions of its `umfi.yml`; Python 3.9, so sharedimp-py cannot be in it and
  the two sides exchange files).
- Job files (`config/NN_*.json`): machine-readable run conditions (data set,
  learner, metric, seed, parity class with tolerance).
- Runners `R/run_jobs.R` and `python/sharedimp_exp/run_jobs.py`: same job
  file, same data file (sha256 verified against the manifest), same fold
  labels (the `fold` column of the data file; one split per label in
  increasing order). Output per job and language: `*.importance.csv`,
  `*.folds.csv` (17 significant digits), `*.meta.json`.
- `python/sharedimp_exp/check_jobs.py`: derives every summary table and
  evaluates the checks; non-zero exit on any failure. Verified to fail on a
  tampered value and on a job marked failed (2026-11-13).
- Threads: 1 everywhere by default (`OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS`,
  `MKL_NUM_THREADS`, `R_RANGER_NUM_THREADS`, `n_jobs`), recorded per run.
- Learner names: `linear` = R built-in `"linear"` / scikit-learn
  `LinearRegression`, `LogisticRegression(C=inf)`; `rand_forest` = R built-in
  (ranger, 500 trees, `min_n = 5`) / scikit-learn forest with 500 trees,
  `min_samples_leaf = 5`, `max_features = "sqrt"` (common specification §8).

## 2. Experiment A — environment and reproducibility (Phase 1, done)

Workflow: `workflow/01_environment.smk`. Records host OS, CPU, threads,
Snakemake and Singularity versions; inside the images the OS, R and Python
versions, dependency versions, BLAS, package versions and commits and
whether the process runs in the pinned image; and for the public images
`ghcr.io/dsc-chiba-u/sharedimp-{r,py}` the tag list, the digest of `latest`
and of the tag named after the pinned commit, whether the two are the
same image, and the revision label of the pinned digest. Then runs the smoke jobs (`config/01_smoke_jobs.json`: n = 20,
p = 3, 4 folds; OLS with `mse` and `r2`; random forest with `mse`).

The package test suites are not re-run here and their parity tests are not
duplicated; A only shows that both packages are callable from this
environment through the runners and agree on one tiny data set.

## 3. Validation of the implementations (Phase 1, done)

Workflow: `workflow/02_validation.smk`; jobs
`config/02_validation_jobs.json`.

- Binary (n = 60) and three-class (n = 90) smoke tests, p = 3, 3 stratified
  folds, labels drawn from a noisy logistic model so that the unpenalized
  fits exist.
- Positive control `pc_linear_n2000_p5` (5 folds):
  `x1, x3, x4 ~ N(0,1)`, `x2 = 0.8 x1 + 0.6 z`, `x5 = x3 + 0.1 z'`,
  `y = 2 x1 + x3 + e`, `e ~ N(0,1)`.

### Closed-form target of the positive control

For an OLS learner and MSE, write `x_j = a_j + b_j x_i + r_j` for the
population regression of feature `j` on the anchor `i`. `Full_i = (x_i, r_{-i})`
is an invertible affine transform of `x`, so the full model attains the same
risk as OLS on the raw features. In `Reduced_i = r_{-i}` every column is
uncorrelated with `x_i`, and `y = c + (Cov(y, x_i)/Var(x_i)) x_i + (terms in
r_{-i}) + e`, so dropping `x_i` adds exactly the variance explained by the
simple regression of `y` on `x_i`:

```
importance_i (MSE, OLS, population) = Cov(y, x_i)^2 / Var(x_i)
```

For the design above: `x1` 4, `x2` 2.56, `x3` 1, `x4` 0, `x5` 1/1.01. Note that
`x2` and `x5` have no direct effect on `y`; their non-zero value is the
definition of UMFI-LR at work (linear dependence on the anchor is removed
from the *other* features), not a discovery. Two consequences used as checks:
(i) for OLS the full score is the same for every anchor within a split;
(ii) the cross-validated estimate should be close to the full-sample plug-in
`Ĉov(y, x_i)^2 / V̂ar(x_i)` (closer than to the population value, whose
sampling error at n = 2000 is a few percent).

### Phase 1 checks (criteria fixed before the runs)

| check | criterion |
|---|---|
| every job completes in R and Python | status `ok` in both; `on_error = "error"` |
| same input | identical sha256 of the data file |
| schema and layout | common columns; identical row order, features, fold labels, split sizes |
| parity, OLS (`exact`) | max abs difference over all numeric columns of both tables ≤ 1e-8 |
| parity, binary logistic (`logistic`) | ≤ 1e-6 |
| parity, multinomial (`multinomial`) | ≤ 1e-3 (limited by `nnet::multinom`; the package test uses 1e-4) |
| random forest (`none`) | difference reported, never checked |
| OLS full-score invariance over anchors | spread within a split ≤ 1e-8 |
| positive control, OLS, signal features | relative deviation from the plug-in ≤ 10 % |
| positive control, OLS, noise feature `x4` | abs importance ≤ 0.05 |
| positive control, OLS, order | `x1 > x2 > {x3, x5} > x4` |
| positive control, random forest | `x1` ranked first and `|imp(x4)| ≤ 0.1 · imp(x1)` in each language |

Observed (2026-11-13, `results/tables/0{1,2}_*_checks.md`): all checks pass;
the numbers are in those tables and are summarised in `docs/STATUS.md`.

## 4. Experiment B — comparison with the official UMFI-LR code (Phase 2)

Workflow: `workflow/03_official_umfi.smk` (placeholder). Images:
`koki/sharedimp-experiments-r` (sharedimp-r and the official R package in one
R session) and `koki/umfi-official-py` (official Python code); see `docker/`.

Sources, verified on 2026-11-13 through the GitHub API:

| repository | language | commit | license |
|---|---|---|---|
| `HydroML/UMFI` | R | `54b964740ffb006d3ade759d84dc6e9af2f45998` (2024-06-24) | MIT |
| `guanton/umfi_python` | Python | `4db1c23f2355d69fc1471ae8df89c196d7a9a347` (2024-06-14) | none |
| `joej1997/UMFI` (original scripts) | R | `16ef563fda5aae1fdb6544001a0f04450799c134` (2022-07-17) | none |

No official code is copied into this repository (two of the three have no
license). The script clones each repository at the pinned commit into
`external/` (git-ignored), records the commit and the sha256 of the files it
uses, and sources/imports them unmodified. If an official implementation
cannot be run (missing dependency such as `minepy`, R version, …) the reason
is recorded in `results/raw/03_official_umfi/` and the corresponding rows are
marked `not run`. The package-side records
(`sharedimp-r/docs/umfi_comparison.md`, `sharedimp-py/docs/relation_to_umfi.md`,
`tests/test_parity_official.py`) are the starting point and are re-derived
here from this environment rather than quoted.

| # | question | method | agreement expected? |
|---|---|---|---|
| B1 | residualization | official `preprocess_lr` / `preprocess_LR` vs `residualize_fit/apply` (R) and `AnchorResidualizer` (Python) on the same rows, per feature pair, separated by whether the official gate fires | yes where the gate fires (≈ 1e-12); no where it does not (official keeps the raw column) |
| B2 | Full / Reduced representation | column set, order, anchor position, values | yes under the B1 condition |
| B3 | importance, same learner and same evaluation data | apply the official scoring rule (forest, OOB R², floors) to sharedimp's representations with the same seed and fit order; conversely evaluate sharedimp's paired-CV rule on representations built the official way | exact only for the constructed identical condition; stated per row |
| B4 | evaluation procedure | table: all-rows preprocessing + OOB vs fold-internal + held-out; plus the size of the numerical difference on the paper's synthetic designs (several seeds) | no; differences reported with between-seed spread |
| B5 | fold-internal residualization | (a) structural test: perturb assessment rows, compare training representations; (b) size of the effect: all-rows vs fold-internal residualization under otherwise identical CV, as a function of n | (a) exact invariance for sharedimp; (b) reported, expected to shrink with n |
| B6 | negative importance | response independent of all features: official values (floored at 0) vs sharedimp (signed, centred near 0) | no; this is a design difference |
| B7 | learner / metric / CV API | feature table built from code inspection, each cell backed by an executed call or a quoted line reference | — |

Outputs: `results/raw/03_official_umfi/`, `results/summary/03_official_umfi/`,
Figure 2.

## 5. Experiment C — real data (Phase 2)

Workflow: `workflow/04_real_data.smk` (placeholder). A download script fetches
each file from its source, verifies sha256, applies the documented
preprocessing and writes `data/real/<id>.csv` with a `fold` column plus an
entry in `data/real/manifest.json` (source URL, license, retrieval date,
preprocessing, features, target).

Candidates — **source, license and availability still have to be verified in
Phase 2 before any is adopted**:

| task | candidate | why |
|---|---|---|
| regression | UCI Concrete Compressive Strength (n = 1030, p = 8) | continuous mixture components with known mutual dependence; no missing values |
| binary | UCI Breast Cancer Wisconsin (Diagnostic) (n = 569; the 10 "mean" features) | strongly correlated size features (radius / perimeter / area) |
| multiclass (optional) | Palmer penguins (complete cases; 4 continuous measurements, 3 species) or UCI Wine (n = 178, p = 13) | small, continuous, correlated |

Design: same file, same fold labels, same metric in both languages.
(i) Deterministic learner (`linear`): R–Python agreement checked with the
parity classes of §3. (ii) Language-specific learners (ranger /
scikit-learn random forest, possibly one more per language): usage examples;
no numerical agreement required, rank agreement reported. Repeated CV
(e.g. 5 × 5 folds, fixed labels) so that the between-split spread can be
shown descriptively. Outputs: importance tables, Figure 3 (importances with
split-level spread; feature correlation structure next to it so that the
behaviour of correlated groups can be read off).

## 6. Experiment D — runtime (Phase 3)

Workflow: `workflow/05_runtime.smk` (placeholder). Timing cells are run one
at a time (`-c1`), never in parallel with other jobs.

- Data: synthetic regression, generated once per (n, p) cell and stored;
  identical files and fold labels for both languages.
- Factors, one at a time around a base cell (n = 1000, p = 10, v = 5):
  n, p, v, learner (`linear`, `rand_forest`). The grid is fixed **after** a
  pilot (two values per factor, one repetition).
- Protocol: 1 thread; 1 warm-up run discarded, then ≥ 5 timed runs per cell;
  median and IQR (and min) reported; wall-clock of the
  `shared_importance()` call only (no data loading, no process start-up).
- Budget: a cell whose pilot-predicted time exceeds the per-cell cap is not
  run and is recorded as `skipped (budget)`; total budget for the main
  benchmark ≤ 2 h. Phase 1 gives one reference point: random forest,
  n = 2000, p = 5, v = 5 took ≈ 46 s in each language (single thread), so
  large-p forest cells will have to be capped.
- Recorded with every timing: language, package commit, learner
  implementation and version, BLAS, threads, CPU.
- Interpretation: differences between R and Python include learner
  implementation (ranger vs scikit-learn; `lm.fit` vs LAPACK `gelsd`) and
  runtime overheads; they are not attributed to "the language". Complexity
  (2·v·p learner fits; residualization O(v·n·p²) in total) is discussed
  separately from the measurements.

## 7. Experiment E — figures and tables (Phases 2–3)

Workflow: `workflow/06_figures.smk` (placeholder). Each figure is
produced by one script from files in `results/summary/` only.

| figure | content | source |
|---|---|---|
| 1 | workflow: input → fold-internal residualization → Full/Reduced learner → paired scoring → importance; shared by R and Python | drawn (no data) |
| 2 | numerical validation: official UMFI-LR vs sharedimp (B1–B6) and R–Python parity (A, 02, C) | `results/summary/{01,02,03,04}_*` |
| 3 | real-data importances | `results/summary/04_real_data` |
| 4 | runtime scaling in n, p, v | `results/summary/05_runtime` |

The number of figures will be adjusted to the SoftwareX guide (to be checked
in Phase 4) and to what the results support.

## 8. Manuscript (Phase 4)

`paper/` holds the manuscript only in this repository. Before drafting: read
the current SoftwareX guide for authors and template. Numbers in the text
come from `results/` through code chunks or generated tables, not typed in.
No DOI, release or result that does not exist yet is cited.

## 9. Open issues after Phase 1

See `docs/STATUS.md`.
