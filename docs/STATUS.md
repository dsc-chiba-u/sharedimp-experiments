# Status and open issues

Last updated: 2026-11-13 (Phase 1 re-run inside containers with
Snakemake + Singularity). Plan: `docs/experiment_plan.md`.
Numbers quoted here are copied from generated files, which are authoritative;
the file is named next to each number.

## Phase 1 — done

Environment (`results/tables/01_environment.md`): host Ubuntu 22.04.5, Intel
Xeon Gold 6226R (16 cores / 32 threads), 1 thread per process; Snakemake
8.10.0 driving Singularity 3.8.6. Every job ran inside the published package
images, referenced by digest: `ghcr.io/dsc-chiba-u/sharedimp-r` (tag
`cf2e1cc`; Ubuntu 24.04, R 4.5.3, OpenBLAS 0.3.26) and
`ghcr.io/dsc-chiba-u/sharedimp-py` (tag `bacc5d8`; Debian 13, Python 3.13.18,
NumPy's bundled OpenBLAS). The registry reports for both digests the pinned
commit as revision label. Nothing is installed on the host besides Snakemake
and Singularity.

Results (`results/tables/01_environment_checks.md`,
`results/tables/02_validation_checks.md`, `results/summary/*/`):

- All 10 jobs ran in both languages; 57 checks pass, 5 are report-only
  (random forest), 0 fail.
- R–Python maximum absolute difference over every numeric column of both
  result tables: OLS 1.3e-15 to 6.2e-15 (criterion 1e-8); binary logistic
  1.9e-10 (1e-6); multinomial 4.3e-6 (1e-3).
- Positive control (OLS, MSE; `results/summary/02_validation/positive_control.csv`):
  importances 4.062, 2.464, 1.091, 0.007, 1.077 for x1..x5 in both languages,
  against the full-sample plug-in 4.059, 2.462, 1.089, 0.008, 1.075 (largest
  relative deviation 0.22 %) and the population values 4, 2.56, 1, 0, 0.990.
- Random forest on the positive control: x1 first and the noise feature near
  zero in both languages; values differ between ranger and scikit-learn as
  expected (not checked).
- The checker was verified to fail on a tampered value and on a failed job,
  and re-running the random-forest jobs reproduced the same values in each
  language (same seed, same thread count). Both verifications were made in
  the earlier conda-based run of the same code (commit `6c094a1`) and were
  not repeated inside the containers.
- The earlier conda-based run (commit `6c094a1`; R and Python with one shared
  OpenBLAS 0.3.34, parsnip 1.6.1 instead of 1.5.0) gave the same check
  results, and the importances quoted above are identical to the digits
  shown.

## Open issues

1. **Docker daemon not accessible to this account** (socket owned by root).
   Solved for *running* images: Singularity pulls and runs them without the
   daemon, and all Phase 1 results come from inside the images. Still open
   for *building* images: the two images defined in `docker/` (official UMFI
   dependencies) have to be built and pushed by someone with Docker access;
   their Dockerfiles have not been built here (see `docker/README.md` for
   what was and was not tested).
2. **R and Python no longer share a BLAS.** Inside the images R uses the
   system OpenBLAS 0.3.26 (pthread) and NumPy/SciPy their bundled OpenBLAS.
   This does not affect the parity results above, but it is one more
   difference to state next to any R-vs-Python timing in experiment D.
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
   control took about 46 s per language with the forest (54 s with four
   jobs running in parallel). The runtime grid of
   experiment D needs a per-cell cap; see the plan, section 6.
6. **Results record the commit of this repository's code** and whether the
   code (everything except `results/`) had uncommitted changes
   (`results/raw/01_environment/host.json`, every `*.meta.json`). For final
   runs: commit the code first, run with `--forceall`, then commit the
   results; the record then shows a clean code commit.
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
and 3. Workflow 03 needs the two images of `docker/` (issue 1). Do not start
large runs before issue 3 has been decided.
