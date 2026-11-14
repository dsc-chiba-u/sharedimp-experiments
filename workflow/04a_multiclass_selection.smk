# Experiment C: screening of the candidates for the multiclass data set.
#
#   snakemake -s workflow/04a_multiclass_selection.smk --use-singularity -c1
#
# Criteria: docs/experiment_plan.md, section 5d (fixed before any candidate
# was downloaded). Needs network access; the source files are pinned by
# sha256. No importance is computed here; the data set that passes is added
# to workflow 04, which checks the R-Python agreement (criterion E9).
#
# Candidates that pass E1-E8 are prepared in data/candidates/ and go through
# the pilot of E9: the `linear` jobs of experiment C in R and Python, checked
# with the unchanged checker and tolerance. A failed parity check is the
# outcome of the pilot (recorded, the workflow goes on); models whose
# accuracy differs are refitted in both languages to explain the difference.
#
#   data     data/candidates/{candidate_<id>.csv,manifest.json}   (not used by any experiment)
#   raw      results/raw/04a_multiclass_selection/screening.json
#            results/raw/04a_multiclass_pilot/{r,python}/<job>.{importance.csv,folds.csv,meta.json}, diag/
#   summary  results/summary/04a_multiclass_selection/{criteria,candidates}.csv
#            results/summary/04a_multiclass_pilot/{checks,parity,importance_long,e9,flips,decision}.csv, decision.json
#   tables   results/tables/04a_multiclass_selection.md, 04a_multiclass_pilot.md, 04a_multiclass_pilot_checks.md
include: "common.smk"

CONFIG = 'config/04a_multiclass_selection.json'
RAW = 'results/raw/04a_multiclass_selection'
SUM = 'results/summary/04a_multiclass_selection'
JOBS_FILE = 'config/04a_pilot_jobs.json'
JOBS = job_ids(JOBS_FILE)
PRAW = 'results/raw/04a_multiclass_pilot'
PSUM = 'results/summary/04a_multiclass_pilot'
RESULT = ['importance.csv', 'folds.csv', 'meta.json']

rule all:
    input:
        SUM + '/candidates.csv',
        PSUM + '/decision.csv'

rule screen:
    input:
        CONFIG
    output:
        RAW + '/screening.json',
        SUM + '/criteria.csv',
        SUM + '/candidates.csv',
        'results/tables/04a_multiclass_selection.md',
        'data/candidates/manifest.json'
    container:
        PY_CONTAINER
    log:
        'logs/04a_multiclass_selection/screen.log'
    shell:
        'python -m sharedimp_exp.multiclass_selection {input} ' + RAW + ' ' + SUM + ' >& {log}'

rule pilot_r:
    input:
        JOBS_FILE,
        'data/candidates/manifest.json'
    output:
        expand(PRAW + '/r/{{job}}.{ext}', ext=RESULT)
    container:
        R_CONTAINER
    benchmark:
        'benchmarks/04a_multiclass_selection/r_{job}.txt'
    log:
        'logs/04a_multiclass_selection/r_{job}.log'
    shell:
        'Rscript R/run_jobs.R {input[0]} ' + PRAW + '/r {wildcards.job} >& {log}'

rule pilot_python:
    input:
        JOBS_FILE,
        'data/candidates/manifest.json'
    output:
        expand(PRAW + '/python/{{job}}.{ext}', ext=RESULT)
    container:
        PY_CONTAINER
    benchmark:
        'benchmarks/04a_multiclass_selection/python_{job}.txt'
    log:
        'logs/04a_multiclass_selection/python_{job}.log'
    shell:
        'python -m sharedimp_exp.run_jobs {input[0]} ' + PRAW + '/python {wildcards.job} >& {log}'

rule pilot_check:
    input:
        JOBS_FILE,
        expand(PRAW + '/{lang}/{job}.{ext}', lang=['r', 'python'], job=JOBS, ext=RESULT)
    output:
        expand(PSUM + '/{name}.csv', name=['checks', 'parity', 'importance_long']),
        'results/tables/04a_multiclass_pilot_checks.md',
        PRAW + '/diag/cells.json'
    container:
        PY_CONTAINER
    log:
        'logs/04a_multiclass_selection/pilot_check.log'
    shell:
        'python -m sharedimp_exp.multiclass_pilot check {input[0]} ' + PRAW + ' ' + PSUM + ' >& {log}'

rule pilot_diag_r:
    input:
        PRAW + '/diag/cells.json'
    output:
        PRAW + '/diag/r_done.json'
    container:
        R_CONTAINER
    log:
        'logs/04a_multiclass_selection/pilot_diag_r.log'
    shell:
        'Rscript R/multiclass_pilot_diag.R ' + PRAW + '/diag >& {log}'

rule pilot_report:
    input:
        JOBS_FILE,
        PSUM + '/checks.csv',
        PRAW + '/diag/r_done.json',
        SUM + '/candidates.csv'
    output:
        expand(PSUM + '/{name}.csv', name=['e9', 'flips', 'decision']),
        PSUM + '/decision.json',
        'results/tables/04a_multiclass_pilot.md'
    container:
        PY_CONTAINER
    log:
        'logs/04a_multiclass_selection/pilot_report.log'
    shell:
        'python -m sharedimp_exp.multiclass_pilot report {input[0]} ' + PRAW + ' ' + PSUM + ' ' + SUM + ' >& {log}'
