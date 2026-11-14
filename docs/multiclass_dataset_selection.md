# Multiclass data set for experiment C: selection attempt of 2026-11-14

Workflow `workflow/04a_multiclass_selection.smk`; configuration
`config/04a_multiclass_selection.json`, `config/04a_pilot_jobs.json`;
results `results/tables/04a_multiclass_selection.md`,
`results/tables/04a_multiclass_pilot.md`,
`results/tables/04a_multiclass_pilot_checks.md` (every number below is
copied from them). Criteria: `docs/experiment_plan.md`, section 5d,
committed (`a4b5f17`) before any candidate file was downloaded.

## Outcome

**No candidate met all criteria. Experiment C was not changed.** The
group-aware analysis of the Maternal Health Risk data (`maternal_grouped`,
`docs/maternal_duplicates.md`) stays the provisional multiclass example.

UCI Abalone with `Sex` as response passed the eight criteria on the data
(E1–E8) and the log-loss part of the R–Python pilot, and failed the accuracy
part of the pilot (E9) because **one assessment row of 836 is classified
differently in R and Python in one of 40 fitted models**; the existing
tolerance (1e-3) is smaller than the weight of one row in that fold
(1/836 = 0.0012). The tolerance was not changed. Section 5 lists what the
authors can decide.

## 1. Candidates and criteria

| | Abalone (`Sex`) | Vertebral Column | Seeds | Dry Bean | Statlog Vehicle |
|---|---|---|---|---|---|
| UCI dataset, DOI | 1, 10.24432/C55C7W | 212, 10.24432/C5K89B | 236, 10.24432/C5H30K | 602, 10.24432/C50S4B | 149, 10.24432/C5HG6N |
| license (landing page) | CC BY 4.0 | CC BY 4.0 | CC BY 4.0 | CC BY 4.0 | CC BY 4.0 |
| rows, features used | 4177, 7 | 310, 5 (of 6) | 210, 7 | 13611, 16 | 946, 18 (provider's figures) |
| classes | F 1307, I 1342, M 1528 | 60 / 100 / 150 | 70 / 70 / 70 | 7 varieties | 4 types |
| a row is | one abalone | one patient | one wheat kernel | one grain image | one silhouette |
| classification is the documented purpose (P1) | **no** (purpose: age from rings) | yes | yes | yes | yes |
| missing values | 0 | not assessed | 0 | not assessed | not assessed |
| rows sharing a feature vector | 0 | not assessed | 0 | not assessed | not assessed |
| largest absolute feature correlation | 0.987 | 0.598 after the rule of E3 | 0.994 | not assessed | not assessed |
| first failed criterion | **E9** | **E3** | **E8** | **E7** | **E7** |
| reason | accuracy differs by 0.0012 between R and Python (tolerance 1e-3) | pelvic incidence = pelvic tilt + sacral slope holds exactly in the file (largest deviation 1.0e-8), so that column is dropped; no pair of the remaining five features reaches 0.7 | complete separation: training accuracy 1.0000 in four of five training folds | n > 5000 and p > 12 (not downloaded) | p > 12 (not downloaded) |

Criteria are assessed in order and the assessment stops at the first
failure; "not assessed" does not mean "passed".

## 2. Abalone: what the provider documents

- **Source.** UCI Machine Learning Repository, dataset 1; creators Nash,
  Sellers, Talbot, Cawthorn and Ford; donated in 1995 by S. Waugh; data from
  a field study of blacklip abalone in Tasmania (Sea Fisheries Division
  Technical Report 48, 1994). CC BY 4.0. The CSV offered by the repository
  is identical to `abalone.data` of the original archive.
- **Features used.** Seven continuous measurements: length, diameter,
  height, whole weight, shucked weight, viscera weight, shell weight. The
  donor divided them by 200. `Rings` (the documented target) is not used.
- **Classes.** `Sex` has the levels M (1528), F (1307) and I (1342,
  "infant").
- **Missing values.** None in the file; the donor states that examples with
  missing values were removed beforehand.
- **Duplicates.** No two rows have the same seven measurements (0 of 4177),
  so no identical records either.
- **Oddities, kept as distributed.** Two rows have height 0 (file lines 1259
  and 3998, both `I`); in the second the shell weight (0.3505) exceeds the
  whole weight (0.134).

## 3. Is `Sex` a sensible response?

- It is **not the purpose of the data set**. The provider describes the
  task as predicting the number of rings; `Sex` is listed as a nominal
  attribute. A web search on 2026-11-14 found tutorials that predict `Sex`,
  but no publication that could be cited for it; the uses listed in
  `abalone.names` classify groups of ring counts.
- The label mixes two things: `I` marks animals whose sex could not be
  determined (immature), M and F are adults. Size separates infants from
  adults fairly well and M from F hardly at all. Cross-validated
  multinomial logistic regression reaches an accuracy of 0.556 (largest
  class 0.366) and a log-loss of 0.868 against 1.096 for the class
  proportions (preference P2: passed). The problem is neither trivial nor
  empty, but a reader should not take it for a biological analysis.
- For the purpose of the paper (the same call in R and Python on correlated
  features, with a probability metric and a class metric) it would do: seven
  strongly correlated size and weight measurements, documented rows, no
  duplicates, three balanced classes, no separation. It would have to be
  introduced as "a three-level label recorded with the measurements", with
  the repurposing stated.

## 4. The pilot (criterion E9)

`linear` learner (unpenalized multinomial logistic regression), log-loss and
accuracy, the prepared file `data/candidates/candidate_abalone.csv` and its
fold column in both languages, checker and tolerance of experiment C. Both
jobs ran in both languages without warnings; nine of ten checks pass.

| metric | largest R–Python difference | tolerance | |
|---|---|---|---|
| log-loss | 2.8e-06 (per-split table), 7.7e-07 (summary table) | 1e-3 | pass |
| accuracy | 0.0012 (per-split table), 0.00035 (summary table) | 1e-3 | **fail** |

What the difference is (scripted: the model was refitted in both languages
on the same exported representation, and reproduces the two job results):

- One model of 40 differs: the Reduced model for the anchor `whole_weight`
  in fold 1 scores 300 of 836 assessment rows in R and 301 in Python.
- `nnet::multinom` reports convergence (code 0). The class probabilities of
  the two fits differ by at most 1.2e-05 over the 836 rows.
- Exactly one row is classified differently. Its two largest class
  probabilities differ by 4.5e-07 in the Python fit and by 1.6e-06 in the R
  fit, in opposite directions.

So the fitted models agree far inside the tolerance, and a thresholded
metric turns a difference of 1e-6 in a probability into 1/836 in the score.
With fewer than 1000 assessment rows per fold, the existing accuracy check
is in effect "no row is classified differently". It held for the Maternal
data (203 rows per fold) and for the smoke test; it did not hold here.
**This is an explanation, not a reason to regard the criterion as met.**

## 5. What can be decided

1. **Keep the criteria as they are** (current state): `maternal_grouped`
   remains the multiclass example, with the duplicates stated in the paper.
2. **Adopt Abalone after amending the agreement rule for thresholded
   metrics**, for all data sets and before re-running anything: for example,
   agreement is asserted on the probability metric (log-loss), and for
   accuracy the number of rows classified differently is reported together
   with their probability margins, each of which must be below the
   tolerance. This is a change of a criterion made after a result was seen,
   so it needs the authors' explicit decision and must be reported as such.
   Abalone's weak point under P1 (repurposed target) stays.
3. **Screen further candidates with the unchanged criteria.** The risk seen
   here is not specific to Abalone: any data set with many assessment rows
   and overlapping classes can contain a near-tie.

The files of the attempt are kept: `data/candidates/` holds the prepared
Abalone file (not used by any experiment), and option 2 would only need the
data set to be added to `config/04_real_data.json` and its job file.
