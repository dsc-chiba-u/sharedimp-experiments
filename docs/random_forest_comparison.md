# Random forests in R (ranger) and Python (scikit-learn): what the settings mean

Workflow `workflow/02b_rf_settings.smk`, configuration
`config/02b_rf_settings.json`, results `results/tables/02b_rf_settings.md`
(all numbers below are copied from that table). Versions: ranger 0.18.0
through parsnip 1.5.0, scikit-learn 1.9.1, one thread.

## Why this was examined

The common specification of the two packages (§8.2) describes the built-in
forest learner by one table for both languages, with the row
"`min_n` / `min_samples_leaf` = 5". In Phase 1 the two forests gave very
different importances on a tiny data set. The two parameters do not mean the
same thing.

## What the parameters mean

| | ranger (R) | scikit-learn (Python) |
|---|---|---|
| smallest node that may be split | `min.node.size`: "Minimal node size to split at" (help page). In the source a node is made terminal when `num_samples_node <= min_node_size` (`TreeRegression.cpp`, `TreeProbability.cpp`), so only nodes with **more than** `min.node.size` rows are split. Defaults: 5 regression, 1 classification, 10 probability forest. | `min_samples_split`: "The minimum number of samples required to split an internal node", so nodes with **at least** `min_samples_split` rows are split. Default 2. |
| smallest terminal node | `min.bucket`: "Minimal terminal node size. No nodes smaller than this value can occur." Default 1. | `min_samples_leaf`: a split is considered only if it leaves at least this many training samples in each branch. Default 1. |
| what parsnip's `min_n` sets | `min.node.size` (`translate()` shows `min.node.size = min_rows(~5, x)`); `min.bucket` stays 1 | — |
| split candidates per node | `mtry`, default `floor(sqrt(p))`; the R built-in learner leaves the default | `max_features`; default `1.0` (all features) for the regressor, `"sqrt"` for the classifier; `"sqrt"` is `max(1, int(sqrt(p)))` |
| trees | `num.trees`, default 500; the R built-in learner sets 500 | `n_estimators`, default 100 |
| sampling | `replace = TRUE`, `sample.fraction = 1` | `bootstrap=True`, `max_samples=None` (n draws) |
| split criterion | variance reduction (regression); Gini (classification and probability forests) | `squared_error`; `gini` |
| classification output through parsnip | probability forest (`probability = TRUE`) | `predict_proba` (mean of the trees' class proportions) |
| depth limit | none | none |
| threads through parsnip / default | `num.threads = 1` (set by parsnip) | `n_jobs=None` (1) |

So, by definition:

- `min.node.size = k` corresponds to `min_samples_split = k + 1`, not `k`;
- `min.bucket = k` corresponds to `min_samples_leaf = k`;
- `min_n = 5` (R built-in) and `min_samples_leaf = 5` (Python counterpart in
  §8.2) are different rules: the first allows leaves of one row, the second
  does not allow leaves of fewer than five.

## What was run

Two synthetic data sets (`rf_reg_n300_p5`, `rf_bin_n300_p5`; n = 300, p = 5,
correlated features, an interaction in the response; 240 training rows, one
fold of 60 rows held out).

1. **One deterministic tree per setting**: no bootstrap, every feature a split
   candidate, so that equal rules must give equal trees. Compared: number of
   leaves, depth, predictions on the training rows and on the held-out fold.
   Criterion for "equivalent", fixed in the configuration file: same number
   of leaves, same depth, predictions equal within 1e-8 on both sets.
2. **Counting under bootstrap**: 50 bootstrap trees with a terminal-node
   minimum of 5; the smallest leaf counted in bootstrap draws and in distinct
   training rows.
3. **Forests as used**: 500 trees, bootstrap, sqrt(p) candidates, five seeds;
   leaves and depth per tree, held-out score, and `shared_importance()` with
   5 folds (R: a parsnip specification; Python: the estimator).

## Results

### Single trees

| pair | regression | binary (probability tree) |
|---|---|---|
| `min.node.size = 5` vs `min_samples_split = 5` | 86 vs 102 leaves: not equivalent | 43 vs 44 leaves: not equivalent |
| `min.node.size = 5` vs `min_samples_split = 6` | 86 vs 86 leaves, depth 12 vs 12, training predictions equal (8.9e-16); 93 % of the held-out predictions equal, largest difference 2.58 | 43 vs 43 leaves, depth 12 vs 12; training predictions differ (up to 0.5) |
| `min.node.size = 4` vs `min_samples_split = 5` | 102 vs 102 leaves, depth 13 vs 13, training predictions equal (8.9e-16); 85 % of the held-out predictions equal | 44 vs 44 leaves; training predictions differ |
| `min.bucket = 5` vs `min_samples_leaf = 5` | 36 vs 36 leaves, depth 8 vs 8, all predictions equal (1.8e-15): **equivalent** | 43 vs 27 leaves, depth 20 vs 7: not equivalent |
| specification §8.2 as written (`min.node.size = 5` vs `min_samples_leaf = 5`) | 86 vs 36 leaves; 2 % of the held-out predictions equal | 43 vs 27 leaves |

Reading:

- The "+1" between `min.node.size` and `min_samples_split` is confirmed for
  regression trees: with it, the two trees have the same shape and the same
  fit on the training rows; without it they do not.
- Even then the regression trees are not the same function. On the held-out
  rows 7 % (or 15 %) of the predictions differ. The training partition is
  identical, so the trees must differ in *which* of several equally good
  splits they chose in small nodes (a node of two or three rows can be
  separated by several features). This explanation was not verified split by
  split.
- With a terminal-node minimum of 5 the regression trees are identical on
  both sets.
- For the binary response **no pairing gave equal trees**, including the one
  whose rules have the same definition (43 vs 27 leaves). The root split is
  the same in both implementations and ranger does not split pure nodes
  (both checked by hand, not part of the workflow); the cause of the
  divergence below the root was not identified. Ties between splits with
  equal Gini gain are a candidate, not a finding.

### Counting under bootstrap

| | smallest leaf, in draws | smallest leaf, in distinct rows |
|---|---|---|
| ranger, `min.bucket = 5` | 5 | 1 |
| scikit-learn, `min_samples_leaf = 5` | 5 | 5 |

ranger counts bootstrap draws: a leaf may consist of one training row drawn
five times. scikit-learn's leaves contain at least five distinct rows. A
bootstrap sample of n draws contains about 0.63 n distinct rows, so under
bootstrap the same number is a stricter limit in scikit-learn. The split
threshold was not examined in the same way, but the forests below are
consistent with it being counted likewise: with the "aligned" definitions
scikit-learn still grows smaller trees.

### Forests as used (mean over five seeds)

| data | setting | leaves per tree | depth | held-out score |
|---|---|---|---|---|
| regression | R built-in (`min.node.size = 5`) | 80.5 | 13.3 | MSE 1.085 |
| regression | Python, `min_samples_split = 6` | 53.2 | 11.9 | MSE 1.131 |
| regression | R, `min.bucket = 5` | 37.7 | 9.1 | MSE 1.228 |
| regression | Python as in §8.2 (`min_samples_leaf = 5`) | 24.5 | 7.4 | MSE 1.393 |
| binary | R built-in | 34.3 | 9.7 | log-loss 0.554 |
| binary | Python, `min_samples_split = 6` | 30.1 | 9.4 | log-loss 0.552 |
| binary | R, `min.bucket = 5` | 35.8 | 13.8 | log-loss 0.532 |
| binary | Python as in §8.2 | 19.5 | 6.9 | log-loss 0.525 |

Importance (`shared_importance()`, 5 folds; largest absolute difference of
the seed means over the five features, next to the largest between-seed SD):

| contrast | regression (largest importance 4.45, seed SD ≤ 0.04) | binary (largest importance 0.19, seed SD ≤ 0.008) |
|---|---|---|
| §8.2 as written: R built-in vs Python `min_samples_leaf = 5` | 0.38 | 0.022 |
| split rule aligned: R built-in vs Python `min_samples_split = 6` | 0.05 | 0.008 |
| leaf rule aligned: R `min.bucket = 5` vs Python `min_samples_leaf = 5` | 0.14 | 0.012 |
| within R: `min.node.size = 5` vs `min.bucket = 5` | 0.23 | 0.027 |
| within Python: `min_samples_leaf = 5` vs `min_samples_split = 6` | 0.32 | 0.014 |

The ranking of the five features was the same in every setting and both
languages on these two data sets. With the settings of §8.2 as written the
cross-language difference in importance was about ten times the seed-to-seed
SD on the regression data; with the split rule aligned it was of the size of
the seed-to-seed SD. These are two small synthetic data sets; the sizes of
the differences are not general.

## Conclusions

1. `min_n = 5` (R) and `min_samples_leaf = 5` (Python) are different stopping
   rules. The R forest grows trees about three times as large (80.5 vs 24.5
   leaves here).
2. A scikit-learn setting whose rule has the same *definition* as the R
   built-in learner exists (`min_samples_split = 6`, `min_samples_leaf = 1`),
   and it removes most of the difference in importance on the data examined.
3. It does not make the two forests the same algorithm: node sizes are
   counted in draws by ranger and in distinct rows by scikit-learn, equally
   good splits are resolved differently, and classification trees differed in
   every pairing examined. No setting gives numerically equal forests, and
   none is claimed.

## What this repository does

- **Phase 2 (experiment C).** Forests are language-specific usage examples:
  R built-in `"rand_forest"` against the Python forest of §8.2 as written
  (`python/sharedimp_exp/learners.py`). Their results are reported side by
  side with the settings stated; they are never checked for agreement.
- **Phase 3 (runtime), proposed.** Two comparisons, reported separately:
  (i) *aligned settings* — R built-in against scikit-learn with
  `min_samples_split = 6`, 500 trees, sqrt(q) candidates, bootstrap, one
  thread, with the caveat of conclusion 3 next to the result (tree sizes
  still differ, so the two forests do not do equal work);
  (ii) *customary learners* — each language's forest as a user would call it
  (R built-in; scikit-learn defaults: 100 trees, all features as candidates
  for regression), as a practical comparison.

## Proposal for the packages (not applied; the sibling repositories are read-only here)

The row is in the common specification kept in the R repository
(`sharedimp-r/docs/specification.md`, §8.2). The Python package's
`docs/specification.md` does not repeat it: it refers to §8.2 and states that
stochastic learners cannot be compared numerically across languages, which
agrees with what was found here. Only the R-side document needs a change.
Options, in order of preference:

1. **Reword §8.2 (documentation only, no change of behaviour).** Replace the
   row "`min_n` / `min_samples_leaf` = 5" by: R `min_n = 5`, i.e. ranger
   `min.node.size = 5`: nodes with more than 5 in-bag draws are split,
   terminal nodes may hold a single row; closest scikit-learn setting
   `min_samples_split = 6`, `min_samples_leaf = 1`. Add that node sizes are
   counted in bootstrap draws by ranger and in distinct rows by scikit-learn,
   so the settings are not equivalent, and that "shared across languages"
   refers to the definition, not to the fitted trees. The R built-in learner
   and every R result stay as they are. Python has no built-in forest, so
   nothing changes in the Python package; in this repository
   `python/sharedimp_exp/learners.py` would follow the new wording.
2. **Change the R built-in learner to a terminal-node minimum**
   (`set_engine("ranger", min.bucket = 5)` with a small `min_n`). This
   matches the Python counterpart as written and gave identical single
   regression trees here, but it changes the default learner of the R
   package and every forest result produced with it, and classification
   trees still differed.
3. **Leave §8.2 and state only that the row pairs non-equivalent
   parameters.** Smallest change; keeps a table that reads as if the settings
   were the same.

In addition, §8.2 gives `mtry` as `floor(sqrt(q))`; the R built-in learner
does not set `mtry` and relies on ranger's default, which is the same value.
That is consistent, but worth stating, because scikit-learn's regressor
default is all features and must be set to `"sqrt"` explicitly.
