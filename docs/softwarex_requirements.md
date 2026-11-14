# SoftwareX: requirements used for the manuscript

Checked on **2026-11-14**. Three kinds of sources, marked in every row:

- **[T]** the journal's current templates, downloaded and read in full:
  `https://legacyfileshare.elsevier.com/promis_misc/softwarex-osp-template.tex`
  (Last-Modified 17 April 2026) and
  `https://legacyfileshare.elsevier.com/promis_misc/softwarex-osp-template.docx`
  ("SoftwareX article template Version 6 (March 2026)"); for comparison the
  software-update templates at the same location.
- **[P]** practice of an earlier submission of the same author to the same
  journal (manuscript SOFTX-D-26-00949, `../fbrglm/paper/`: manuscript
  source, reviewer reports of October 2026, response letter, submission
  checklist). Evidence of what was accepted for review and of what reviewers
  asked for, not a statement of the rules.
- **[D]** the DOAJ record of the journal
  (`https://doaj.org/api/search/journals/issn%3A2352-7110`, updated
  2026-09-17).

**Not read: the Guide for Authors itself.**
`https://www.sciencedirect.com/journal/softwarex/publish/guide-for-authors`
(and the elsevier.com address that redirects to it) answered HTTP 403 to
automated requests. Everything that only the Guide states is listed under
"Not verified" below and must be checked in a browser before submission.
Nothing in this file is filled in from memory.

## Scope and what reviewers weigh

- [T] Two article types with separate templates: *Original Software
  Publication* (this manuscript) and *Software Update*.
- [T] "We will only consider software articles submitted using this
  template. Any submission that deviates widely will likely face desk
  rejection."
- [T] On section 4, Impact: "This is the main section of the article and
  reviewers will weight it appropriately."
- [T] "Please focus your paper on the software and place supporting
  information into your GitHub repository README.md file."
- [P] The two reviewers of SOFTX-D-26-00949 asked for: a comparison table
  with existing software; a concise table of validation results with the
  numerical criteria; claims of equality scoped to the conditions under
  which they were verified (a "bit-identical" claim had to be withdrawn);
  runtime with hardware, versions, repetitions and variability;
  installation example and instructions to reproduce; a limitations
  subsection; description of tests, tolerances, seeds and environment. The
  present manuscript contains each of these (Tables 2 and 3, sections 2.3,
  3.5 and 4.3, the reproducibility statement).

## Requirements

| item | requirement | source | in the manuscript |
|---|---|---|---|
| Sections | five mandatory main sections, in this order: 1 Motivation and significance; 2 Software description (Software architecture; Software functionalities; Sample code snippets analysis, optional); 3 Illustrative examples; 4 Impact; 5 Conclusions. "Your paper will be returned or rejected if these are missing." | T | as required; the requested extra topics are subsections (validation in 3.1–3.3, limitations in 4.3) |
| Front matter | title "Name of your software: then a short title"; authors with affiliations, addresses, email; abstract; keywords | T | yes; author block to be confirmed |
| Abstract | "ca. 100 words" | T | 111 words (workflow 07 check) |
| Keywords | maximum of six | T (Word template) | six |
| Length | main text (sections 1–5) "maximum six (6) pages in total (excluding metadata, tables, figures, references) with a 4000-word limit (we ask that more priority is placed on the word limit versus the page count)" | T | 3249 words (check `main_text_words`); **6 pages** from the title to the end of section 5 when figures and tables are removed (check `text_only_pages`, see "Reading of the page limit"); with figures and tables the same text ends on page 10 of 11 |
| Figures | at most six; a pictorial overview of the architecture is encouraged | T | four, the first is the overview; all drawn at the width of the text block |
| Tables | no numerical limit stated | T | three (metadata, comparison, validation) |
| Code metadata table | rows C1–C8: current code version; permanent link to code/repository used for this code version; legal code license; code versioning system used; software code languages, tools and services used; compilation requirements, operating environments and dependencies; link to developer documentation/manual; support email | T | Table 1 |
| Software metadata table (S rows) | not in the current templates; the LaTeX template ends with an empty heading "Current executable software version" | T | not included |
| Repository | "It is mandatory to publicly share the code"; "We only accept GitHub repositories within Metadata Tables"; the repository must have "a well-documented README.md file, and a Licence.txt file" | T | two GitHub repositories (R and Python) in C2; both have README.md; license files are `LICENSE` / `LICENSE.md`, **not** `Licence.txt` (see open points) |
| License | "one of the pre-approved licenses listed in the Guide for Authors, such as Apache License, GNU General Public License (GPL) or MIT License" | T | MIT |
| Version | C1 "For example: v42"; C4 versioning system | T | v0.1.0, git; no tag exists (see open points) |
| DOI of the code | not required by the templates; "If the software repository you used supplied a DOI or another Persistent IDentifier (PID), please add a reference for your software here" | T | none exists, none cited |
| References | numbered, in order of citation; LaTeX: `elsarticle` with `elsarticle-num` | T | `elsarticle-num` via natbib |
| LaTeX class | template: `\documentclass[preprint,12pt,a4paper]{elsarticle}` | T | `preprint, 3p` through `rticles::elsevier_article`, as in the earlier submission [P]; switching is a one-line change of `classoption` |
| Acknowledgements | optional ("Optionally thank people and institutes you need to acknowledge") | T | heading present, text to be completed or removed by the author |
| Funding, competing interest, generative-AI declaration | not in the template; present as unnumbered sections after the conclusions in the earlier submission | P | same headings, in the same order; text "TO BE COMPLETED BY THE AUTHOR" (facts of the earlier submission are not copied) |
| Review model | single anonymized | D | author names in the manuscript |
| Open access | open-access journal with an article publishing charge | D | – |

## Comparison with the earlier submission (`../fbrglm/paper/`), 2026-11-14

Re-read for the revision of the manuscript: `fbrglm-softwarex.Rmd`, its
built PDF (8 pages), `README.md`, and `revise/` (reviews, response letter,
cover letter, submission checklist).

| element | earlier submission [P] | current template [T] | this manuscript |
|---|---|---|---|
| class and options | `rticles::elsevier_article`, `classoption: "preprint, 3p"`, `journal: SoftwareX`, `numbersections: true`, natbib, `biblio-style: elsarticle-num` | `\documentclass[preprint,12pt,a4paper]{elsarticle}`, `elsarticle-num` | as [P]. The template prescribes sections and limits, not the option set; both are `elsarticle` preprint layouts. Changing to the template's options is one line (`classoption`) |
| preamble | booktabs, longtable, array, float, shims for JSS markup | – | booktabs, array, float; float-placement parameters |
| five sections | yes, same titles | mandatory | yes, same titles |
| Impact subsections | three | free | four (the fourth is Limitations, asked for by the reviewers of [P]) |
| metadata table | C1–C8, placed before section 1 | "Required Metadata", before the text | same |
| repository in C2 | one GitHub repository; a Zenodo DOI for the companion repository | GitHub only | two GitHub repositories with commits; no DOI exists |
| author block | three authors, emails, two affiliations, footnote | authors, affiliations, email | one author (the only one named in the packages), one affiliation, no email yet |
| after the conclusions | Funding; Declaration of competing interest; Declaration of generative AI…; References | Acknowledgements (optional); References | Reproducibility and data availability; Acknowledgements; Funding; the two declarations; References |
| length | 8 pages in total with one figure | 6 pages excluding metadata, tables, figures, references; 4000 words | see next section |

No conflict between [P] and [T] was found that would require departing from
[P], except that [T] contains an Acknowledgements section, which was added.

## Reading of the page limit

Template: "maximum six (6) pages in total (excluding metadata, tables,
figures, references) with a 4000-word limit (we ask that more priority is
placed on the word limit versus the page count)". The limit therefore
applies to the running text of sections 1–5. It is checked as follows
(`R/manuscript_checks.R`, check `text_only_pages`): every figure and table
environment is removed from the built LaTeX file, the file is compiled
again, and the pages up to the end of section 5 are counted. The count
includes the title block and the abstract, which the template does not
mention, so it is an upper bound. Result: 6 pages in the `preprint, 3p`
layout. With the template's `12pt, a4paper` options the same text would
take more pages; the word limit, which has priority, is met with a margin
(3249 of 4000). Nothing was cut or compressed to reach a page number.

## Not verified (Guide for Authors not readable)

- the complete list of pre-approved licenses;
- highlights (whether required, and their limits);
- exact wording and placement of the declarations (competing interest,
  CRediT, generative AI, funding) and of a data-availability statement;
- figure file formats and resolution;
- whether a tagged release or an archived DOI of the code is required
  beyond what the templates say;
- the current article publishing charge.

## Open points for the author before submission

1. **Two repositories in C2.** The template speaks of "a GitHub repository"
   that the journal forks. This paper covers two (R and Python). Whether
   two links are acceptable, or a single umbrella repository is needed,
   should be asked of the editorial office.
2. **License file name.** The template asks for `Licence.txt`; the package
   repositories have `LICENSE` (Python) and `LICENSE` + `LICENSE.md` (R).
3. **No release tag and no DOI.** C1 gives v0.1.0 and C2 the commits the
   experiments were run with (`config/pins.env`). A tagged release (and, if
   wanted, a Zenodo DOI, as for the earlier submission) would make the
   "permanent link" exact. The R repository has one later,
   documentation-only commit (`4632626`, specification §8.2).
4. **Author list, affiliations, corresponding email, funding,
   declarations.** Only what could be taken from the earlier manuscript of
   the same author (name, affiliation address) is filled in; everything
   else is marked in the text.
5. **Page count and layout.** The running text is at the six-page limit
   in the `3p` layout (see "Reading of the page limit") and well inside the
   word limit. The earlier submission was 8 pages in total with one figure;
   this one is 11 with four figures and three tables. If the editor reads
   the limit more strictly, the candidates to move to the repository are
   Figure 4 (runtime) and section 3.5.

## How the references were verified (2026-11-14)

| key | checked against |
|---|---|
| `janssen2023umfi` | proceedings page (Phase 1); PDF read on 2026-11-14 for the definition (`docs/manuscript_review.md`) |
| `catav2021marginal` | proceedings page `https://proceedings.mlr.press/v139/catav21a.html` (title, eight authors, volume 139, pages 1324–1335, editors), 2026-11-14 |
| `breiman2001random`, `strobl2008conditional`, `kaufman2012leakage`, `wright2017ranger`, `molder2021snakemake`, `kurtzer2017singularity` | Crossref record of the DOI (title, authors, journal, volume, year) |
| `pedregosa2011scikit` | citation metadata of the JMLR page |
| `tidymodels` | citation file of the CRAN package |
| `uci_concrete`, `uci_wdbc`, `uci_maternal` | UCI API (creators, year, DOI); the DOIs resolve to the data-set pages |
| `umfi_r`, `umfi_python` | the repositories at the commits of `config/pins.env`; author of the R package from its DESCRIPTION; the Python repository names no author, so the account name is given; year = year of the pinned commit |
