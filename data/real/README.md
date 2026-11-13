# Real data (experiment C)

Prepared by `python/sharedimp_exp/real_data.py` from the sources listed in
`config/04_real_data.json` (workflow `workflow/04_real_data.smk`). Do not edit
the files; change the configuration or the script and regenerate.

| file | data set | source | license |
|---|---|---|---|
| `concrete.csv` | Concrete Compressive Strength | Yeh, I-C. (1998), UCI Machine Learning Repository, https://doi.org/10.24432/C5PK67 | CC BY 4.0 |
| `wdbc.csv` | Breast Cancer Wisconsin (Diagnostic), the ten "mean" features | Wolberg, W., Mangasarian, O., Street, N., & Street, W. (1993), UCI Machine Learning Repository, https://doi.org/10.24432/C5DW2B | CC BY 4.0 |
| `maternal.csv` | Maternal Health Risk | Ahmed, M. (2020), UCI Machine Learning Repository, https://doi.org/10.24432/C5DP5D | CC BY 4.0 |

The files here are **modified** versions of the originals (CC BY 4.0 requires
saying so): columns selected and renamed, features standardized and rounded
to 6 decimals, class labels with spaces replaced by underscores, a `fold`
column added. `manifest.json` records for every file the source URL, the
sha256 of the downloaded original, the retrieval date, the preprocessing, the
sha256 of the prepared file, and the result of the separation check; data
sets that were prepared but rejected (Palmer penguins: complete separation)
are listed under `rejected` with the reason. The downloaded originals are
kept in `downloads/` (git-ignored).

Selection criteria and decisions: `docs/experiment_plan.md`, section 5.
