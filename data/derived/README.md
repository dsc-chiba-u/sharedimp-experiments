# Derived data

Files derived from data sets in `data/real/` by a script of this repository.
Do not edit; change the configuration or the script and regenerate.

| file | derived from | how | script |
|---|---|---|---|
| `maternal_grouped.csv` | `data/real/maternal.csv` | all rows; fold labels replaced by group-aware folds (rows with identical features share a fold) | `python/sharedimp_exp/maternal_variants.py`, `config/04b_maternal.json` |
| `maternal_dedup.csv` | `data/real/maternal.csv` | first occurrence of every identical record (features and label); group-aware folds | same |

`manifest.json` has the same format as `data/real/manifest.json` (sha256 of
every file, features, folds) plus the derivation. Both files are modified
versions of *Maternal Health Risk* (Ahmed, M., 2020, UCI Machine Learning
Repository, https://doi.org/10.24432/C5DP5D, CC BY 4.0); see
`data/real/README.md` for the modifications already made there. Background:
`docs/maternal_duplicates.md`.
