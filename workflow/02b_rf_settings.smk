# Random-forest settings study: what min.node.size / min.bucket (ranger) and
# min_samples_split / min_samples_leaf (scikit-learn) mean and how much the
# difference matters. Background and conclusions: docs/random_forest_comparison.md.
#
#   snakemake -s workflow/02b_rf_settings.smk --use-singularity -c2
#
#   raw      results/raw/02b_rf_settings/{r,python}/{single_tree,single_tree_predictions,bootstrap_counting,forest,forest_importance}.csv, meta.json
#   summary  results/summary/02b_rf_settings/{single_tree_pairs,bootstrap_counting,forest_settings,forest_importance,forest_importance_contrasts}.csv
#   tables   results/tables/02b_rf_settings.md
include: "common.smk"

CONFIG = 'config/02b_rf_settings.json'
RAW = 'results/raw/02b_rf_settings'
SUM = 'results/summary/02b_rf_settings'
FILES = ['single_tree.csv', 'single_tree_predictions.csv', 'bootstrap_counting.csv', 'forest.csv', 'forest_importance.csv', 'meta.json']

rule all:
    input:
        'results/tables/02b_rf_settings.md'

rule rf_settings_r:
    input:
        CONFIG,
        'data/synthetic/manifest.json'
    output:
        expand(RAW + '/r/{file}', file=FILES)
    container:
        R_CONTAINER
    benchmark:
        'benchmarks/02b_rf_settings/r.txt'
    log:
        'logs/02b_rf_settings/r.log'
    shell:
        'Rscript R/rf_settings.R {input[0]} ' + RAW + '/r >& {log}'

rule rf_settings_python:
    input:
        CONFIG,
        'data/synthetic/manifest.json'
    output:
        expand(RAW + '/python/{file}', file=FILES)
    container:
        PY_CONTAINER
    benchmark:
        'benchmarks/02b_rf_settings/python.txt'
    log:
        'logs/02b_rf_settings/python.log'
    shell:
        'python -m sharedimp_exp.rf_settings {input[0]} ' + RAW + '/python >& {log}'

rule rf_settings_summary:
    input:
        CONFIG,
        expand(RAW + '/{lang}/{file}', lang=['r', 'python'], file=FILES)
    output:
        expand(SUM + '/{name}.csv', name=['single_tree_pairs', 'bootstrap_counting', 'forest_settings', 'forest_importance', 'forest_importance_contrasts']),
        'results/tables/02b_rf_settings.md'
    container:
        PY_CONTAINER
    log:
        'logs/02b_rf_settings/summary.log'
    shell:
        'python -m sharedimp_exp.rf_settings_summary {input[0]} ' + RAW + ' ' + SUM + ' >& {log}'
