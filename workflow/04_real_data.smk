# Experiment C: public data sets in R and in Python.
#
#   snakemake -s workflow/04_real_data.smk --use-singularity -c8
#
# Same data file, same fold labels (column `fold`), same metric in both
# languages. `linear` jobs are checked for R-Python agreement; `rand_forest`
# jobs are language-specific usage examples and are only reported.
#
#   data     data/real/<id>.csv, data/real/manifest.json   (prepared from the sources in config/04_real_data.json)
#   raw      results/raw/04_real_data/{r,python}/<job>.{importance.csv,folds.csv,meta.json}
#   summary  results/summary/04_real_data/{checks,parity,importance_long,datasets,performance}.csv
#   tables   results/tables/04_real_data*.md
include: "common.smk"

DATA_CONFIG = 'config/04_real_data.json'
JOBS_FILE = 'config/04_real_data_jobs.json'
JOBS = job_ids(JOBS_FILE)
DATASETS = sorted({job['dataset'] for job in json.load(open(JOBS_FILE))['jobs']})
RAW = 'results/raw/04_real_data'
SUM = 'results/summary/04_real_data'
RESULT = ['importance.csv', 'folds.csv', 'meta.json']

rule all:
    input:
        SUM + '/checks.csv',
        SUM + '/performance.csv',
        'results/tables/04_real_data.md'

# Needs network access. The source files are pinned by sha256.
rule prepare_data:
    input:
        DATA_CONFIG
    output:
        'data/real/manifest.json',
        expand('data/real/{dataset}.csv', dataset=DATASETS)
    container:
        PY_CONTAINER
    log:
        'logs/04_real_data/prepare_data.log'
    shell:
        'python -m sharedimp_exp.real_data {input} >& {log}'

rule real_r:
    input:
        JOBS_FILE,
        'data/real/manifest.json'
    output:
        expand(RAW + '/r/{{job}}.{ext}', ext=RESULT)
    container:
        R_CONTAINER
    benchmark:
        'benchmarks/04_real_data/r_{job}.txt'
    log:
        'logs/04_real_data/r_{job}.log'
    shell:
        'Rscript R/run_jobs.R {input[0]} ' + RAW + '/r {wildcards.job} >& {log}'

rule real_python:
    input:
        JOBS_FILE,
        'data/real/manifest.json'
    output:
        expand(RAW + '/python/{{job}}.{ext}', ext=RESULT)
    container:
        PY_CONTAINER
    benchmark:
        'benchmarks/04_real_data/python_{job}.txt'
    log:
        'logs/04_real_data/python_{job}.log'
    shell:
        'python -m sharedimp_exp.run_jobs {input[0]} ' + RAW + '/python {wildcards.job} >& {log}'

rule check:
    input:
        JOBS_FILE,
        expand(RAW + '/{lang}/{job}.{ext}', lang=['r', 'python'], job=JOBS, ext=RESULT)
    output:
        expand(SUM + '/{name}.csv', name=['checks', 'parity', 'importance_long']),
        'results/tables/04_real_data_checks.md'
    container:
        PY_CONTAINER
    log:
        'logs/04_real_data/check.log'
    shell:
        'python -m sharedimp_exp.check_jobs ' + JOBS_FILE + ' ' + RAW + ' ' + SUM + ' >& {log}'

rule summary:
    input:
        JOBS_FILE,
        'data/real/manifest.json',
        SUM + '/importance_long.csv',
        SUM + '/parity.csv',
        expand(RAW + '/{lang}/{job}.{ext}', lang=['r', 'python'], job=JOBS, ext=RESULT)
    output:
        SUM + '/datasets.csv',
        SUM + '/performance.csv',
        SUM + '/importance_wide.csv',
        'results/tables/04_real_data.md'
    container:
        PY_CONTAINER
    log:
        'logs/04_real_data/summary.log'
    shell:
        'python -m sharedimp_exp.real_data_summary ' + JOBS_FILE + ' ' + RAW + ' ' + SUM + ' >& {log}'
