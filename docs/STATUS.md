# Status and open issues

Last updated: 2026-11-14 (Phase 4: first draft of the manuscript). Plan: `docs/experiment_plan.md`.
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
(`results/summary/*/checks*.csv`): 218 pass, 0 fail; 57 further rows are
"reported" (no criterion by design). Of these, 131 pass / 31 reported belong
to Phases 1 and 2 (workflows 01, 02, 03, 04), the same counts as at the end
of Phase 2.

All results were regenerated on 2026-11-14 with `--forceall` at code commit
`e516acd` (recorded in every result, no uncommitted code changes); the
figures were redrawn afterwards at the following commit, which changed two
labels of one figure. The Phase 1 and 2 summaries and tables are identical
to the committed ones except for the columns of elapsed seconds.

## Phase 1 — done (re-run with Phase 3, unchanged)

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

## Phase 3 — done

### Maternal Health Risk: duplicated rows (`docs/maternal_duplicates.md`, `results/tables/04b_maternal.md`)

- 1014 rows, 452 distinct records (features and label), 416 distinct
  feature vectors. 562 rows repeat an earlier record (the "562" of Phase 2
  is this definition); 598 repeat an earlier feature vector; 35 feature
  vectors (215 rows) carry more than one label. The last 300 rows or so add
  almost no new record (3, 0, 0, 0 per block of 100). The provider's page
  has no patient identifier and says nothing about duplicates.
- With the random folds of experiment C, 807 of 1014 assessment rows have
  their feature vector in the training rows.
- Derived files in `data/derived/` (the original is unchanged):
  `maternal_grouped` (all rows, group-aware folds) and `maternal_dedup`
  (452 rows, group-aware folds). 42 + 36 checks pass; multinomial logistic
  regression agrees between R and Python (9.5e-6 and 3.1e-6, criterion 1e-3).
- Full-model log-loss, random → group-aware → identical records removed:
  multinomial logistic 0.787 → 0.804 → 0.781; forest R 0.443 → 0.794 →
  0.696, Python 0.547 → 0.739 → 0.686. The forest's advantage in experiment
  C came from rows present in training and assessment folds.
- Linear importances (log-loss): unchanged with group-aware folds (largest
  change 0.003, Spearman 1.000); Spearman 0.771 with identical records
  removed (blood sugar first in all three).
- Recommendation: group-aware folds with all rows as the main analysis if
  the data set is kept (no assumption about what the copies are needed);
  identical records removed as sensitivity analysis; preferably another
  multiclass data set for the paper. Decision open (issue 6).

### Forest importance under a null design (`docs/null_forest_investigation.md`, `results/tables/04c_null_forest.md`)

Small simulation (20 data sets per design, response independent of the
features, one setting changed at a time, R and Python).

- p = 5, n = 300, baseline: +0.0136 ± 0.0033 (R), +0.0075 ± 0.0021
  (Python). Both models predict worse than the training mean; the
  importance is a difference of two amounts of overfitting.
- Equal number of columns (noise column added to the Reduced model):
  +0.0015 / +0.0003. Noise column in place of the anchor: +0.0131 /
  +0.0064, as the baseline. The positive mean comes with the extra column,
  not with the anchor.
- p = 4 (candidates per split 2 for Full, 1 for Reduced): baseline about
  zero (+0.0024 / −0.0051); with the same number of candidates in both
  models +0.0287 / +0.0179. The sign depends on how `floor(sqrt(q))` falls.
- Not the cause: number of trees (50, 500, 2000 give the same mean), finite
  assessment sample (n = 1200: +0.0149 / +0.0091, all 20 data sets
  positive). Shallow trees shrink it; no bootstrap enlarges it.
- OLS: −0.0046 (n = 300), −0.0009 (n = 1200), about −σ²/n_train.
- Not settled: a remainder of about two standard errors with equal column
  numbers in the p = 4 and n = 1200 designs; one correlation structure,
  regression only. No theoretical statement is made.

### Runtime (experiment D; `docs/runtime_benchmark.md`, `results/tables/05_runtime.md`)

- Protocol as planned: 1 thread, 1 warm-up + 5 timed calls per cell, only
  the `shared_importance()` call timed, one process per language and
  learner run one after the other, same data file and folds in both
  languages. 9 checks pass (incl. linear R = Python within 1.0e-14 in all
  18 cells; 2·p·v learner fits counted in both languages).
- Budget: 2 h for the main benchmark; cap 600 s per cell from the pilot.
  **59 of 90 cells measured, 31 skipped by the budget rule** (all of them
  forest cells: n ≥ 2000, p ≥ 20, v ≥ 10; the customary scikit-learn forest
  also has n = 2000 and v = 10). Main processes 5239 s, pilot 1803 s.
- Base cell (n = 1000, p = 10, v = 5), median seconds: linear 0.184 (R) /
  0.305 (Python); forest R built-in 58.5, scikit-learn aligned 88.9,
  scikit-learn defaults 35.1.
- Linear: nearly flat in n up to 1000 (fixed cost per fit); Python / R
  1.73 at n = 125, 0.78 at n = 32000; p = 160: 15.4 / 19.3 s; proportional
  to v.
- No order of growth is claimed, and no "R vs Python" ranking (different
  learner implementations and BLAS builds; the ratio changes sign).

### Selection of a multiclass data set (`docs/multiclass_dataset_selection.md`, `results/tables/04a_multiclass_*.md`)

Attempt of 2026-11-14 to replace Maternal Health Risk as the multiclass
example, with criteria committed beforehand (`docs/experiment_plan.md`, §5d).

- Five UCI candidates. Dry Bean and Statlog Vehicle: too large (E7).
  Vertebral Column: one feature is the exact sum of two others; without it
  the largest feature correlation is 0.598 < 0.7 (E3). Seeds: complete
  separation in four of five training folds (E8).
- Abalone with `Sex` as response (n = 4177, 7 measurements, classes 1307 /
  1342 / 1528, no missing values, no two rows with the same measurements,
  largest correlation 0.987, no separation: training accuracy 0.556–0.568)
  passed E1–E8. Pilot with the `linear` learner: log-loss agrees between R
  and Python within 2.8e-06; **accuracy differs by 0.0012 > 1e-3**: one
  assessment row of 836 in one of 40 models is classified differently, its
  two top class probabilities being 4.5e-07 apart (probabilities of the two
  fits agree within 1.2e-05; `nnet::multinom` converged).
- **Outcome: no candidate is eligible, experiment C is unchanged**, and
  `maternal_grouped` stays the provisional multiclass example. The tolerance
  was not changed. The target `Sex` is also not the documented purpose of
  the Abalone data.
- Workflow 04a: 9 of 10 pilot checks pass; the failed parity check is the
  recorded outcome of the pilot (it is not counted among the checks of the
  experiments above).

### Proposal for the packages (`docs/package_change_proposal.md`)

Text for a documentation-only change of specification §8.2 (R `min_n = 5`
↔ scikit-learn `min_samples_split=6, min_samples_leaf=1`; the two forests
stated as not equivalent). Not applied: the package repositories are
read-only from here.

### Figures and tables added

`results/figures/`: `04b_maternal_duplicates`, `04c_null_forest`,
`05_runtime_scaling`, `05_runtime_learners`. `results/tables/`:
`04b_maternal.md`, `04b_maternal_checks.md`, `04b_maternal_jobs_checks.md`,
`04c_null_forest.md`, `05_runtime.md`, `05_runtime_checks.md`.

## Phase 4 — first draft of the manuscript

`paper/manuscript.Rmd`, built by `workflow/07_manuscript.smk` in the image
`sharedimp-manuscript` (pinned in `config/pins.env`); requirements and their
sources in `docs/softwarex_requirements.md`.

- Journal requirements were taken from the current templates (version 6,
  March 2026) and from the author's earlier SoftwareX submission
  (`../fbrglm/paper/`, including its reviewer reports). The Guide for
  Authors page could not be read (HTTP 403); what only it states is listed
  as not verified.
- Structure: code metadata table (C1–C8); the five mandatory sections;
  validation and examples as subsections of section 3 (reference
  implementations, fold-internal effect, R–Python agreement, public data,
  runtime); limitations as section 4.3; reproducibility and data
  statement; funding and declarations as headings to be completed.
- Build checks (`results/tables/07_manuscript_checks.md`): about 3170 words
  in the main sections (limit 4000), 4 figures (limit 6), abstract 110
  words, 6 keywords, no unresolved citation or reference, 14 references all
  cited. Sections 1–5 with figures and tables end on page 8 of 9.
- 69 values in the text are read from `results/` at build time
  (`results/summary/07_manuscript/numbers.csv`, with the source file of
  each). The build stops if any experiment check has failed.
- Figures: `07_software_overview` (new diagram), `03_fold_internal_effect`,
  `07_examples_importance` (new; Concrete and Breast Cancer from experiment
  C, Maternal Health Risk with group-aware folds from 04b),
  `05_runtime_scaling`. The R–Python agreement is given as a table.
- Multiclass example in the paper: Maternal Health Risk, all rows,
  group-aware folds, with the random-fold and the deduplicated analyses as
  sensitivity analyses and the failed replacement attempt stated.
- The experiment workflows 01–06 and their results were not changed. Added
  to `config/pins.env`: the three `MANUSCRIPT_IMAGE*` entries.

### To be decided or supplied by the author before submission

1. Author list, affiliations, corresponding email (C8), funding,
   competing-interest and generative-AI declarations, acknowledgements.
2. Multiclass example: keep Maternal Health Risk with group-aware folds
   (as drafted) or change it (issue 6).
3. Code version: no release tag and no DOI exist for either package; C2
   names the commits of `config/pins.env`. The R repository has a later
   documentation-only commit (`4632626`).
4. Two GitHub repositories in the metadata table (the template speaks of
   one); license files are not named `Licence.txt`.
5. Page count under the stricter reading of the six-page limit (body with
   figures: 8 pages); `preprint, 3p` versus the template's
   `preprint, 12pt, a4paper`.
6. Everything listed as "Not verified" in
   `docs/softwarex_requirements.md`.
7. The claim in section 4.1 about the purpose of UMFI paraphrases the
   UMFI paper and should be checked against it by the author; the
   manuscript has not been proof-read by a person.

## Open issues

1. **Docker Hub.** The Phase 2 images are on GHCR only. This repository has
   no `DOCKER_USERNAME` / `DOCKER_PASSWORD` secrets (the package repositories
   do); the build workflow skips Docker Hub with a warning. Add the two
   secrets and re-run the workflow if `docker.io/koki/…` copies are wanted
   (`docker/README.md`).
2. **Specification §8.2 pairs non-equivalent forest parameters** (for the
   package maintainers; replacement text in
   `docs/package_change_proposal.md`, not applied). Until decided, the
   Python forest of experiments A–C follows §8.2 as written.
3. **Classification trees differ between ranger and scikit-learn in every
   pairing examined**, also with stopping rules of the same definition. The
   cause was not identified (ties between equally good splits are a
   candidate). Relevant for Phase 3: "aligned" forests do not do equal work.
4. **The forest importances on the null design are positive on average**
   (B6). Investigated in Phase 3 (`docs/null_forest_investigation.md`): the
   mean follows the number of columns and of split candidates of the two
   models and can be positive, zero or negative. A remainder of about two
   standard errors with equal column numbers is unexplained; classification
   and other correlation structures were not examined. The paper must not
   describe forest importances as centred at zero under the null.
5. **The all-rows effect (B5b) was measured with OLS only.** Its size for
   forests or other learners is unknown.
6. **Maternal Health Risk: 562 of 1014 rows repeat an earlier record, and
   the origin of the copies is undocumented** (`docs/maternal_duplicates.md`).
   The Phase 2 forest scores on it must not be quoted. A replacement was
   attempted on 2026-11-14 and none of five candidates met the pre-set
   criteria (`docs/multiclass_dataset_selection.md`); `maternal_grouped`
   is the provisional multiclass example. Open decision for the authors:
   keep it; or adopt Abalone (`Sex`) after amending the agreement rule for
   thresholded metrics; or screen further candidates.
7. **One 5-fold split per data set.** The between-split SD shown is over 5
   splits; repeated CV was not run.
8. **R and Python parse some 6-decimal numbers to doubles that differ in the
   last bit** (1.1e-16). No effect on any tolerance used; exact comparisons
   with raw data are made inside one language.
9. **Disk.** 2026-11-14: `/` 81 % used, 88 GB free (inodes 8 %);
   `~/.singularity/cache` is now a symlink to `/data2`; `.snakemake` 1.3 GB.
   The wrappers still put Singularity's temporary files in `/dev/shm`.
   Copies of the three repositories exist under `/data2/dev/`; work
   continues in `~/dev` until the move is completed by the user.
10. **R and Python do not share a BLAS inside the images** (system OpenBLAS
    0.3.26 vs NumPy's bundled OpenBLAS); to be stated with any timing.
11. **Forest runtime was measured on small cells only** (n ≤ 1000, p ≤ 10,
    v ≤ 5 in both languages): one call takes 7 s to 1.5 min on one thread
    there, and the 2-hour budget excluded everything larger. Runtime with
    several threads was not measured.
12. Parity is checked on full-rank designs only (common specification §8.1).
13. **SoftwareX Guide for Authors not read** (HTTP 403 for automated
    access); templates and an earlier submission were used instead
    (`docs/softwarex_requirements.md`). To be checked in a browser.
14. The checker's own failure modes (tampered value, failed job) were
    verified in the conda-based run of Phase 1 (`6c094a1`), not again since.

15. **Runtime: one machine, one data-generating model, regression with MSE
    only**; the machine was shared (load average up to 2.2 before a timed
    run). The share of residualization in the total time was not measured.

16. **The R–Python agreement check on accuracy is in effect "no row is
    classified differently"** when a fold has fewer than 1000 assessment
    rows (one row weighs more than the tolerance 1e-3). Probabilities that
    agree within 1e-5 can still flip a near-tied row, as seen on Abalone.
    The checks that passed are unaffected; a rule for thresholded metrics
    would be a change of criterion and is left to the authors.

## Next

Author's decisions listed under Phase 4; then proof-reading, a tagged
release of both packages (and a DOI if wanted), and submission files
(cover letter, highlights if required).
