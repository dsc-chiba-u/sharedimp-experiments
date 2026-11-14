# Why is the forest importance positive on average under a null design (B6)?
# A small simulation, one factor at a time. Reading: docs/null_forest_investigation.md.
#
#   snakemake -s workflow/04c_null_forest.smk --use-singularity -c16
#
#   data     data/null_forest/<design>.csv, manifest.json
#   raw      results/raw/04c_null_forest/{r,python}/<design>__<variant>.{csv,meta.json}
#   summary  results/summary/04c_null_forest/{summary,paired_with_baseline,runs}.csv
#   tables   results/tables/04c_null_forest.md
include: "common.smk"

CONFIG = 'config/04c_null_forest.json'
CFG = json.load(open(CONFIG))
RAW = 'results/raw/04c_null_forest'
SUM = 'results/summary/04c_null_forest'
CELLS = [(lang, design, variant)
         for design, d in CFG['designs'].items()
         for variant, v in CFG['variants'].items()
         for lang in v.get('languages', ['r', 'python'])
         if d['variants'] == 'all' or variant in d['variants']]
RESULTS = [f'{RAW}/{lang}/{design}__{variant}.{ext}' for lang, design, variant in CELLS for ext in ('csv', 'meta.json')]

wildcard_constraints:
    design='[a-z0-9_]+?',
    variant='[a-z0-9_]+'

rule all:
    input:
        'results/tables/04c_null_forest.md'

rule null_data:
    input:
        CONFIG
    output:
        'data/null_forest/manifest.json',
        expand('data/null_forest/{design}.csv', design=list(CFG['designs']))
    container:
        PY_CONTAINER
    log:
        'logs/04c_null_forest/data.log'
    shell:
        'python -m sharedimp_exp.null_forest_data {input} >& {log}'

rule null_r:
    input:
        CONFIG,
        'data/null_forest/manifest.json'
    output:
        RAW + '/r/{design}__{variant}.csv',
        RAW + '/r/{design}__{variant}.meta.json'
    container:
        R_CONTAINER
    benchmark:
        'benchmarks/04c_null_forest/r_{design}__{variant}.txt'
    log:
        'logs/04c_null_forest/r_{design}__{variant}.log'
    shell:
        'Rscript R/null_forest.R {input[0]} ' + RAW + '/r {wildcards.design} {wildcards.variant} >& {log}'

rule null_python:
    input:
        CONFIG,
        'data/null_forest/manifest.json'
    output:
        RAW + '/python/{design}__{variant}.csv',
        RAW + '/python/{design}__{variant}.meta.json'
    container:
        PY_CONTAINER
    benchmark:
        'benchmarks/04c_null_forest/python_{design}__{variant}.txt'
    log:
        'logs/04c_null_forest/python_{design}__{variant}.log'
    shell:
        'python -m sharedimp_exp.null_forest {input[0]} ' + RAW + '/python {wildcards.design} {wildcards.variant} >& {log}'

rule null_summary:
    input:
        CONFIG,
        RESULTS
    output:
        expand(SUM + '/{name}.csv', name=['summary', 'paired_with_baseline', 'runs']),
        'results/tables/04c_null_forest.md'
    container:
        PY_CONTAINER
    log:
        'logs/04c_null_forest/summary.log'
    shell:
        'python -m sharedimp_exp.null_forest_summary {input[0]} ' + RAW + ' ' + SUM + ' >& {log}'
