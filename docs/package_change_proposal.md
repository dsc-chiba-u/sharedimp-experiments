# Proposed change to the common specification, §8.2 (random forest)

Status: **proposal, not applied.** The package repositories are read-only
from here; nothing in `../sharedimp-r` or `../sharedimp-py` was changed.
Evidence: `docs/random_forest_comparison.md` and
`results/tables/02b_rf_settings.md` (workflow `02b_rf_settings`).

## What is wrong

`sharedimp-r/docs/specification.md`, §8.2, describes the built-in forest by
one table "with fixed hyperparameters shared across languages" and contains
the row

```
| min_n / min_samples_leaf | 5 |
```

The two names in that row are different stopping rules:

| | rule | smallest terminal node |
|---|---|---|
| R: `min_n = 5` → ranger `min.node.size = 5` | a node is split only if it holds **more than 5** rows (in-bag draws) | 1 |
| Python: `min_samples_leaf = 5` | a split must leave **at least 5** rows (distinct training rows) on each side | 5 |

Measured (`results/tables/02b_rf_settings.md`): with the row as written the
R forest grows trees about three times as large as the Python forest (80.5
vs 24.5 leaves per tree on the regression data), and the importances of the
two languages differ by up to 0.38 where the seed-to-seed SD is at most 0.04.

The R package implements `min_n = 5` (`R/learners.R`, `builtin_rand_forest()`);
the Python package has no built-in forest, so the row has no implementation
on the Python side and only says what a Python user should pass to obtain
"the same" learner. That advice is what is wrong.

## Recommended change: documentation only

No code changes, no change of any result of either package.

### 1. `sharedimp-r/docs/specification.md`, §8.2 — replace the table and the paragraph after it

Current text:

```
Random forest with fixed hyperparameters shared across languages:

| parameter | value |
|---|---|
| trees | 500 |
| mtry / max_features | `floor(sqrt(q))`, `q` = number of representation columns |
| min_n / min_samples_leaf | 5 |
| classification output | class probabilities |
| bootstrap | yes, sample fraction 1 |

R engine: `ranger` through `parsnip::rand_forest()`. Python: scikit-learn
`RandomForestRegressor` / `RandomForestClassifier`. Forest implementations
differ between languages; cross-language equality is **not** expected for this
learner, only qualitative agreement. [...]
```

Proposed text:

```
Random forest with fixed hyperparameters. The built-in learner exists in R
only; the last column gives the scikit-learn settings whose definitions are
closest to it. The two forests are **not equivalent** (see below).

| parameter | R built-in (`ranger` through `parsnip::rand_forest()`) | closest scikit-learn setting |
|---|---|---|
| trees | `trees = 500` | `n_estimators=500` |
| split candidates | ranger default `mtry = floor(sqrt(q))`, `q` = number of representation columns | `max_features="sqrt"` (must be set for the regressor, whose default is all columns) |
| node size | `min_n = 5`, i.e. ranger `min.node.size = 5`: a node with more than 5 rows is split; terminal nodes may hold a single row (`min.bucket = 1`) | `min_samples_split=6`, `min_samples_leaf=1` |
| classification output | class probabilities (probability forest) | `predict_proba` |
| sampling | bootstrap, sample fraction 1 | `bootstrap=True` |
| threads | 1 (set by parsnip) | `n_jobs=1` |

Not equivalent, even with these settings:

- `min.node.size = k` in ranger corresponds to `min_samples_split = k + 1`
  in scikit-learn (ranger stops at node size `<= k`), not to
  `min_samples_split = k` and not to `min_samples_leaf = k`.
  `min_samples_leaf = k` corresponds to ranger's `min.bucket = k`.
- Under bootstrap sampling ranger counts node sizes in in-bag draws,
  scikit-learn in distinct training rows, so the same number is a stricter
  limit in scikit-learn and its trees are smaller.
- Ties between equally good splits are resolved differently; single
  classification trees differed in every pairing examined, including
  stopping rules of the same definition.

Cross-language equality is therefore **not** expected for this learner and
is never tested; "closest setting" refers to the definition of the
parameters, not to the fitted trees. Evidence: sharedimp-experiments,
`docs/random_forest_comparison.md`.
```

The sentence about exactly-zero columns that follows in §8.2 stays as it is.

### 2. Optional, for consistency (same repository)

- `R/learners.R` (roxygen of `sharedimp_learner`, line 14) and
  `man/sharedimp_learner.Rd`: after "`min_n = 5`" add
  "(ranger `min.node.size`: nodes with more than 5 rows are split)".
- `vignettes/sharedimp.Rmd`, line 81: the same parenthesis.
- §12, row "learner": no change needed.

### 3. `sharedimp-py`

No change required. `docs/specification.md` (line 260) already states that
stochastic learners cannot be compared numerically across languages and
refers to §8.2. If the Python documentation ever shows a forest "like the R
default", it should use `min_samples_split=6, min_samples_leaf=1,
max_features="sqrt", n_estimators=500`.

## Alternatives considered

| option | effect | why not recommended |
|---|---|---|
| Change the R built-in learner to a terminal-node minimum (`set_engine("ranger", min.bucket = 5)`) so that it matches `min_samples_leaf = 5` | single regression trees become identical (`results/tables/02b_rf_settings.md`) | changes the default learner of the R package and every forest result produced with it; classification trees still differ; the bootstrap counting still differs |
| Leave the table, add a footnote that the row pairs non-equivalent parameters | smallest edit | keeps a table that reads as if the settings were the same |
| Remove the Python column altogether | nothing wrong remains | users lose the pointer to the closest setting, which removes most of the difference in importance on the data examined (0.38 → 0.05) |

## What this repository does meanwhile

- Phase 2 results are kept as they were run: the Python forest of
  experiments A–C follows §8.2 as written (`min_samples_leaf = 5`;
  `python/sharedimp_exp/learners.py`). They are labelled language-specific
  and are never checked for agreement.
- Phase 3 (runtime) names its forest settings explicitly in
  `config/05_runtime.json`: "aligned" (`min_samples_split=6`,
  `min_samples_leaf=1`, 500 trees, `max_features="sqrt"`) and "customary"
  (scikit-learn defaults), each against the R built-in learner.
- If §8.2 is changed as proposed, `python/sharedimp_exp/learners.py` should
  follow in a separate commit, with a re-run of workflows 01, 02, 03 and 04
  (their forest rows are report-only, so no check depends on it).
