# Experiment C, follow-up: the duplicated rows of the Maternal Health Risk data.
#
#   snakemake -s workflow/04b_maternal.smk --use-singularity -c8
#
# Run workflow 04 first: its Maternal results (random stratified folds, all
# rows) are the reference and are read, not recomputed. Here the same jobs are
# run on two derived files: group-aware folds, and identical records removed.
# Background and recommendation: docs/maternal_duplicates.md.
#
#   data     data/derived/{maternal_grouped,maternal_dedup}.csv, data/derived/manifest.json
#   raw      results/raw/04b_maternal/{duplicates.json,multiplicity.csv,first_occurrence.csv,conflicting_groups.csv}
#            results/raw/04b_maternal/{r,python}/<job>.{importance.csv,folds.csv,meta.json}
#   summary  results/summary/04b_maternal/{checks,parity,importance_long,variants,scores,importance_by_variant,rank_agreement}.csv
#   tables   results/tables/04b_maternal{,_checks}.md
include: "common.smk"

CONFIG = 'config/04b_maternal.json'
JOBS_FILE = 'config/04b_maternal_jobs.json'
JOBS = job_ids(JOBS_FILE)
VARIANTS = list(json.load(open(CONFIG))['variants'])
RAW = 'results/raw/04b_maternal'
SUM = 'results/summary/04b_maternal'
RESULT = ['importance.csv', 'folds.csv', 'meta.json']
REFERENCE = expand('results/raw/04_real_data/{lang}/maternal_{job}.{ext}', lang=['r', 'python'],
                   job=['linear_logloss', 'linear_accuracy', 'rf_logloss', 'rf_accuracy'], ext=RESULT)

rule all:
    input:
        'results/tables/04b_maternal.md',
        SUM + '/checks.csv'

rule variants:
    input:
        CONFIG,
        'data/real/manifest.json',
        'data/real/maternal.csv'
    output:
        'data/derived/manifest.json',
        expand('data/derived/{variant}.csv', variant=VARIANTS),
        expand(RAW + '/{name}', name=['duplicates.json', 'multiplicity.csv', 'first_occurrence.csv', 'conflicting_groups.csv'])
    container:
        PY_CONTAINER
    log:
        'logs/04b_maternal/variants.log'
    shell:
        'python -m sharedimp_exp.maternal_variants {input[0]} ' + RAW + ' >& {log}'

rule maternal_r:
    input:
        JOBS_FILE,
        'data/derived/manifest.json'
    output:
        expand(RAW + '/r/{{job}}.{ext}', ext=RESULT)
    container:
        R_CONTAINER
    benchmark:
        'benchmarks/04b_maternal/r_{job}.txt'
    log:
        'logs/04b_maternal/r_{job}.log'
    shell:
        'Rscript R/run_jobs.R {input[0]} ' + RAW + '/r {wildcards.job} >& {log}'

rule maternal_python:
    input:
        JOBS_FILE,
        'data/derived/manifest.json'
    output:
        expand(RAW + '/python/{{job}}.{ext}', ext=RESULT)
    container:
        PY_CONTAINER
    benchmark:
        'benchmarks/04b_maternal/python_{job}.txt'
    log:
        'logs/04b_maternal/python_{job}.log'
    shell:
        'python -m sharedimp_exp.run_jobs {input[0]} ' + RAW + '/python {wildcards.job} >& {log}'

rule check:
    input:
        JOBS_FILE,
        expand(RAW + '/{lang}/{job}.{ext}', lang=['r', 'python'], job=JOBS, ext=RESULT)
    output:
        expand(SUM + '/{name}.csv', name=['checks_jobs', 'parity', 'importance_long']),
        'results/tables/04b_maternal_jobs_checks.md'
    container:
        PY_CONTAINER
    log:
        'logs/04b_maternal/check.log'
    shell:
        # check_jobs names its table after the output directory; keep its
        # checks apart from the data checks added by the summary rule
        'python -m sharedimp_exp.check_jobs ' + JOBS_FILE + ' ' + RAW + ' ' + SUM + ' >& {log}; '
        'mv ' + SUM + '/checks.csv ' + SUM + '/checks_jobs.csv; '
        'mv results/tables/04b_maternal_checks.md results/tables/04b_maternal_jobs_checks.md'

rule summary:
    input:
        CONFIG,
        JOBS_FILE,
        'data/derived/manifest.json',
        RAW + '/duplicates.json',
        SUM + '/checks_jobs.csv',
        SUM + '/importance_long.csv',
        'results/summary/04_real_data/importance_long.csv',
        REFERENCE
    output:
        expand(SUM + '/{name}.csv', name=['checks', 'variants', 'scores', 'importance_by_variant', 'rank_agreement']),
        'results/tables/04b_maternal.md',
        'results/tables/04b_maternal_checks.md'
    container:
        PY_CONTAINER
    log:
        'logs/04b_maternal/summary.log'
    shell:
        'python -m sharedimp_exp.maternal_summary {input[0]} {input[1]} ' + RAW + ' ' + SUM + ' >& {log}'
