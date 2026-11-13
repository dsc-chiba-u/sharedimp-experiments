# Status and open issues

Last updated: 2026-11-13 (end of Phase 2). Plan: `docs/experiment_plan.md`.
Numbers quoted here are copied from generated files, which are authoritative;
the file is named next to each number. Nothing here is a conclusion of the
paper: Phase 4 decides what is reported and how.

## Environment

`results/tables/01_environment.md`: host Ubuntu 22.04.5, Intel Xeon Gold 6226R
(16 cores / 32 threads), 1 thread per process; Snakemake 8.10.0 driving
Singularity 3.8.6. Every job runs inside an image referenced by digest
(`config/pins.env`): the two package images (`sharedimp-r` at `cf2e1cc`:
Ubuntu 24.04, R 4.5.3; `sharedimp-py` at `bacc5d8`: Debian 13, Python
3.13.18) and the two Phase 2 images built by GitHub Actions from `docker/`
(`sharedimp-experiments-r`, `umfi-official-py`, both at repository commit
`408e962`). The registry reports the pinned commit as revision label for all
four digests. Nothing is installed on the host besides Snakemake and
Singularity.

Checks with a criterion fixed in advance, over all workflows
(`results/summary/*/checks.csv`): 131 pass, 0 fail; 31 further rows are
"reported" (no criterion by design).

## Phase 1 — done (re-run with Phase 2, unchanged)

`results/tables/01_environment_checks.md`, `results/tables/02_validation_checks.md`:

- All 10 jobs ran in both languages; 57 checks pass, 5 are report-only
  (random forest).
- R–Python maximum absolute difference over every numeric column of both
  result tables: OLS 1.3e-15 to 6.2e-15 (criterion 1e-8); binary logistic
  1.9e-10 (1e-6); multinomial 4.3e-6 (1e-3).
- Positive control (OLS, MSE; `results/summary/02_validation/positive_control.csv`):
  importances 4.062, 2.464, 1.091, 0.007, 1.077 for x1..x5 in both languages,
  against the full-sample plug-in 4.059, 2.462, 1.089, 0.008, 1.075 and the
  population values 4, 2.56, 1, 0, 0.990.

## Phase 2 — done

### Random-forest settings (`docs/random_forest_comparison.md`, `results/tables/02b_rf_settings.md`)

- `min_n = 5` in R is ranger's `min.node.size` (nodes with more than 5 rows
  are split; leaves of one row allowed); `min_samples_leaf = 5` in Python is
  a terminal-node minimum. They are different rules; the R forest grew trees
  about three times as large (80.5 vs 24.5 leaves per tree on the regression
  data).
- By definition `min.node.size = k` ↔ `min_samples_split = k + 1` and
  `min.bucket = k` ↔ `min_samples_leaf = k`. Single deterministic regression
  trees confirmed both (same shape and training fit; identical trees for the
  leaf rule). One of ten pairings met the equivalence criterion; for the
  binary response none did, including the pairing with the same definition
  (43 vs 27 leaves).
- Under bootstrap ranger counts node sizes in draws, scikit-learn in distinct
  rows (smallest leaf: 5 draws / 1 row vs 5 draws / 5 rows).
- Importance on the regression data: largest cross-language difference 0.38
  with the settings of specification §8.2 as written, 0.05 with the split
  rule aligned (seed-to-seed SD ≤ 0.04; largest importance 4.45). Feature
  rankings were the same in every setting on the two data sets examined.
- Consequence here: forests are never compared numerically across languages.
  A change of the specification is proposed in that document; nothing was
  changed in the package repositories.

### Experiment B — official UMFI-LR code (`results/tables/03_official_umfi.md`, `_checks.md`)

Three official implementations were fetched at the pinned commits and run
unmodified: `HydroML/UMFI` (R package, MIT), `joej1997/UMFI` (the original R
script, no license; only its definitions of `modifty_linreg` and `UMFI` are
evaluated), `guanton/umfi_python` (Python, no license). All three ran.
18 checks pass, 0 fail, 20 rows are reported.

Comparable exactly (criterion 1e-8, met):

- **B1 Residualization.** Where the official dependence test passes, the
  official residual column and sharedimp's (same rows) differ by at most
  4.7e-15 (R, 18 feature pairs) and 2.2e-15 (Python, 22 pairs).
- **B2 Representation.** Same columns in the same order; anchor column equal
  to the raw anchor; sharedimp's Reduced representation equals its Full
  representation without the anchor column.
- **B3 Importance under an identical condition.** On a data set where every
  dependence test passes, the official importance and the official scoring
  rule applied to sharedimp's all-rows representation (same seed, same order
  of model fits) are identical (difference 0) in R (ranger) and in Python
  (extra trees and random forest), 5 seeds each. `HydroML/UMFI` and the
  original script are identical to each other as well.
- **B5a.** The training representation sharedimp hands to the learner is
  bit-identical after perturbing the assessment rows (R and Python, 10 fits
  each). **B5b.** A step-by-step pipeline built from `build_representations()`
  reproduces `shared_importance()` exactly (2500 values).

Not comparable by design (reported, no criterion):

- **Dependence test.** Where the official test fails, the official code keeps
  the raw column and sharedimp residualizes (difference up to 1.28). The two
  official implementations use different tests (p < 0.01 in R, R² > 0.01 in
  Python) and disagree with each other on 4 of 38 feature pairs. With such
  pairs present the official importance and the "official rule on sharedimp's
  representation" differ (up to 0.029 on `rf_reg_n300_p5`).
- **B4 Evaluation procedure.** On the four synthetic designs shipped with
  the official Python code (n = 500, 10 data sets each) the means of the
  official importances (all rows, out-of-bag R², 100 trees, floors) and of
  sharedimp's (fold-internal, 5-fold R², 500 trees) differ by at most 0.023
  (R) and 0.078 (Python, `RF=True`); between-data-set SDs are in the same
  table (figure `03_official_designs`).
- **B5 All-rows residualization.** Under otherwise identical 5-fold CV (OLS,
  MSE, positive-control design, 100 data sets per n), residualizing on all
  rows instead of the training rows raised the importance of the four
  informative features by 34 % at n = 30, 16 % at n = 60, 8 % at n = 120,
  1.8 % at n = 500 and 0.4 % at n = 2000 (`x1`: 5.34 vs 3.90 at n = 30,
  population value 4; figure `03_fold_internal_effect`). Measured with OLS
  only. Perturbing the assessment rows changes the official training
  residuals (up to 1.29), since `preprocess_lr()` is given all rows.
- **B6 Negative importance.** On the design with the response independent of
  the features every official value is exactly 0 (floors). sharedimp's values
  are signed: OLS mean −0.003, 86 % negative (identical in R and Python);
  forest mean +0.015 (R) and +0.009 (Python), 28 % and 40 % negative. The
  forest values are *not* centred at zero.
- **B7 Design differences.** Table with a source line, a recorded signature
  or an executed check for every cell. The official code offers things
  sharedimp does not: optimal-transport dependence removal (both), automatic
  choice of preprocessing (Python), `umfi_par()` (R).

### Experiment C — public data (`results/tables/04_real_data.md`, `_checks.md`)

Data (`data/real/`, sources and licenses in `data/real/README.md`): Concrete
Compressive Strength (n = 1030, p = 8), Breast Cancer Wisconsin (Diagnostic)
with the ten mean features (n = 569), Maternal Health Risk (n = 1014, p = 6,
three classes); all UCI, CC BY 4.0. Palmer penguins was prepared and
rejected by the rule fixed beforehand: the classes are completely separated
in every training fold, so the unpenalized logistic estimate does not exist.

- 12 jobs ran in both languages; 56 checks pass, 6 are report-only.
- `linear` learner, R vs Python, largest absolute difference over all result
  columns: OLS 5.3e-15 (criterion 1e-8); binary logistic 2.5e-9 (1e-6);
  multinomial 5.9e-6 (1e-3). Figure `04_r_python_agreement`.
- `rand_forest` (language-specific; settings not equivalent): largest
  difference over the result columns 1.43 (RMSE units, Concrete); Spearman correlation of the R and Python
  importances 0.90–1.00 on Concrete and Breast Cancer, 0.71 and −0.43 on
  Maternal Health Risk, where all forest importances are close to zero
  (|importance| ≤ 0.015 in log-loss).
- Score of the Full model (5 folds): Concrete OLS R² 0.604, forest 0.872 (R) /
  0.825 (Python); Breast Cancer log-loss 0.171 (logistic), 0.193 / 0.207
  (forest); Maternal log-loss 0.787 (multinomial), 0.443 / 0.547 (forest).
- Importances: figure `04_real_data_importance`. Several forest importances
  on Concrete are negative in both languages (e.g. slag −0.17 / −0.24 RMSE).

### Figures and tables

`results/figures/`: `03_official_designs`, `03_fold_internal_effect`,
`04_real_data_importance`, `04_r_python_agreement` (`.pdf`, `.png`).
`results/tables/`: `02b_rf_settings.md`, `03_official_umfi.md`,
`03_official_umfi_checks.md`, `04_real_data.md`, `04_real_data_checks.md`
next to the Phase 1 tables.

## Open issues

1. **Docker Hub.** The Phase 2 images are on GHCR only. This repository has
   no `DOCKER_USERNAME` / `DOCKER_PASSWORD` secrets (the package repositories
   do); the build workflow skips Docker Hub with a warning. Add the two
   secrets and re-run the workflow if `docker.io/koki/…` copies are wanted
   (`docker/README.md`).
2. **Specification §8.2 pairs non-equivalent forest parameters** (for the
   package maintainers; proposal in `docs/random_forest_comparison.md`).
   Until decided, the Python forest here follows §8.2 as written.
3. **Classification trees differ between ranger and scikit-learn in every
   pairing examined**, also with stopping rules of the same definition. The
   cause was not identified (ties between equally good splits are a
   candidate). Relevant for Phase 3: "aligned" forests do not do equal work.
4. **The forest importances on the null design are positive on average**
   (B6). Not investigated; the built-in forest draws `floor(sqrt(q))`
   candidates, and q differs between the Full and the Reduced model. To be
   understood before the paper says anything about values near zero.
5. **The all-rows effect (B5b) was measured with OLS only.** Its size for
   forests or other learners is unknown.
6. **Maternal Health Risk has 562 duplicated rows of 1014**; identical rows
   are in training and assessment folds. Scores of flexible learners on it
   are optimistic, and the R forest (larger trees) scores much better than
   the Python forest for that reason, presumably. Consider replacing the
   data set, or deduplicating, before the paper.
7. **One 5-fold split per data set.** The between-split SD shown is over 5
   splits; repeated CV was not run.
8. **R and Python parse some 6-decimal numbers to doubles that differ in the
   last bit** (1.1e-16). No effect on any tolerance used; exact comparisons
   with raw data are made inside one language.
9. **The system disk of the machine is 97 % full.** Singularity unpacks an
   image per job; the wrappers use `/dev/shm`. Running `snakemake` directly
   with many cores and without `SINGULARITY_TMPDIR` fails with empty logs.
10. **R and Python do not share a BLAS inside the images** (system OpenBLAS
    0.3.26 vs NumPy's bundled OpenBLAS); to be stated with any timing.
11. **The built-in R forest runs on one thread** (parsnip passes
    `num.threads = 1`); forests are slow (seconds per run in
    `results/tables/04_real_data.md`); Phase 3 needs a per-cell cap.
12. Parity is checked on full-rank designs only (common specification §8.1).
13. **SoftwareX guide and template not yet checked**; `paper/manuscript.Rmd`
    is a skeleton and has not been built. No manuscript image is defined.
14. The checker's own failure modes (tampered value, failed job) were
    verified in the conda-based run of Phase 1 (`6c094a1`), not again since.

## Next (Phase 3, not started)

Runtime benchmark (experiment D) with a pilot first; the forest comparison
split into "aligned settings" and "customary learners"
(`docs/experiment_plan.md`, section 6). Then Phase 4 (manuscript).
