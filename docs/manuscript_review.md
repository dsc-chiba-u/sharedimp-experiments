# Review of the manuscript (second pass, 2026-11-14)

Scope: `paper/manuscript.Rmd` after the first draft (commit `cb3c8de`), read
as a statistics / machine-learning reviewer for SoftwareX would read it.
Every claim was compared with (a) the UMFI article, (b) the recorded results
under `results/`, (c) the common specification and the package sources.
No experiment was run or re-run for this review; workflows 01–06 and their
results are unchanged. Only workflow 07 (paper figures, PDF, checks) was
re-run.

Sources read for (a): the PDF of Janssen, Guan and Robeva (2023),
`https://proceedings.mlr.press/v206/janssen23a/janssen23a.pdf`, downloaded
on 2026-11-14 and read as text (abstract, Definition 2, Algorithm 1,
Section 4, Supplements A.2, E.2 and F); the proceedings page of Catav et al.
(2021), `https://proceedings.mlr.press/v139/catav21a.html` (bibliographic
data only).

## 1. Claims, evidence, and what was changed

### 1.1 Definition of UMFI-LR

| claim in the manuscript | evidence | finding and change |
|---|---|---|
| UMFI of `x_i` is `ν(S_i ∪ {x_i}) − ν(S_i)`, `S_i` being the other features with the dependence on `x_i` removed | article, Definition 2, eq. (5) | first draft gave the definition in words only; the formula is now in section 1 |
| the definition is a framework (any dependence removal, any evaluation function) | article, after Definition 2 and Algorithm 1 ("can be applied using any pair of preprocessing functions and evaluation functions") | **was missing.** The first draft could be read as if a fixed forest were part of the method. It is a choice of the experiments and of the reference code; the text now says so |
| UMFI-LR: each other feature is replaced by the residual of its simple regression on the anchor | article, Supplement E.2 | correct; kept |
| relation to conditional importance: conditional measures give no credit for shared information, UMFI and MCI count it | article, introduction and Supplement A.2 | first draft opposed UMFI to conditional importance only; MCI, which UMFI is built on, was not mentioned. Added with a verified reference (`catav2021marginal`) |
| Full = anchor + residuals, Reduced = residuals; importance = score(Full) − score(Reduced) on the assessment rows | specification §5, §6, §9 | correct; now written as two display equations with the rows on which each quantity is computed |
| with a linear learner the Full score is the same for every anchor | affine invariance (argument, `docs/experiment_plan.md`); observed: largest range over anchors 1.8e-15 in the least-squares examples (`results/summary/04_real_data/performance.csv`) | added, labelled as a consequence of the definition |
| with least squares and squared error the importance estimates the variance explained by the anchor alone | same argument; closed form used as the target of experiment B5b | added, labelled as a consequence of the definition, not a finding. It tells the reader that UMFI-LR with a linear learner is a marginal measure |
| importances are predictive gains, not causal or conditional effects; no intervals or tests | specification §1 | kept in sections 1 and 4.4. The article's title speaks of "causal guarantees"; the manuscript does not repeat or rely on them (see 1.6) |

### 1.2 What is existing, what is new, what was observed

Section 1 now separates four things, as the reviewers of the earlier
submission asked for comparable software:

- existing method: UMFI and UMFI-LR (article);
- choices of the reference code (all-rows regression, out-of-bag forest
  score, dependence test, floors, global generator): read from the source
  at fixed commits, table "B7" of `results/tables/03_official_umfi.md`;
- what `sharedimp` implements differently: items (i)–(v) of section 1 and
  Table 2;
- what was observed in executed experiments: section 3 only.

Removed or reworded: "the same analysis gives the same numbers in both
languages" (now "are checked against each other", with the conditions in
section 3.3); "The contribution is engineering" kept. No sentence says that
`sharedimp` is better than the reference code.

### 1.3 Comparison with the reference implementations (experiment B)

| claim | evidence (`results/tables/03_official_umfi.md`) | finding and change |
|---|---|---|
| residual columns agree where the reference test passes | B1: 18 (R) and 22 (Python) feature pairs, ≤ 4.7e-15 | correct |
| the two reference codes use different tests and disagree on some pairs | B1 / B7 | correct |
| importance equal under a constructed identical condition | B3: difference 0 on the all-gates data set, up to 0.029 otherwise | correct; the wording "equals" is tied to "same seed and order of fits" |
| **new:** on the four designs of the reference Python code, reference and `sharedimp` forest importances are close (≤ 0.023 in R²) | B4, `importance_by_design.csv` | **was missing.** The first draft reported only differences. Without this sentence the section suggested that the procedures give different answers in general, which the data do not show at n = 500 |
| reference importances are exactly 0 under a null response; `sharedimp` least squares gives a slightly negative mean | B6 | correct |
| Table 2 | B7, every cell with a source line or a check | two rows added so that what the reference code offers and `sharedimp` does not is complete: repeated runs (Python `niter`), parallel function (R `umfi_par`); optimal transport was already there |
| the dependence test is part of the published method's implementation | article, Supplement F ("we only remove dependencies when the regression slope coefficient is statistically significant (p-value < 0.01)") | noted here; the manuscript describes the test neutrally as a property of the reference code and no longer presents its absence as an unqualified improvement (see 1.4) |

### 1.4 Fold-internal residualization (experiment B5b)

Three problems in the first draft.

1. **The experiment is not a measurement of the reference code.** It
   compares residualization on the training rows with residualization on
   all rows *inside the same cross-validation*. The reference code scores
   out of bag. The first draft's Impact section ("Three behaviours differ
   from the reference implementations and are documented with executed
   comparisons. Estimating the residualization on all rows inflated
   importances…") let the reader attribute the 34 % to the reference
   implementation. Now stated explicitly in section 3.2, and the Impact
   section refers to "the cross-validated importances in our simulation".
   Whether out-of-bag scoring with all-rows preprocessing is optimistic was
   not measured.
2. **"the fold-internal values stay near the population values" was too
   strong.** The fold-internal means deviate by up to 18 % (features with a
   large-sample value of about 1, n = 60; about 2.5 Monte Carlo standard
   errors). Replaced by the number, and the figure now shows ± 2 Monte
   Carlo standard errors. "Population value" is called "large-sample
   value": it is the limit, not the expectation at finite n.
3. **An unfavourable result was in the data but not in the text.** For the
   feature unrelated to the response and to the other features (`x4`),
   residualizing unconditionally gives a positive mean importance in small
   samples (0.19 at n = 30, 0.04 at n = 120, 0.003 at n = 2000; large-sample
   value 0), and the preprocessing of the reference R package, with its
   dependence test, does not (−0.05 at n = 30, about 0 from n = 60;
   column `all_rows_official_gate` of `leak.csv`). Explanation (argument,
   consistent with the numbers: importance × training size ≈ 4 at every n):
   slopes that are zero in the population are estimated with error, the
   Reduced representation therefore lacks a part of the informative
   features proportional to the anchor, and the Full model recovers it.
   This is a cost of design decision "always residualize". It is now
   reported in section 3.2, shown in Figure 2 (third curve) and listed
   under Limitations. The same column shows that the reference
   preprocessing also reduces the all-rows inflation (19 % instead of 34 %
   at n = 30); reported as well.

### 1.5 R–Python agreement

| claim | evidence | finding and change |
|---|---|---|
| least squares: rounding level; logistic and multinomial: below 1e-6 and 1e-3 | `parity.csv` of workflows 01, 02, 04, 04b: 5 / 4 / 7 analyses, largest differences 6.2e-15, 2.5e-9, 9.5e-6 | correct; Table 3 header "Largest absolute difference" moved to the caption because the last row is a count |
| restricted to full-rank designs | specification §8.1 and §15.4: on a rank-deficient training design `lm.fit` (aliasing) and a minimum-norm solver predict differently on new rows (1.5e-2 in one recorded cell) | first draft mentioned "full-rank designs" only in the limitations; now in section 3.3 with the reason |
| not claimed for forests | `docs/random_forest_comparison.md` | kept |
| multinomial agreement is limited by the optimisers | different algorithms (`nnet::multinom`, L-BFGS) | stated |
| accuracy can differ by one near-tied row although probabilities agree | workflow 04a, Abalone pilot | kept in the limitations, as an observation on a candidate data set |
| **new sentence:** "a statement about the analyses that were run, not a proof for all inputs" | – | added |

### 1.6 Theoretical guarantees and the sign of the estimates

Definition 2 of the article takes an evaluation function with values in
`R≥0`, and its guarantees (Theorem 3.1) are proved for a Gaussian model and
an evaluation function linearly related to mutual information. The
reference code enforces non-negativity by floors; `sharedimp` reports
signed estimates and admits metrics such as a negated loss. The manuscript
therefore must not suggest that the article's axioms hold for
`sharedimp`'s output. A sentence to that effect was added to the
limitations. The article also reports that linear regression failed to
remove the dependence on a gene-expression data set (Supplement F); cited
in the limitations.

### 1.7 Runtime (experiment D)

| point | finding and change |
|---|---|
| same hardware and conditions | yes (one machine, one thread, same data files and fold columns); now stated. R and Python use different BLAS builds: covered by "linear-algebra libraries of the two environments" |
| equivalent learners | least squares: same statistical work (results equal, check `parity`); forests: "settings have the same definitions but which is not the same learner" added |
| measured time vs complexity | the count 2pv is attributed to the algorithm and to the counting check, the time per fit to the learner; "no order of growth is inferred" kept |
| 59 of 90 | the first draft's text said "59 of 90 conditions" while the figure footer said "42 of 108 cell-language pairs" (the R forest counted in two comparisons). The paper figure is now `07_runtime` (comparisons A and B only) and the text gives one consistent breakdown: 36 of 36 least squares, 14 of 36 forests shown, 9 of 18 scikit-learn default forest (repository only); the range for which forest runtime is known is stated in the same paragraph |
| generalisation | "do not rank the languages" kept; the change of sign of the ratio along n is now given with numbers (n = 32000) so that the reader sees why |

### 1.8 Impact

Rewritten. The first draft repeated the list of features of section 1 and
contained the misattribution of 1.4. The section now has four parts: what
was difficult with the reference code and is an argument now (validation
design, with the Maternal example as the executed illustration; model class
and loss; sign and spread); research questions and settings; reproducible
analyses in two languages; limitations. Statements about use are limited to
what the interface accepts; "we make no claim about their adoption" is in
the text. Not executed and therefore worded as capability only: penalized
regression, boosting, pipelines (the experiments used least squares,
logistic models and forests).

### 1.9 Maternal Health Risk

Kept as the provisional main multiclass example with group-aware folds, as
instructed. The text now says, in this order: 452 distinct records among
1014 rows; origin of the repeated rows unknown; random folds put the
feature values of 807 assessment rows into the training rows and the
performance estimate is optimistic for a learner that can memorize rows
(forest log-loss 0.443 against 0.787 for the multinomial model); group-aware
folds, which need no assumption (0.794 against 0.804); deduplicated
analysis as sensitivity analysis, appropriate only if the rows are copies;
"an illustration of the software, not a clinical analysis". No new search
for data sets was made. Abalone is not named in the manuscript; see
section 3 below.

## 2. Figures and tables

All four figures are now drawn 6.5 in wide (the width of the text block) and
included unscaled; in the first draft they were drawn 7.5–9.4 in wide and
shrunk, which put the lettering at 5–6 pt.

| item | finding | change |
|---|---|---|
| Figure 1 (overview) | lettering about 4.7 pt after scaling; the "specification" box was not connected to anything; inputs were one box | redrawn (`R/figure_overview.R`): the four inputs with the objects that carry them in each package, arrows to the step that uses each, the loop, the result, and the specification attached to the computation |
| Figure 2 (fold-internal) | no uncertainty shown; the reference preprocessing, present in the data, not shown; title "population value" | paper version `07_fold_internal_effect` (`R/figure_paper.R`): ± 2 Monte Carlo SE for the fold-internal means, third curve, large-sample value in each panel title. `03_fold_internal_effect` of workflow 06 is unchanged |
| Figure 3 (examples) | small lettering; panel title "linear / logistic" for a multinomial model | 6.5 in wide; model named in each title; caption says the forests are not expected to agree |
| Figure 4 (runtime) | three rows of which one was not discussed; footer count inconsistent with the text; quartile bars invisible; x axis without the values used | paper version `07_runtime`: comparisons A and B, x-axis breaks at the measured values, no bars (interquartile range is in the text). `05_runtime_scaling` of workflow 06 is unchanged |
| Table 1 (metadata) | C8 and the author items open | unchanged; `nnet` added to C6 (needed by the built-in multinomial model, `Suggests` of the R package) |
| Table 2 (design) | incomplete on what the reference code offers | two rows added |
| Table 3 (validation) | 9 pt too wide (overfull box); header did not fit the last row | column narrowed; header "Observed", explanation in the caption |

Floats: the examples figure was pushed behind the references in the first
build of this revision; float parameters are now set in the preamble and
all floats appear in the section that cites them (pages 3–8).

## 3. Remaining concerns

1. **Abalone and the choice of the multiclass example.** The pilot failed
   on one near-tied row for accuracy, which is not a disagreement of the
   UMFI-LR implementations. Independently of that, predicting `Sex` from
   the physical measurements is a weak example scientifically (the usual
   target of that data set is the number of rings, and infant / female /
   male is not a response the measurements were collected to explain). The
   Maternal example has its own weakness (unknown origin of the repeated
   rows). Both are stated; the decision is the author's (`docs/STATUS.md`,
   item 2).
2. **Unconditional residualization and uninformative features** (1.4,
   point 3). Reported, not solved. Whether the packages should offer the
   dependence test as an option is a design question for the package
   maintainers; nothing was changed in the packages.
3. **Out-of-bag scoring with all-rows preprocessing** was not measured
   against cross-validation at small n. The manuscript makes no claim about
   it.
4. **Single five-fold split per data set** in the examples; no repeated
   cross-validation. Stated in the limitations.
5. **Flexible learners not executed.** See 1.8.
6. **Forest runtime** for n > 1000, p > 10, v > 5: not measured.
7. **Guide for Authors** still not readable by automated requests
   (`docs/softwarex_requirements.md`).
8. The manuscript has been revised by the same assistant that drafted it.
   It has not been proof-read by a person, and the reading of the UMFI
   article above should be confirmed by the author.

## 4. Decisions and facts only the author can supply

| item | state in the manuscript | what is known |
|---|---|---|
| Author list | one author, Koki Tsuyuzaki | `DESCRIPTION` and `CITATION.cff` of both packages name this one author. The earlier submission (`../fbrglm/paper/`) had three; not copied |
| Affiliation | Data Science Core, Chiba University, with a footnote "to be confirmed" | address taken from the earlier submission; that manuscript also carried a second affiliation in a footnote, not copied |
| Corresponding / support email (C8) | `TO BE COMPLETED BY THE AUTHOR` | two candidates exist: the maintainer address in the `DESCRIPTION` of sharedimp-r, and the address used in the earlier submission. Which one to print is the author's choice; none was written into this repository |
| Funding | `TO BE COMPLETED BY THE AUTHOR` | the earlier submission lists grants; whether any of them supported this work cannot be inferred |
| Competing interest | `TO BE COMPLETED BY THE AUTHOR` | the earlier submission used the standard Elsevier sentence ("no known competing financial interests or personal relationships…") |
| Generative-AI declaration | placeholder plus a draft sentence | the draft describes what was actually done in this repository (workflows, drafting and revising the text with Claude Code); the author must confirm the wording and the responsibility statement |
| Acknowledgements | placeholder, optional in the template | none in the earlier submission |
| Release tag, DOI | none | not created in this task, as instructed |
| Multiclass example | Maternal Health Risk, group-aware folds (provisional) | see 3.1 |
| Two repositories in C2, licence file name, page format | see `docs/softwarex_requirements.md` | – |
