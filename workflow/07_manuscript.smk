# Manuscript (Phase 4): figures made for the paper, the PDF, and its checks.
#
#   snakemake -s workflow/07_manuscript.smk --use-singularity -c1
#
# Reads results/summary/ and results/figures/ of workflows 01-06 (inputs; run
# them first) and changes none of them. Every number in the text is read from
# results/ while the document is knitted (paper/manuscript.Rmd, chunk
# `setup`) and written with its source file to numbers.csv.
#
#   figures  results/figures/07_software_overview.{pdf,png}   (diagram, no data)
#            results/figures/07_examples_importance.{pdf,png} (examples; Maternal with group-aware folds)
#   paper    paper/manuscript.pdf, paper/manuscript.tex        (build products, git-ignored)
#   summary  results/summary/07_manuscript/{numbers,checks}.csv
#   tables   results/tables/07_manuscript_checks.md
include: "common.smk"

MANUSCRIPT_CONTAINER = f"docker://{PINS['MANUSCRIPT_IMAGE']}@{PINS['MANUSCRIPT_IMAGE_DIGEST']}"
SUM = 'results/summary/07_manuscript'
PAPER_FIGURES = ['07_software_overview', '07_examples_importance']
USED_FIGURES = ['03_fold_internal_effect', '04_r_python_agreement', '05_runtime_scaling']

rule all:
    input:
        'paper/manuscript.pdf',
        SUM + '/checks.csv'

rule figure_overview:
    output:
        expand('results/figures/07_software_overview.{ext}', ext=['pdf', 'png'])
    container:
        EXP_R_CONTAINER
    log:
        'logs/07_manuscript/figure_overview.log'
    shell:
        'Rscript R/figure_overview.R results/figures >& {log}'

rule figure_examples:
    input:
        'results/summary/04_real_data/importance_wide.csv',
        'results/summary/04_real_data/datasets.csv',
        'results/summary/04b_maternal/importance_by_variant.csv'
    output:
        expand('results/figures/07_examples_importance.{ext}', ext=['pdf', 'png'])
    container:
        EXP_R_CONTAINER
    log:
        'logs/07_manuscript/figure_examples.log'
    shell:
        'Rscript R/figure_examples.R results/summary results/figures >& {log}'

# tinytex.install_packages = FALSE: nothing is downloaded while building; a
# missing LaTeX package is an error of the image, not something to fetch.
rule render:
    input:
        'paper/manuscript.Rmd',
        'paper/references.bib',
        'config/pins.env',
        expand('results/figures/{name}.pdf', name=PAPER_FIGURES + USED_FIGURES),
        expand('results/summary/{stage}/checks.csv', stage=['01_environment', '02_validation', '03_official_umfi', '04_real_data', '04b_maternal', '05_runtime']),
        'results/summary/04a_multiclass_pilot/decision.csv',
        'results/summary/04c_null_forest/summary.csv'
    output:
        'paper/manuscript.pdf',
        'paper/manuscript.tex',
        'paper/manuscript.log',
        SUM + '/numbers.csv'
    container:
        MANUSCRIPT_CONTAINER
    log:
        'logs/07_manuscript/render.log'
    shell:
        """Rscript -e 'options(tinytex.install_packages = FALSE, tinytex.clean = FALSE); rmarkdown::render("paper/manuscript.Rmd", quiet = TRUE)' >& {log}"""

rule checks:
    input:
        'paper/manuscript.tex',
        'paper/manuscript.log',
        'paper/references.bib',
        SUM + '/numbers.csv'
    output:
        SUM + '/checks.csv',
        'results/tables/07_manuscript_checks.md'
    container:
        MANUSCRIPT_CONTAINER
    log:
        'logs/07_manuscript/checks.log'
    shell:
        'Rscript R/manuscript_checks.R paper ' + SUM + ' >& {log}'
