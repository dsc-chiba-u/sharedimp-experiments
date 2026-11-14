# Figures of Phases 2 and 3, drawn from summary files only.
#
#   snakemake -s workflow/06_figures.smk --use-singularity -c1
#
# The summaries are inputs: run workflows 01-05 first. The workflow diagram of
# the paper (no data) belongs to Phase 4 and is not produced here.
include: "common.smk"

FIGURES = ['03_official_designs', '03_fold_internal_effect', '04_real_data_importance', '04_r_python_agreement']

FIGURES_PHASE3 = ['04b_maternal_duplicates', '04c_null_forest', '05_runtime_scaling', '05_runtime_learners']

rule all:
    input:
        expand('results/figures/{name}.{ext}', name=FIGURES + FIGURES_PHASE3, ext=['pdf', 'png'])

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

rule figures_phase3:
    input:
        expand('results/summary/04b_maternal/{name}.csv', name=['scores', 'importance_by_variant']),
        'results/summary/04c_null_forest/summary.csv',
        expand('results/summary/05_runtime/{name}.csv', name=['cells', 'comparisons'])
    output:
        expand('results/figures/{name}.{ext}', name=FIGURES_PHASE3, ext=['pdf', 'png'])
    container:
        EXP_R_CONTAINER
    log:
        'logs/06_figures/figures_phase3.log'
    shell:
        'Rscript R/figures_phase3.R results/summary results/figures >& {log}'
