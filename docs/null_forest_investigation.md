# Random-forest importance when the response is independent of the features

Workflow `workflow/04c_null_forest.smk`, configuration
`config/04c_null_forest.json`, results `results/tables/04c_null_forest.md`
(every number below is copied from that table), figure
`results/figures/04c_null_forest`.

## The observation to be explained

In experiment B6 (response independent of the features, n = 500, p = 5) the
importances of the forest learners were positive on average (+0.015 in R,
+0.009 in Python, in R²), while those of OLS were slightly negative
(`results/tables/03_official_umfi.md`). A reader might expect values
scattered around zero.

## What was done

A small simulation, not a benchmark: 20 data sets per design, features
equicorrelated normal (0.5), `y ~ N(0, 1)` independent of them, 5 folds,
metric MSE, importance = MSE(Reduced) − MSE(Full). Designs: n = 300 with
p = 5 (as in B6) and with p = 4, and n = 1200 with p = 5 for three settings.
Every setting uses the same data, folds and seeds; one thing is changed at a
time from the baseline, which is the forest of B6 in each language (R: the
settings of the built-in learner, ranger called directly; Python:
`min_samples_leaf = 5`). Representations come from the packages. The unit of
replication is the data set; "±" below is the Monte Carlo standard error of
the mean over the 20 data sets. Var(y) = 1, so the numbers are on the scale
of R².

p = 4 was added on purpose: the forests draw `floor(sqrt(q))` candidate
columns per split, which is 2 for the Full model and 2 for the Reduced model
when p = 5 (q = 5 and 4), but 2 and **1** when p = 4 (q = 4 and 3).

## Results

Mean importance (R / Python):

| setting | p = 5, n = 300 | p = 4, n = 300 |
|---|---|---|
| baseline | +0.0136 ± 0.0033 / +0.0075 ± 0.0021 | +0.0024 ± 0.0049 / −0.0051 ± 0.0040 |
| Reduced model draws as many candidates as the Full model | same setting as the baseline | +0.0287 ± 0.0049 / +0.0179 ± 0.0044 |
| all columns are candidates | +0.0089 ± 0.0034 / +0.0026 ± 0.0022 | +0.0247 ± 0.0053 / +0.0106 ± 0.0049 |
| one candidate | +0.0118 ± 0.0026 / +0.0052 ± 0.0015 | +0.0251 ± 0.0045 / +0.0148 ± 0.0035 |
| depth at most 2 | +0.0022 ± 0.0010 / +0.0018 ± 0.0010 | −0.0019 ± 0.0013 / −0.0026 ± 0.0014 |
| large nodes (50) | +0.0032 ± 0.0015 / +0.0009 ± 0.0005 | −0.0037 ± 0.0024 / −0.0015 ± 0.0008 |
| no bootstrap | +0.0466 ± 0.0053 / +0.0253 ± 0.0033 | −0.0304 ± 0.0076 / −0.0292 ± 0.0068 |
| 50 trees | +0.0129 ± 0.0037 / +0.0075 ± 0.0026 | −0.0030 ± 0.0057 / −0.0043 ± 0.0048 |
| 2000 trees | +0.0139 ± 0.0030 / +0.0070 ± 0.0021 | +0.0040 ± 0.0051 / −0.0058 ± 0.0039 |
| Reduced model padded with a noise column (equal number of columns) | +0.0015 ± 0.0061 / +0.0003 ± 0.0049 | +0.0114 ± 0.0063 / +0.0102 ± 0.0039 |
| Full model = Reduced + a noise column (anchor not used) | +0.0131 ± 0.0050 / +0.0064 ± 0.0041 | −0.0088 ± 0.0062 / −0.0157 ± 0.0046 |
| scikit-learn, `min_samples_split = 6` | – / +0.0123 ± 0.0027 | – / +0.0010 ± 0.0049 |
| OLS | −0.0046 ± 0.0013 (both) | −0.0026 ± 0.0010 (both) |

n = 1200, p = 5: baseline +0.0149 ± 0.0017 / +0.0091 ± 0.0013; padded
Reduced model +0.0040 ± 0.0018 / +0.0035 ± 0.0016; OLS −0.0009 ± 0.0003.

In every forest setting **both** models predict worse than the training mean
(the table's "excess MSE": 0.085 for the Full and 0.099 for the Reduced
model in the R baseline with p = 5). The importance is the difference of two
amounts of overfitting.

## Reading, factor by factor

1. **Number of columns of the Full and the Reduced model: yes, this is the
   main ingredient for p = 5.** Giving the Reduced model one more column of
   pure noise, so that both models have five, removes most of the positive
   mean (R: 0.0136 → 0.0015; Python: 0.0075 → 0.0003; with n = 1200:
   0.0149 → 0.0040 and 0.0091 → 0.0035). Replacing the anchor in the Full
   model by pure noise leaves it as it was (0.0131 against 0.0136;
   0.0064 against 0.0075): a column without any information earns the same
   "importance" as the anchor. The positive mean is therefore not something
   the anchor contributes; with a fixed number of candidates per split, a
   forest on five noise columns overfits a little less than a forest on
   four.
2. **Candidates per split (`mtry` / `max_features`): yes, and it can cancel
   or reverse the effect.** With p = 4 the Reduced model draws one candidate
   of three and the Full model two of four; the baseline mean is then about
   zero (+0.0024 / −0.0051). Forcing the same number of candidates in both
   models brings the positive mean back (+0.0287 / +0.0179), as do "all
   columns" and "one candidate", in which the two models are treated alike.
   So whether the null importance of the built-in forest is positive, zero
   or negative depends on how `floor(sqrt(q))` happens to fall for q = p and
   q = p − 1. For the same reason the padded and the noise-anchor settings
   of p = 4 change two things at once (the column count and, through it, the
   number of candidates of one model) and are not a clean test there.
3. **Tree depth: the size of the effect follows the amount of
   overfitting.** With depth ≤ 2 or nodes of 50 the excess MSE of both
   models is several times smaller and the mean importance is within about
   0.004 of zero in every cell.
4. **Bootstrap sampling: not the cause; it damps the effect.** Without
   bootstrap, trees differ only through the candidate draws, and the
   difference between the two models is larger, in the direction given by
   the candidates: +0.047 / +0.025 for p = 5 (about three times the
   baseline), −0.030 / −0.029 for p = 4 (baseline about zero).
5. **Variance of the learner (number of trees): no.** 50, 500 and 2000 trees
   give the same mean (0.0129, 0.0136, 0.0139 in R; 0.0075, 0.0075, 0.0070
   in Python for p = 5). More trees do not move the mean towards zero.
6. **Finite assessment sample: no.** With four times the rows the mean is
   unchanged (0.0149 against 0.0136 in R; 0.0091 against 0.0075 in Python)
   and its standard error halves; all 20 data sets have a positive mean. The
   positive value is a property of the pair of learners being compared, not
   noise of the evaluation.
7. **OLS for comparison.** The Full model estimates one coefficient more
   than the Reduced model, which costs about σ²/n_train on new data
   (1/240 = 0.0042 and 1/960 = 0.0010 here); the simulation gives −0.0046
   and −0.0009. For OLS the null importance is slightly negative for a known
   reason; for the forests examined it is the sign that depends on the
   settings.

An interpretation that fits all rows, but which was **not measured
directly** (the correlation between trees was not computed): under a null
design the error of a forest beyond Var(y) is the variance of its
predictions; whatever makes the trees more different from each other (more
columns to choose from, fewer candidates per split) lowers it. The Full
model has one more column, the Reduced model sometimes one candidate fewer.

## What is not settled

- With equal numbers of columns a remainder of +0.004 to +0.011 is left in
  four of the six cells (p = 4 and n = 1200), about two standard errors
  each; the same 20 data sets and noise columns are used in both languages,
  so these are not independent confirmations. Twenty data sets cannot
  decide whether an anchor and an independent noise column are exactly
  exchangeable here.
- One correlation structure, one noise level, regression with MSE only; no
  classification; p = 4 and 5 only. The sizes above are not general.
- Nothing was done about the effect: the packages were not changed and no
  correction is proposed.

## Consequences for the paper and the documentation

- Do not write that importances near zero are "centred at zero" for a
  forest, or that a positive value of the size seen here indicates
  information. Under a null design the built-in forest gave about +0.01 in
  R² with p = 5 in two independent simulations (B6 and this one), around
  zero with p = 4.
- Do not write that a forest importance cannot be negative or must be
  negative under the null either: both signs occurred, depending on
  settings that have nothing to do with the data.
- This is a property of comparing two fitted learners with different inputs,
  i.e. of UMFI-LR with a forest, in both implementations; it is not specific
  to sharedimp and is not presented as a finding about the method beyond
  this description.
- A user who needs a reference level for "no information" can obtain it the
  way it was done here (a column of noise in place of the anchor); whether
  the packages should offer that is a design question outside this
  repository.
