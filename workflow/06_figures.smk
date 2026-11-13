# Figures of Phase 2 (experiments B and C), drawn from summary files only.
#
#   snakemake -s workflow/06_figures.smk --use-singularity -c1
#
# The summaries are inputs: run workflows 01-04 first. Figure 4 (runtime) and
# the workflow diagram belong to Phase 3 and are not produced yet.
include: "common.smk"

FIGURES = ['03_official_designs', '03_fold_internal_effect', '04_real_data_importance', '04_r_python_agreement']

rule all:
    input:
        expand('results/figures/{name}.{ext}', name=FIGURES, ext=['pdf', 'png'])

rule figures:
    input:
        'results/summary/03_official_umfi/importance_by_design.csv',
        'results/summary/03_official_umfi/leak.csv',
        'results/summary/04_real_data/importance_wide.csv',
        expand('results/summary/{stage}/{name}.csv', stage=['01_environment', '02_validation', '04_real_data'], name=['importance_long', 'parity'])
    output:
        expand('results/figures/{name}.{ext}', name=FIGURES, ext=['pdf', 'png'])
    container:
        EXP_R_CONTAINER
    log:
        'logs/06_figures/figures.log'
    shell:
        'Rscript R/figures.R results/summary results/figures >& {log}'
