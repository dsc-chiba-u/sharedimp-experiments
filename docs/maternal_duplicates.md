# Maternal Health Risk: duplicated rows

Workflow `workflow/04b_maternal.smk`, configuration `config/04b_maternal.json`,
results `results/tables/04b_maternal.md` (every number below is copied from
that table or from `results/tables/04b_maternal_checks.md`), figure
`results/figures/04b_maternal_duplicates`. The data file of experiment C
(`data/real/maternal.csv`) and its results are unchanged.

## What the file contains

Definitions used here: an *identical record* is a set of rows equal in the
six features **and** in the class label; rows with *identical features* are
equal in the six features, whatever the label.

| | |
|---|---|
| rows | 1014 |
| distinct records (features and label) | 452 |
| rows that repeat an earlier record | 562 |
| rows whose record occurs more than once | 866 |
| largest number of copies of one record | 27 |
| distinct feature vectors | 416 |
| rows that repeat an earlier feature vector | 598 |
| feature vectors that carry more than one label | 35 (215 rows; one of them carries all three labels) |

So the "562 duplicated rows" of Phase 2 are rows identical in features and
label. Counting by features only gives 598. In 35 feature vectors the same
measurements are labelled differently (for example one vector occurs 34
times, 27 times as mid risk and 7 times as low risk).

The copies are not spread evenly over the file. Per block of 100 rows in
file order, the number of records not seen before is 97, 60, 59, 64, 63, 59,
47, **3, 0, 0, 0**: the last 300 rows or so consist almost entirely of
records that occur earlier in the file.

The class proportions differ between rows and distinct records: high risk
272 rows / 112 records, low risk 406 / 234, mid risk 336 / 106.

## What is known about the origin

The UCI page of the data set (read on 2026-11-14) says that the data were
collected from hospitals, community clinics and maternal health care
centres in rural Bangladesh through an IoT-based risk monitoring system. It
does not say whether a row is a patient or a measurement, has no patient
identifier, and says nothing about duplicates, repeated measurements or
resampling. It states 1013 instances; the file has 1014 rows. How the risk
level was assigned is not stated either.

Therefore it **cannot be decided from the documentation** whether equal rows
are (a) different women with equal measurements, (b) repeated records of the
same woman, or (c) copies added when the file was assembled. What speaks
against (a) as the only explanation is in the file itself: a blood-sugar
value with two decimals, an age and four further measurements coincide for
up to 27 rows, and the last third of the file adds no new record. This is
an inference from the file, not a documented fact.

## Why it matters

With the random stratified folds of experiment C, 807 of the 1014 assessment
rows have a feature vector that is also among their training rows (781 with
the same label). A learner that can reproduce single training rows is then
partly scored on rows it has seen.

## What was compared

| file | rows | folds |
|---|---|---|
| `maternal` (experiment C) | 1014 | random, stratified by class |
| `maternal_grouped` | 1014 | group-aware (`StratifiedGroupKFold`): rows with identical features are always in the same fold |
| `maternal_dedup` | 452 (one row per identical record; rows with identical features and different labels are all kept) | group-aware |

The feature values are the same in the three files (standardized once with
all 1014 rows; the learners used are invariant to that). Same learners,
metrics and seed as in experiment C; R and Python use the same fold column.
Checks (all pass): no feature vector in more than one fold of the derived
files; row sets as specified; the separation rule holds; all eight jobs ran
in both languages; multinomial logistic regression agrees between R and
Python (largest difference 9.5e-06 and 3.1e-06, criterion 1e-3).

## Results

Score of the Full model (5 folds):

| learner, metric | language | random folds | group-aware folds | identical records removed |
|---|---|---|---|---|
| multinomial logistic, log-loss | R = Python | 0.787 | 0.804 | 0.781 |
| multinomial logistic, accuracy | R = Python | 0.622 | 0.610 | 0.675 |
| random forest, log-loss | R | 0.443 | 0.794 | 0.696 |
| random forest, log-loss | Python | 0.547 | 0.739 | 0.686 |
| random forest, accuracy | R | 0.834 | 0.642 | 0.725 |
| random forest, accuracy | Python | 0.765 | 0.648 | 0.728 |

- The linear model hardly notices the fold assignment (log-loss 0.787 →
  0.804). The forest does: its log-loss with random folds (0.44 in R, 0.55
  in Python) becomes 0.79 and 0.74 with group-aware folds, about the level
  of the linear model. The advantage of the forest in experiment C was
  produced by rows that occur in training and assessment folds.
- The large difference between the R and the Python forest in experiment C
  (0.443 against 0.547) shrinks with group-aware folds and with identical
  records removed (0.696 against 0.686). This fits the settings: the R
  forest grows larger trees (`docs/random_forest_comparison.md`) and can
  reproduce single rows more closely. It was not examined further.
- Importances, linear model, log-loss: with group-aware folds they are the
  same as in experiment C (largest change 0.003, Spearman correlation
  1.000); with identical records removed they are smaller for most features
  and the order changes below the first place (Spearman 0.771; blood sugar
  first in all three).
- Importances, forest, log-loss: with random folds all are near zero
  (between −0.006 and 0.006 in R, −0.007 and 0.014 in Python); with
  group-aware folds all are positive (0.014 to 0.055 in R, 0.005 to 0.032
  in Python). A model that recognizes a row from its other five features
  loses little when one feature is removed; that reading is consistent with
  the numbers but was not tested separately. The between-split SDs are of
  the size of the importances (table), so the order of the features is not
  established for the forest in any of the three analyses.
- The scores with identical records removed are not comparable with the
  other two columns as "the same analysis without leakage": the sample is a
  different one (452 rows, other class proportions).

## Assessment

- **Random folds on the file as distributed are not a sound basis for
  scores of flexible learners on this data set**, under any reading of the
  duplicates except "independent patients who happen to coincide", which the
  file makes implausible for most of them.
- **Removing identical records is correct only if the copies are not
  observations.** If equal rows are different women (or repeated visits that
  are observations in their own right), removing them discards data and
  changes the class proportions; the documentation does not allow to rule
  that out.
- **Group-aware folds with all rows need no such assumption.** No row is
  dropped, and no feature vector is scored by a model that was trained on
  it. If the copies are artefacts they still act as weights in the fit and
  in the score, which is a limitation of this choice.

## Recommendation

1. If Maternal Health Risk stays in the paper: report the **group-aware
   analysis with all rows** (`maternal_grouped`) as the main result, state
   the duplicates and the missing documentation in one sentence, and give
   the analysis with identical records removed as a sensitivity analysis.
   The R–Python agreement of the linear learner holds in all three analyses,
   which is what the example is for.
2. Preferable for the paper: **replace the multiclass example by a data set
   whose rows are documented observations**, and keep Maternal Health Risk
   in the repository as a documented case. A candidate that has **not been
   prepared or checked here** is UCI Abalone with the three-level variable
   `Sex` as response (4177 rows, eight continuous and strongly correlated
   measurements). Before it could be used, the checks of experiment C would
   have to be run: license and DOI on the provider's page, the separation
   rule (unpenalized multinomial logistic regression must not separate a
   training fold), missing values, and duplicated rows.
3. Either way the Phase 2 result for `maternal` should not be quoted for
   the performance of the forest. `docs/STATUS.md` says so.

The decision between 1 and 2 is the authors'. Until it is taken, experiment
C stays as run and `maternal_grouped` is the analysis this repository
recommends for that data set.
