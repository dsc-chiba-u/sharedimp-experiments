# Experiment plan — sharedimp SoftwareX paper

Status: **Phases 1 to 3 complete (2026-11-14): experiments A, B, C, the
random-forest settings study, the two follow-ups of Phase 2 (duplicated rows
of the Maternal Health Risk data, forest importance under a null design) and
experiment D (runtime). Phase 4 (manuscript) is planned, not started.**
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
- Singularity unpacks an image for every job; `scripts/_snakemake.sh` points
  `SINGULARITY_TMPDIR` to `/dev/shm` because the system disk of the machine
  used here is nearly full (parallel jobs failed with "No space left on
  device" otherwise).
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

## 3b. Random-forest settings (Phase 2)

Workflow: `workflow/02b_rf_settings.smk`, configuration
`config/02b_rf_settings.json`. Question, method, results and the resulting
recommendations are in `docs/random_forest_comparison.md`. The only
pass/fail statement is whether a pair of single-tree settings meets the
equivalence criterion written in the configuration file (same number of
leaves, same depth, predictions equal within 1e-8 on training rows and on a
held-out fold); nothing is asserted about forests.

## 4. Experiment B — comparison with the official UMFI-LR code (Phase 2)

Workflow: `workflow/03_official_umfi.smk`, configuration and criteria
`config/03_official_umfi.json`, design table `config/03_api_comparison.json`.
Images: `sharedimp-experiments-r` (sharedimp-r and the official R code in one
R session) and `umfi-official-py` (official Python code, Python 3.9); see
`docker/`.

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
`results/tables/03_official_umfi{,_checks}.md`, figures
`03_official_designs` and `03_fold_internal_effect`.

### As executed (2026-11-13)

- **How the official code is run.** `fetch_official` (host, git) fetches the
  three repositories at the pinned commits into `external/` and records the
  sha256 of every file read (`sources.json`). `HydroML/UMFI`: `R/preprocess_lr.R`
  and `R/umfi.R` are sourced. `joej1997/UMFI`: the file is a script that runs
  the paper's experiments (absolute Windows paths, many packages), so it is
  parsed and only the first definitions of `modifty_linreg` and `UMFI` are
  evaluated. `guanton/umfi_python`: `umfi.preprocess_LR`, `umfi.UMFI` and the
  generators of `umfi.experiments` are imported. Nothing is modified or copied.
- **Data.** B1/B2: `smoke_reg_n20_p3`, `rf_reg_n300_p5`, `allgate_reg_n300_p4`.
  B3: `allgate_reg_n300_p4`, in which every pair of features is clearly
  dependent, so that the official dependence test passes everywhere and the
  official representation is the same function of the data as sharedimp's;
  `rf_reg_n300_p5` as the contrast. B4: the four synthetic designs of the
  official Python repository (`nonlinear_interaction`,
  `correlated_interaction`, `correlation`, `blood_relation`), produced by
  the official generators after `numpy.random.seed(s)`, n = 500, s = 1..10.
  B6: a design with the response independent of the features, same n and
  seeds. B5b: the positive-control design simulated in R, n = 30, 60, 120,
  500, 2000, 100 data sets each, OLS, MSE, 5 folds.
- **B3 construction.** R: `set.seed(s); umfi(X, y)` against `set.seed(s)` and
  the official scoring rule (two `ranger` forests with 100 trees, out-of-bag
  R² floored at 0, difference, negatives set to 0) applied to
  `build_representations(X, X, anchor)`; same call order, hence same random
  numbers. Python: the same with `numpy.random.seed(s)`, `UMFI(niter = 1)`,
  and the representation of `AnchorResidualizer` passed as a CSV file with 17
  significant digits (sharedimp-py cannot be installed under Python 3.9).
- **Criteria** (tolerance 1e-8, fixed in the config file before the run):
  B1 where the official test passes; B2 layout, anchor, Reduced = Full minus
  anchor; B3 on the all-gates data set; B5a bit-identity; B5b agreement of the
  step-by-step pipeline with `shared_importance()`; B7 every statement backed
  by a source line, a signature or a check. Everything else is reported.
- **Deviations from the plan above.** B4 uses the designs shipped with the
  official Python code instead of re-typing the designs of the paper. B5b is
  measured with OLS only (deterministic; no Monte Carlo noise from the
  learner); the size of the effect for other learners was not measured.
- **Found while implementing.** R's `read.csv` and pandas parse the same
  6-decimal text to doubles that differ in the last bit for a few values
  (largest difference 1.1e-16). Exact comparisons with the raw data are
  therefore made inside each language. The name `null` for a design is read
  as a missing value by pandas; the design is called `independent`.

## 5. Experiment C — real data (Phase 2)

Workflow: `workflow/04_real_data.smk`; sources and preprocessing
`config/04_real_data.json`; jobs `config/04_real_data_jobs.json`.
`python/sharedimp_exp/real_data.py` downloads each file, verifies the pinned
sha256, applies the preprocessing and writes `data/real/<id>.csv` (columns
`fold`, `y`, features) and `data/real/manifest.json` (source URL, DOI,
citation, license, retrieval date, preprocessing, checks).

Selection criteria (fixed before any importance was computed): public and
re-downloadable from a stable URL; source and license stated by the provider;
continuous features with some strongly correlated ones; no or trivial missing
values; small enough to run in minutes; and, for classification, **the
unpenalized (multinomial) logistic maximum-likelihood estimate must exist**
(no complete separation in any training fold), because the deterministic
learner used for the R–Python comparison is unpenalized.

| task | data set | source, license (verified 2026-11-13) | decision |
|---|---|---|---|
| regression | Concrete Compressive Strength, n = 1030, p = 8 | UCI ML Repository 165, doi:10.24432/C5PK67, CC BY 4.0 | used |
| binary | Breast Cancer Wisconsin (Diagnostic), the ten "mean" features, n = 569 | UCI 17, doi:10.24432/C5DW2B, CC BY 4.0 | used |
| three classes | Maternal Health Risk, n = 1014, p = 6 | UCI 863, doi:10.24432/C5DP5D, CC BY 4.0 | used |
| three classes | Palmer penguins, 4 measurements, n = 342 complete cases | palmerpenguins (GitHub, commit `8957207`), doi:10.5281/zenodo.3960218, CC0 | **rejected by the separation rule**: the species are completely separated in every training fold |

UCI Wine (n = 178, p = 13), the other candidate of Phase 1, was not prepared:
with 13 features and 178 rows it is expected to be separated as well, and one
multiclass example suffices. The license of the UCI data sets is the CC BY 4.0
link on each data set's page; DOI and creators come from the UCI API.

Preprocessing, the same for every data set: select and rename columns, drop
rows with missing values (none in the three data sets used), standardize
every feature with the mean and SD of all rows, round to 6 decimals, draw
5 fold labels from a seeded permutation (stratified by class). The learners
used here are invariant to an affine rescaling of a feature (up to
optimiser tolerance), so standardizing with all rows conditions the
optimisers without passing information between folds through the model.

Jobs: for every data set the `linear` learner with two metrics (checked with
the parity classes of §3) and the `rand_forest` learner with the same two
metrics (language-specific usage example: reported, never checked). The
forest settings of the two languages are not equivalent
(`docs/random_forest_comparison.md`).

Outputs: `results/raw/04_real_data/`, `results/summary/04_real_data/`
(`checks`, `parity`, `importance_long`, `importance_wide`, `datasets`,
`performance`), `results/tables/04_real_data{,_checks}.md`, figures
`04_real_data_importance` and `04_r_python_agreement`.

Deviations from the Phase 1 sketch: one 5-fold split instead of repeated
cross-validation (the between-split SD shown is over 5 splits); the
correlation structure is summarised by the largest absolute feature
correlation in the data-set table, not drawn. Known limitation: Maternal
Health Risk contains many duplicated rows (count in the data-set table), so
identical rows occur in training and assessment folds and the scores of
flexible learners on it are optimistic; it is used as distributed.

## 5b. Follow-up of experiment C — duplicated rows of the Maternal Health Risk data (Phase 3)

Workflow: `workflow/04b_maternal.smk`; configuration and criteria
`config/04b_maternal.json`; jobs `config/04b_maternal_jobs.json`. Reading
and recommendation: `docs/maternal_duplicates.md`.

Question: experiment C used the file as distributed, with random stratified
folds; many rows are identical, so identical rows are in training and
assessment folds. How much do the score of the Full model and the
importances depend on that?

- Definitions (config file): *identical record* = equal in the six features
  and the label; *identical features* = equal in the six features;
  *conflicting group* = identical features with more than one label.
- The data file of experiment C is not changed. Two derived files are
  written to `data/derived/` (own `manifest.json` with sha256):
  `maternal_grouped` (all rows; folds from scikit-learn's
  `StratifiedGroupKFold`, group = identical features) and `maternal_dedup`
  (first occurrence of every identical record; the same kind of folds).
  Feature values are those of the source file (not standardized again).
- The four Maternal jobs of experiment C (linear and forest, log-loss and
  accuracy) are run on both files in R and Python with the same fold column;
  the results of experiment C for the original file are read, not recomputed.

Criteria (fixed before the run): no feature vector occurs in more than one
fold of a derived file; `maternal_grouped` has the rows of the source in the
same order and `maternal_dedup` exactly one row per identical record; the
separation rule of §5 holds for both; `linear` jobs agree between R and
Python within the multinomial tolerance of §3 (1e-3); every job completes in
both languages with identical input and layout. Changes of scores and
importances between the three files are reported, not judged.

## 5c. Follow-up of experiment B6 — forest importance under a null design (Phase 3)

Workflow: `workflow/04c_null_forest.smk`; configuration
`config/04c_null_forest.json`. Reading: `docs/null_forest_investigation.md`.

Question: in B6 the forest importances were positive on average although
the response was independent of the features. Which ingredient produces
that? A small simulation, deliberately not a benchmark: 20 data sets per
design (n = 300, p = 5 as in B6; n = 300, p = 4, where `floor(sqrt(q))`
differs between the Full and the Reduced model; n = 1200, p = 5 for three
settings), equicorrelated normal features, `y ~ N(0, 1)`, 5 folds, MSE.
The same data, folds and seeds are used in every setting and one setting is
changed at a time from the baseline (the forests of B6): candidates per
split (as in the Full model / all / one), tree depth (depth 2; large
nodes), no bootstrap, number of trees (50, 2000), number of columns (the
Reduced model padded with an independent noise column; the Full model built
from the Reduced representation plus that noise column), the closest
scikit-learn setting (Python), and OLS as a reference. Representations come
from the packages (`build_representations()`, `AnchorResidualizer`); the
forests are called directly (`ranger`, `RandomForestRegressor`) so that
single settings can be changed.

No criterion: every number is reported with its Monte Carlo standard error
over the data sets. The study does not establish that a forest importance
is zero, non-negative or non-positive in general.

## 5d. Replacement of the multiclass data set of experiment C

Reason: the Maternal Health Risk file contains many repeated records of
undocumented origin (§5b). The multiclass example of the paper is to be a
data set whose rows are documented observations. The Maternal results stay
in the repository as a sensitivity / supplementary analysis.

### Criteria (written on 2026-11-14, before any candidate file was downloaded or analysed)

Candidates named beforehand: UCI Abalone with `Sex` as response (dataset 1),
UCI Vertebral Column, three-class version (212), UCI Seeds (236), UCI Dry
Bean (602), UCI Statlog Vehicle Silhouettes (149).

A candidate is **eligible** only if all of the following hold. They are
assessed in this order; none of them uses an importance.

| | criterion |
|---|---|
| E1 | public, downloadable from a stable URL, with a DOI; the provider states a license that allows redistributing a modified version (CC BY 4.0 or more permissive) |
| E2 | at least three classes; the provider's documentation says what a row is, and rows are distinct observational units |
| E3 | at least four continuous features, at least one pair with absolute correlation ≥ 0.7, and full column rank. If features are linearly dependent *by their documented definition*, the feature that is the combination of the others is dropped before anything else is computed |
| E4 | rows with a missing value in the columns used: at most 1 % (they are dropped) |
| E5 | rows whose feature vector also occurs in another row: at most 1 % of the rows. If there are any, the folds keep identical feature vectors together (as in §5b); the rows stay |
| E6 | every class has at least 50 rows |
| E7 | n ≤ 5000 and p ≤ 12 (the forest jobs fit 2·p·5 forests of 500 trees on one thread) |
| E8 | the separation rule of §5: unpenalized multinomial logistic regression misclassifies at least one training row in every training fold; and neither optimiser reports a failure (no convergence warning from scikit-learn in the check; no warning recorded by the R job) |
| E9 | pilot with the `linear` learner, the two metrics of the Maternal jobs (log-loss, accuracy), the same file and fold column in both languages: R and Python agree within the existing `multinomial` tolerance (1e-3). The tolerance is not changed |

Among the eligible candidates the choice is made by these preferences, in
this order:

| | preference |
|---|---|
| P1 | predicting the class from the features is the documented purpose of the data set (preferred), or at least a use documented by the provider or in published work; a target that was only repurposed here ranks below |
| P2 | the classification is neither trivial nor empty: the cross-validated log-loss of the Full multinomial model is lower than that of predicting the class proportions, and the accuracy is below 1. (A score of the model, not an importance) |
| P3 | more rows; then fewer features |

Rules for the outcome:

- Importances are computed only for the chosen data set, after the choice.
- If no candidate is eligible, nothing is replaced: the group-aware Maternal
  analysis (`maternal_grouped`) stays the provisional multiclass example and
  the reasons are reported.
- A candidate that fails a criterion is recorded with the criterion and the
  observed value; a file prepared for it is not kept among the data used.
- The forest jobs of the chosen data set are run and reported only; no
  agreement between R and Python is required of them.
- The results of Phases 1 to 3 are not changed by the replacement: the
  Maternal jobs keep their job ids, data file, folds and seeds; the runtime
  benchmark (05) is not re-run.

## 6. Experiment D — runtime (Phase 3)

Workflow: `workflow/05_runtime.smk`; conditions, protocol, budget rule and
criteria `config/05_runtime.json` (**written before the pilot was run**).
Protocol, complexity and reading: `docs/runtime_benchmark.md`.

- **Data.** Synthetic regression (features with correlation `0.5^|j-k|`,
  response with three main effects and one interaction), one file per
  (n, p), one fold column per number of folds; generated by
  `python/sharedimp_exp/runtime_data.py`, sha256 in
  `data/runtime/manifest.json` (tracked; the CSV files, several MB, are
  regenerated). Both languages verify the checksum and use the same fold
  column.
- **Factors**, one at a time around the base cell (n = 1000, p = 10, v = 5):
  n ∈ {125, …, 32000}, p ∈ {5, …, 160}, v ∈ {2, 3, 5, 10, 20}; language;
  learner. These are *candidate* cells; which of them are run is decided by
  the budget rule from the pilot.
- **Learners, three comparisons, never mixed in one curve.**
  A. linear regression: R built-in `"linear"` (`lm.fit`) against
  `LinearRegression()`.
  B. random forest, *aligned settings*: R built-in `"rand_forest"` against
  `RandomForestRegressor(n_estimators=500, min_samples_split=6,
  min_samples_leaf=1, max_features="sqrt", bootstrap=True, n_jobs=1)`. The
  stopping rules have the same definition; the trees are not the same
  (`docs/random_forest_comparison.md`).
  C. random forest, *customary settings*: R built-in against
  `RandomForestRegressor()` with scikit-learn's defaults; a practical
  comparison, not one of equal work. The R forest is measured once and used
  in B and C.
- **Protocol.** One process per language and learner; the processes run one
  after the other and nothing else is run by the workflow at the same time.
  1 thread. Per cell: data read and fold list built (not timed), 1 warm-up
  call (discarded), 5 timed calls of `shared_importance()` with the same
  seed; garbage collected before each call, outside the timed region.
  Reported: median, quartiles (IQR) and minimum.
- **Pilot.** Seven cells (base and two values per factor), one warm-up on
  the first cell and one timed run per cell and process. Per process a
  least-squares fit of log(seconds) on log n, log p, log v predicts the
  candidate cells; it is a planning device, not a complexity estimate.
- **Budget.** Main benchmark ≤ 2 h in total. A cell costs 6 × its predicted
  time; cells above the per-cell cap are recorded as `skipped (budget)`; the
  cap is the largest of a fixed list for which the planned total is at most
  80 % of 2 h. A cell whose warm-up shows that it would cost more than twice
  the cap is stopped (`skipped (budget, after warm-up)`); a process that has
  used 1.25 × its planned time skips its remaining cells.
- **Recorded** with every process: language and runtime version, package
  versions, BLAS/LAPACK library, CPU, threads and thread variables, timer,
  container image, package commit, commit of this repository, load average
  before every run.

Criteria (fixed before the pilot; `config/05_runtime.json`): every candidate
cell is measured with 5 timed runs or recorded as skipped with a reason;
both languages read the same file and fold column in every cell; for the
linear learner the importances of the timed calls agree between R and Python
within 1e-8 (the two languages did the same work); one call fits the learner
exactly 2·p·v times (counted with a counting learner); 1 thread everywhere;
the main processes took at most 2 h; every process ran in the pinned image.
Timings themselves are reported, never judged.

Interpretation: differences between R and Python include the learner
implementation (`lm.fit` vs LAPACK `gelsd`; ranger vs scikit-learn), the
linear-algebra libraries and the overhead of each framework; they are not
attributed to "the language". The complexity argument (2·v·p learner fits;
residualization O(v·n·p²) in total) is given separately from the
measurements, and no order of growth is read off the measured times.

## 7. Experiment E — figures and tables (Phases 2–3)

Workflow: `workflow/06_figures.smk` (`R/figures.R` for Phase 2,
`R/figures_phase3.R` for Phase 3, in the `sharedimp-experiments-r` image). Every figure is drawn from files in
`results/summary/` only, as `.pdf` and `.png` in `results/figures/`.

| file | content | source | status |
|---|---|---|---|
| `03_official_designs` | B4/B6: importance on the official synthetic designs, official code vs sharedimp | `03_official_umfi/importance_by_design.csv` | done |
| `03_fold_internal_effect` | B5b: all-rows vs fold-internal residualization as a function of n | `03_official_umfi/leak.csv` | done |
| `04_real_data_importance` | C: importance on the public data sets, R and Python, linear and forest | `04_real_data/importance_wide.csv` | done |
| `04_r_python_agreement` | R vs Python importance for every job of 01, 02, 04; largest difference against the tolerance | `{01,02,04}_*/{importance_long,parity}.csv` | done |
| `04b_maternal_duplicates` | Maternal Health Risk: score of the Full model and importances with random folds, group-aware folds, identical records removed | `04b_maternal/{scores,importance_by_variant}.csv` | done |
| `04c_null_forest` | null design: mean forest importance per setting | `04c_null_forest/summary.csv` | done |
| `05_runtime_scaling` | D: runtime against n, p and the number of folds for the three comparisons, R and Python | `05_runtime/comparisons.csv` | done |
| `05_runtime_learners` | D: every learner at the base cell; Python / R along the sweeps | `05_runtime/{cells,comparisons}.csv` | done |
| (workflow diagram) | input → fold-internal residualization → Full/Reduced learner → paired scoring → importance | drawn (no data) | Phase 4 |

Tables: `results/tables/03_official_umfi.md` (sources, residualization,
identical condition, designs, null design, all-rows effect, design
differences), `results/tables/04_real_data.md` (data sets, run conditions,
scores, importances), `results/tables/02b_rf_settings.md`, and the
`*_checks.md` tables. Which of these become figures or tables of the paper is
decided in Phase 4.

The number of figures will be adjusted to the SoftwareX guide (to be checked
in Phase 4) and to what the results support.

## 8. Manuscript (Phase 4)

`paper/` holds the manuscript only in this repository. Before drafting: read
the current SoftwareX guide for authors and template. Numbers in the text
come from `results/` through code chunks or generated tables, not typed in.
No DOI, release or result that does not exist yet is cited.

## 9. Open issues after Phase 1

See `docs/STATUS.md`.
