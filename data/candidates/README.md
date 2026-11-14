# Candidate data sets (not used by any experiment)

Written by `python/sharedimp_exp/multiclass_selection.py` (workflow
`workflow/04a_multiclass_selection.smk`) for the pilot of criterion E9 of
`docs/experiment_plan.md`, section 5d. A file here passed the criteria on
the data (E1–E8); whether it is used is decided by the pilot, see
`docs/multiclass_dataset_selection.md`. Do not edit the files.

| file | data set | source | license |
|---|---|---|---|
| `candidate_abalone.csv` | Abalone, `Sex` as response, the seven continuous measurements | Nash, W., Sellers, T., Talbot, S., Cawthorn, A., & Ford, W. (1994), UCI Machine Learning Repository, https://doi.org/10.24432/C55C7W | CC BY 4.0 |

The file is a **modified** version of the original: columns selected and
renamed, features standardized and rounded to 6 decimals, a `fold` column
added (`manifest.json` has the checksums and the preprocessing).
