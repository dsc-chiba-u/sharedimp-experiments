# Runtime of `shared_importance()` (experiment D)

Workflow `workflow/05_runtime.smk`, configuration `config/05_runtime.json`
(written before the pilot was run), results `results/tables/05_runtime.md`
and `results/tables/05_runtime_checks.md` (every number below is copied from
them), figures `results/figures/05_runtime_scaling` and
`results/figures/05_runtime_learners`. Run on 2026-11-14 at repository
commit `e516acd`.

Two things are kept apart in this document: what the algorithm has to do
(section 2, an argument) and what was measured (section 4). Nothing in
section 4 is used to support an order of growth.

## 1. What was measured, and how

- **Timed region:** one call of `shared_importance()`, elapsed wall-clock
  time (`proc.time()` in R, resolution 1 ms; `time.perf_counter()` in
  Python). Reading the data, building the fold list, starting the process
  and the container are outside it.
- **Per cell:** 1 warm-up call (discarded), 5 timed calls with the same
  seed, garbage collected before each call outside the timed region.
  Reported: median, quartiles and minimum.
- **One thread** (BLAS, OpenMP and learner); one process per language and
  learner; the five processes run one after the other and the workflow runs
  nothing else at the same time. The machine is shared: the largest
  1-minute load average seen before a timed run was 2.20 (32 logical CPUs).
- **Data:** synthetic regression, features with correlation `0.5^|j−k|`,
  `y = 2x1 + x2 − x3 + 0.5·x4·x5 + noise`; one file per (n, p) with one fold
  column per number of folds; both languages verify the sha256
  (`data/runtime/manifest.json`) and use the same fold column. Metric MSE.
- **Cells:** one factor at a time around the base cell n = 1000, p = 10,
  v = 5: n ∈ {125, 250, …, 32000}, p ∈ {5, 10, …, 160}, v ∈ {2, 3, 5, 10,
  20}; 18 candidate cells per learner.
- **Three comparisons, never mixed:**
  A. linear regression: R built-in `"linear"` (`stats::lm.fit`) against
  `LinearRegression()`;
  B. forest, *aligned settings*: R built-in `"rand_forest"` (ranger, 500
  trees, `min.node.size = 5`, `mtry = floor(sqrt(q))`, 1 thread) against
  `RandomForestRegressor(n_estimators=500, min_samples_split=6,
  min_samples_leaf=1, max_features="sqrt", bootstrap=True, n_jobs=1)`: the
  same definitions of the settings, not the same trees
  (`docs/random_forest_comparison.md`);
  C. forest, *customary settings*: the same R forest against
  `RandomForestRegressor()` with scikit-learn's defaults (100 trees, all
  columns as candidates, fully grown trees): what a user gets without
  choosing, not equal work.
- **Environment** (recorded per process, table "Processes"): Intel Xeon
  Gold 6226R; R 4.5.3 with system OpenBLAS 0.3.26, ranger 0.18.0, parsnip
  1.5.0; Python 3.13.18 with scikit-learn 1.9.1, NumPy 2.5.4 and the
  OpenBLAS bundled with NumPy/SciPy; sharedimp 0.1.0 in both, at the commits
  and image digests of `config/pins.env`. R and Python do **not** use the
  same BLAS.

### Pilot and budget

The budget for the main benchmark was 2 hours. A pilot (seven cells, one
timed run each, per process) gave a log-linear prediction of the time of
every candidate cell; this prediction is a planning device only. Rule
(fixed beforehand): a cell costs 6 × its predicted time; a cell above the
per-cell cap is not run and is recorded as `skipped (budget)`; the cap is
the largest value of a fixed list for which the planned total stays within
80 % of the budget. Chosen cap: 600 s per cell; planned total 4964 s.

Result: **59 of the 90 cells were measured, 31 were skipped by the budget
rule**; none failed, none was stopped after its warm-up. The main processes
took 5239 s (criterion ≤ 7200 s); the pilot took a further 1803 s
(`results/raw/05_runtime/pilot/*.meta.json`), and the whole workflow
including container start-up 118 minutes.

| process | cells measured | cells skipped |
|---|---|---|
| R linear, Python linear | 18 each | 0 |
| R `rand_forest` | 7 | 11 |
| Python `rf_aligned` | 7 | 11 |
| Python `rf_customary` | 9 | 9 |

For the forests this leaves n ≤ 1000 (customary: ≤ 2000), p ∈ {5, 10} and
v ∈ {2, 3, 5} (customary: also 10). **The forest runtime for larger n, for
p ≥ 20 and for v ≥ 10 (aligned) was not measured.** The pilot's single runs
at n = 2000, p = 20 and v = 10 are listed in the table "Pilot"; they are
single runs, not benchmark results.

## 2. What the algorithm has to do (not a measurement)

For each of the `p` anchors and each of the `v` splits,
`shared_importance()`

1. residualizes the other `p − 1` features on the anchor with the training
   rows (simple regressions: one pass over the data per feature) and applies
   the coefficients to the assessment rows: O(n·p) per anchor and split,
   **O(v·n·p²)** in total;
2. fits the learner twice (Full representation with `p` columns, Reduced
   with `p − 1`) and predicts the assessment rows: **2·p·v learner fits**
   per call. This count was verified by counting: 30 fits for p = 5, v = 3
   in both languages (check `fit_count`).

The cost of step 2 depends on the learner:

- OLS on `q` columns and `m` training rows costs O(m·q²), so step 2 is
  O(v·n·p³) for the linear learner when the arithmetic dominates, and
  dominates step 1. With small data the fixed cost of a fit and a
  prediction (argument checks, data-frame handling, object construction)
  is what counts, and that cost is proportional to the number of fits,
  2·p·v, not to n.
- For a forest of `T` trees with `c` candidate columns per split a common
  heuristic is O(T·c·m·log m) per fit for balanced trees; it is not a
  bound, and tree size depends on the data and the stopping rule. Step 2
  is then roughly 2·p·v such fits, and step 1 is negligible next to it.

So the number of fits grows linearly in `p` and in `v` by construction, and
the cost of one fit grows with `p` as well (more columns per fit). How the
*time* grows also depends on fixed overheads, memory effects and the
libraries; the measurements below cover too small a range, and for the
forests too few cells, to say more.

## 3. Checks (criteria fixed before the pilot)

All pass (`results/tables/05_runtime_checks.md`): every one of the 90 cells
is measured with 5 timed runs or recorded as skipped with a reason; one data
file and one fold column per cell in both languages; **the linear learner
returned the same importances and scores in R and Python in all 18 cells
(largest difference 1.0e-14, criterion 1e-8)**, i.e. the two timed calls did
the same statistical work; 2·p·v fits per call in both languages; 1 thread
in every process; main processes within 2 h; every process inside its
pinned image; no failed cell. Timings are reported, not judged.

## 4. Measured times

Median seconds per call (5 timed runs). The interquartile range is
at most 2 % of the median in every cell except R linear at n = 32000
(5.5 %); single runs deviate more in the R linear cells with n ≥ 4000
(range of the five runs up to 37 % of the median; `results/summary/05_runtime/cells.csv`).

Base cell (n = 1000, p = 10, v = 5; 100 learner fits):

| | R | Python |
|---|---|---|
| A. linear | 0.184 | 0.305 |
| B. forest, aligned | 58.5 | 88.9 |
| C. forest, customary | 58.5 (the same R runs) | 35.1 |

A. Linear regression:

| sweep | R | Python | Python / R |
|---|---|---|---|
| n = 125 → 32000 (p = 10, v = 5) | 0.165 → 1.48 | 0.285 → 1.16 | 1.73 → 0.78 |
| p = 5 → 160 (n = 1000, v = 5) | 0.087 → 15.4 | 0.146 → 19.3 | 1.67 → 1.25 |
| v = 2 → 20 (n = 1000, p = 10) | 0.074 → 0.738 | 0.123 → 1.21 | 1.66, 1.68, 1.66, 1.63, 1.64 |

- Between n = 125 and n = 1000 the time hardly changes (R 0.165 → 0.184,
  Python 0.285 → 0.305) although the data grow eightfold: in this range the
  call is dominated by costs that do not depend on n. About 1.8 ms (R) and
  3.0 ms (Python) per learner fit, prediction and scoring at the base cell.
- From n = 16000 on the Python call is the faster one (ratio 0.88 and
  0.78). Which part of either call is responsible was not measured; the two
  use different least-squares routines and different BLAS builds.
- In v the time is proportional to the number of fits within the rounding
  of the table (ten times the folds, 10.0 and 9.8 times the time).
- In p the time grows faster than the number of fits: doubling p multiplies
  the R time by 2.1, 2.3, 2.6, 3.3 and 4.2 in turn (5 → 160). The factor is
  still changing at the largest p measured, so no exponent is read from it.

B and C. Forests (cells measured in both languages):

| cell | R built-in | Python aligned | Python customary |
|---|---|---|---|
| n = 125 | 7.46 | 47.3 | 11.4 |
| n = 250 | 13.3 | 53.1 | 14.2 |
| n = 500 | 27.0 | 64.0 | 20.7 |
| n = 1000 (base) | 58.5 | 88.9 | 35.1 |
| p = 5 | 22.7 | 38.1 | 11.8 |
| v = 2 | 15.1 | 28.9 | 9.87 |
| v = 3 | 29.1 | 48.9 | 18.2 |

Python customary only: n = 2000 68.3 s, v = 10 77.5 s.

- One call with a forest learner takes between 7 seconds and 1.5 minutes on
  one thread at these small sizes: two to three orders of magnitude more
  than with the linear learner (base cell: 58.5 s against 0.184 s in R).
  The learner, not sharedimp's own work, determines the runtime.
- Aligned settings: the scikit-learn forest was slower in every measured
  cell, by a factor that falls with n (6.3 at n = 125, 1.5 at n = 1000).
  The Python time at n = 125 (47 s for 100 fits of 500 trees) is consistent
  with a cost per tree that does not depend on n; that was not measured
  separately.
- Customary settings: scikit-learn's default forest (100 trees) was faster
  than the R built-in forest (500 trees) from n = 500 on (ratio 0.77, 0.60)
  and slower at n = 125 (1.52). The two do different amounts of work; the
  comparison says what a user waits for, nothing about the libraries.
- R forest, v sweep: 15.1, 29.1, 58.5 s for 2, 3, 5 folds: more than
  proportional to the number of fits (40, 60, 100), because the training
  share grows with v (1/2, 2/3, 4/5 of the rows) as well.

## 5. What may and may not be said

- May: the number of learner fits per call is 2·p·v (argued and counted);
  for the linear learner, R and Python did the same work in every cell;
  measured times with their conditions; for small data the fixed cost per
  fit dominates the linear learner; with a forest the learner dominates.
- May not: "R is faster than Python" or the reverse. The ratio changes sign
  within the n sweep of the linear learner, and every ratio includes the
  learner implementation, the BLAS build and the framework around the
  learner (parsnip and yardstick; scikit-learn).
- May not: an order of growth in n or p from these times (overhead-dominated
  at the small end, at most nine values per factor, one data-generating
  model, one machine).
- May not: anything about forests beyond the cells in the table; in
  particular nothing about large n or p.
- Not measured: several threads, classification, other metrics, memory use,
  the share of residualization in the total time, repeated CV.
