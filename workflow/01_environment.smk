# Experiment A: environment record and smoke test (n = 20, p = 3).
#
#   snakemake -s workflow/01_environment.smk --use-singularity -c4
#
#   raw      results/raw/01_environment/{host,r,python,docker_images}.json
#            results/raw/01_environment/{r,python}/<job>.{importance.csv,folds.csv,meta.json}
#   summary  results/summary/01_environment/{environment,checks,parity,importance_long}.csv
#   tables   results/tables/01_environment.md, results/tables/01_environment_checks.md
#
# Fails if a process does not run inside the pinned image, if an image is not
# the pinned commit, if a job fails in either language, or if a check fails.
include: "common.smk"

JOBS_FILE = 'config/01_smoke_jobs.json'
JOBS = job_ids(JOBS_FILE)
RAW = 'results/raw/01_environment'
SUM = 'results/summary/01_environment'
RESULT = ['importance.csv', 'folds.csv', 'meta.json']

rule all:
    input:
        SUM + '/environment.csv',
        'results/tables/01_environment.md',
        SUM + '/checks.csv',
        'results/tables/01_environment_checks.md'

rule host_info:
    output:
        RAW + '/host.json'
    params:
        python=sys.executable
    log:
        'logs/01_environment/host_info.log'
    shell:
        '{params.python} python/sharedimp_exp/host_info.py {output} >& {log}'

rule r_env_info:
    output:
        RAW + '/r.json'
    container:
        R_CONTAINER
    log:
        'logs/01_environment/r_env_info.log'
    shell:
        'Rscript R/env_info.R {output} >& {log}'

rule python_env_info:
    output:
        RAW + '/python.json'
    container:
        PY_CONTAINER
    log:
        'logs/01_environment/python_env_info.log'
    shell:
        'python -m sharedimp_exp.env_info {output} >& {log}'

rule docker_info:
    output:
        RAW + '/docker_images.json'
    container:
        PY_CONTAINER
    log:
        'logs/01_environment/docker_info.log'
    shell:
        'python -m sharedimp_exp.docker_info {output} >& {log}'

rule env_summary:
    input:
        expand(RAW + '/{name}.json', name=['host', 'r', 'python', 'docker_images'])
    output:
        SUM + '/environment.csv',
        'results/tables/01_environment.md'
    container:
        PY_CONTAINER
    log:
        'logs/01_environment/env_summary.log'
    shell:
        'python -m sharedimp_exp.env_summary ' + RAW + ' ' + SUM + ' >& {log}'

rule smoke_r:
    input:
        JOBS_FILE
    output:
        expand(RAW + '/r/{{job}}.{ext}', ext=RESULT)
    container:
        R_CONTAINER
    benchmark:
        'benchmarks/01_environment/r_{job}.txt'
    log:
        'logs/01_environment/r_{job}.log'
    shell:
        'Rscript R/run_jobs.R {input} ' + RAW + '/r {wildcards.job} >& {log}'

rule smoke_python:
    input:
        JOBS_FILE
    output:
        expand(RAW + '/python/{{job}}.{ext}', ext=RESULT)
    container:
        PY_CONTAINER
    benchmark:
        'benchmarks/01_environment/python_{job}.txt'
    log:
        'logs/01_environment/python_{job}.log'
    shell:
        'python -m sharedimp_exp.run_jobs {input} ' + RAW + '/python {wildcards.job} >& {log}'

rule check:
    input:
        JOBS_FILE,
        expand(RAW + '/{lang}/{job}.{ext}', lang=['r', 'python'], job=JOBS, ext=RESULT)
    output:
        expand(SUM + '/{name}.csv', name=['checks', 'parity', 'importance_long']),
        'results/tables/01_environment_checks.md'
    container:
        PY_CONTAINER
    log:
        'logs/01_environment/check.log'
    shell:
        'python -m sharedimp_exp.check_jobs ' + JOBS_FILE + ' ' + RAW + ' ' + SUM + ' >& {log}'
