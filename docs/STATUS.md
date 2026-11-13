# Status and open issues

Last updated: 2026-11-13 (end of Phase 1). Plan: `docs/experiment_plan.md`.
Numbers quoted here are copied from generated files, which are authoritative;
the file is named next to each number.

## Phase 1 — done

Environment (`results/tables/01_environment.md`): Ubuntu 22.04.5, Intel Xeon
Gold 6226R (16 cores / 32 threads), 1 thread used; conda env `sharedimp-exp`
with R 4.5.3 and Python 3.13.18 sharing OpenBLAS 0.3.34; sharedimp-r 0.1.0 at
`cf2e1cc`, sharedimp-py 0.1.0 at `bacc5d8`, installed non-editable from
`git archive` snapshots. Not run inside a container.

Results (`results/tables/01_environment_checks.md`,
`results/tables/02_validation_checks.md`, `results/summary/*/`):

- All 10 jobs ran in both languages; 57 checks pass, 5 are report-only
  (random forest), 0 fail.
- R–Python maximum absolute difference over every numeric column of both
  result tables: OLS 1.9e-15 to 6.2e-15 (criterion 1e-8); binary logistic
  1.9e-10 (1e-6); multinomial 4.3e-6 (1e-3).
- Positive control (OLS, MSE; `results/summary/02_validation/positive_control.csv`):
  importances 4.062, 2.464, 1.091, 0.007, 1.077 for x1..x5 in both languages,
  against the full-sample plug-in 4.059, 2.462, 1.089, 0.008, 1.075 (largest
  relative deviation 0.22 %) and the population values 4, 2.56, 1, 0, 0.990.
- Random forest on the positive control: x1 first and the noise feature near
  zero in both languages; values differ between ranger and scikit-learn as
  expected (not checked).
- The checker was verified to fail on a tampered value and on a failed job.
- Re-running the random-forest jobs reproduced the same values in each
  language (same seed, same thread count).

## Open issues

1. **Docker daemon not accessible to this account** (socket owned by root).
   Image tags and digests are recorded through the registry API, and
   `latest` equals the pinned commit for both images on 2026-11-13, but no
   experiment has been run *inside* the images. Needs either access to the
   daemon (docker group or rootless Docker) or a CI job. Until then the paper
   may say that images exist and which commit they contain, not that the
   results were produced in them.
2. **Environment differs from the images.** The conda environment has R 4.5.3
   / Python 3.13 like the images, but its dependency versions are whatever
   conda-forge resolved, not those inside the images, and no lock file is
   committed yet. To do before Phase 2 results are final: export an explicit
   lock (`conda env export` / `conda-lock`) next to `environment.yml`.
3. **Random-forest hyperparameters are not equivalent across languages**
   (for the package maintainers; nothing was changed in the sibling
   repositories). Common specification §8.2 pairs `min_n = 5` (R) with
   `min_samples_leaf = 5` (Python). parsnip passes `min_n` to ranger as
   `min.node.size`, which ranger documents as the minimal node size *to
   split at*; its terminal-node minimum is `min.bucket` (default 1).
   scikit-learn's `min_samples_leaf` is a terminal-node minimum. On the
   n = 20 smoke data the two forests therefore behave very differently
   (importance of x1: 0.176 in R, 0.010 in Python;
   `results/summary/01_environment/importance_long.csv`). The experiment
   runner follows the specification as written. Decide before Phase 3 whether
   the specification should say `min_samples_split` or `min.bucket`, because
   the runtime comparison of the forest learner depends on tree depth.
4. **The built-in R forest learner runs on one thread**: parsnip's
   ranger engine passes `num.threads = 1` and `learner = "rand_forest"` exposes no
   option for it. The benchmark must therefore use one
   thread in Python too (as now) or a user-supplied parsnip spec in R.
5. **scikit-learn forests are slow relative to their size on tiny data**
   (n = 20: about 9 s for 24 forests of 500 trees) and the n = 2000 positive
   control took about 46 s per language with the forest. The runtime grid of
   experiment D needs a per-cell cap; see the plan, section 6.
6. **Results record the parent commit of this repository** with `dirty: true`
   (`results/raw/01_environment/system.json`), because results are committed
   together with the code that produced them. For the final runs: commit the
   code first, run on a clean tree, then commit the results.
7. **Real-data candidates are unverified** (source, license, availability);
   see the plan, section 5.
8. **SoftwareX guide and template not yet checked**; `paper/manuscript.Rmd`
   is a skeleton with provisional section names and has not been built.
9. Parity is checked here on full-rank designs only. Rank-deficient designs
   need an aliasing OLS on the Python side (common specification §8.1); the
   package tests cover them and the experiments avoid exact duplicates unless
   that learner is used.

## Next (Phase 2, not started)

Experiment B (official UMFI-LR) and experiment C (real data), then figures 2
and 3. Do not start large runs before the issues 1–3 have been decided.
