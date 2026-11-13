# Validation of the two implementations inside the pinned images:
# classification smoke tests and the linear-Gaussian positive control.
# (Cross-language parity itself is tested in the packages; this workflow only
# confirms it on the data and through the runners used by the experiments.)
#
#   snakemake -s workflow/02_validation.smk --use-singularity -c4
#
#   raw      results/raw/02_validation/{r,python}/<job>.{importance.csv,folds.csv,meta.json}
#   summary  results/summary/02_validation/{checks,parity,importance_long,positive_control}.csv
#   tables   results/tables/02_validation_checks.md
#
# The synthetic data are regenerated first and must reproduce the committed
# files byte for byte.
include: "common.smk"

JOBS_FILE = 'config/02_validation_jobs.json'
JOBS = job_ids(JOBS_FILE)
RAW = 'results/raw/02_validation'
SUM = 'results/summary/02_validation'
RESULT = ['importance.csv', 'folds.csv', 'meta.json']

rule all:
    input:
        SUM + '/checks.csv',
        'results/tables/02_validation_checks.md'

rule check_synthetic:
    input:
        'data/synthetic/manifest.json'
    output:
        RAW + '/synthetic_data_check.json'
    container:
        PY_CONTAINER
    log:
        'logs/02_validation/check_synthetic.log'
    shell:
        'python -m sharedimp_exp.make_synthetic --check {output} >& {log}'

rule validate_r:
    input:
        JOBS_FILE,
        RAW + '/synthetic_data_check.json'
    output:
        expand(RAW + '/r/{{job}}.{ext}', ext=RESULT)
    container:
        R_CONTAINER
    benchmark:
        'benchmarks/02_validation/r_{job}.txt'
    log:
        'logs/02_validation/r_{job}.log'
    shell:
        'Rscript R/run_jobs.R {input[0]} ' + RAW + '/r {wildcards.job} >& {log}'

rule validate_python:
    input:
        JOBS_FILE,
        RAW + '/synthetic_data_check.json'
    output:
        expand(RAW + '/python/{{job}}.{ext}', ext=RESULT)
    container:
        PY_CONTAINER
    benchmark:
        'benchmarks/02_validation/python_{job}.txt'
    log:
        'logs/02_validation/python_{job}.log'
    shell:
        'python -m sharedimp_exp.run_jobs {input[0]} ' + RAW + '/python {wildcards.job} >& {log}'

rule check:
    input:
        JOBS_FILE,
        expand(RAW + '/{lang}/{job}.{ext}', lang=['r', 'python'], job=JOBS, ext=RESULT)
    output:
        expand(SUM + '/{name}.csv', name=['checks', 'parity', 'importance_long', 'positive_control']),
        'results/tables/02_validation_checks.md'
    container:
        PY_CONTAINER
    log:
        'logs/02_validation/check.log'
    shell:
        'python -m sharedimp_exp.check_jobs ' + JOBS_FILE + ' ' + RAW + ' ' + SUM + ' >& {log}'
