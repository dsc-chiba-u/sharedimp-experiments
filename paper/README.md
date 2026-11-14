# `paper/` — SoftwareX manuscript (Phase 4; reviewed and revised, `docs/manuscript_review.md`)

```
paper/
  manuscript.Rmd    the manuscript (rticles::elsevier_article, journal SoftwareX)
  references.bib    verified entries only (docs/softwarex_requirements.md)
```

Journal requirements and the sources they were taken from:
`docs/softwarex_requirements.md`.

## Build

```sh
bash scripts/07_manuscript.sh      # workflow/07_manuscript.smk
```

writes `paper/manuscript.pdf` and `paper/manuscript.tex` (build products,
git-ignored), the four figures of the paper
(`results/figures/07_software_overview`, `07_fold_internal_effect`,
`07_examples_importance`, `07_runtime`; 6.5 in wide, the width of the text
block),
`results/summary/07_manuscript/numbers.csv` and the checks
(`results/tables/07_manuscript_checks.md`: word count, pages of running
text without figures and tables, sections, number of figures, abstract length, unresolved citations or references, figure
files, bibliography keys).

Environment: the image `ghcr.io/dsc-chiba-u/sharedimp-manuscript`, pinned by
digest in `config/pins.env` and built from `docker/manuscript/Dockerfile`
(R 4.5.3 with knitr, rmarkdown, rticles, bookdown, ggplot2, patchwork,
jsonlite; pandoc; TeX Live from Ubuntu 24.04: `texlive-latex-base`,
`-latex-recommended`, `-latex-extra`, `-fonts-recommended`, `-publishers`
(elsarticle), `-bibtex-extra`, `-science`, `lmodern`). Nothing is downloaded
while building. Without the image: R with the packages above, pandoc, and a
LaTeX installation that has `elsarticle`.

## Rules

- **No number is typed into the text.** Every value is computed in the
  `setup` chunk from files under `results/` (or `config/pins.env`) through
  `num()` / `reg()`, which record the value and its source file;
  `numbers.csv` is that record. The build stops if a check file contains a
  failure or a figure is missing.
- Figures are files of `results/figures/`, written by workflows 06 and 07.
- Text marked `TO BE COMPLETED BY THE AUTHOR` (author details, funding,
  declarations, support email) must not be filled in by guessing.
- The main text is between the markers `MAIN-TEXT-START` and
  `MAIN-TEXT-END`; the word limit (4000) is checked on it.
- Multiclass example: Maternal Health Risk with group-aware folds
  (`docs/maternal_duplicates.md`, `docs/multiclass_dataset_selection.md`).

## Before submission

The list of what the author still has to decide, supply or verify is in
`docs/STATUS.md` ("To be decided or supplied by the author before
submission"), `docs/manuscript_review.md` (sections 3 and 4) and `docs/softwarex_requirements.md` ("Not verified", "Open
points").
