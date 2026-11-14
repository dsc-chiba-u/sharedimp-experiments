# Experiment D: runtime of shared_importance() (Phase 3).
#
#   snakemake -s workflow/05_runtime.smk --use-singularity -c1 pilot   # pilot and plan only
#   snakemake -s workflow/05_runtime.smk --use-singularity -c1         # pilot, plan, main benchmark, summary
#
# Every timing process claims all cores given to Snakemake, so the processes
# run one after the other whatever -c is. Do not run anything else on the
# machine at the same time. Conditions and the budget rule: config/05_runtime.json
# (fixed before the pilot); protocol and reading: docs/runtime_benchmark.md.
#
#   data     data/runtime/rt_n<n>_p<p>.csv (not tracked), data/runtime/manifest.json
#   raw      results/raw/05_runtime/pilot_plan.csv
#            results/raw/05_runtime/{pilot,main}/<language>_<learner>.{runs.csv,cells.csv,importance.csv,meta.json}
#   summary  results/summary/05_runtime/{plan,pilot,pilot_model}.csv, budget.json   (rule plan)
#            results/summary/05_runtime/{cells,comparisons,environment,checks}.csv   (rule summary)
#   tables   results/tables/05_runtime{,_checks}.md
include: "common.smk"

CONFIG = 'config/05_runtime.json'
CFG = json.load(open(CONFIG))
RAW = 'results/raw/05_runtime'
SUM = 'results/summary/05_runtime'
PROCESSES = [f'{lang}_{learner}' for learner, d in CFG['learners'].items() for lang in ('r', 'python') if lang in d]
FILES = ['runs.csv', 'cells.csv', 'importance.csv', 'meta.json']
PLAN_FILES = [SUM + '/plan.csv', SUM + '/pilot.csv', SUM + '/pilot_model.csv', SUM + '/budget.json']

wildcard_constraints:
    stage='pilot|main',
    learner='[a-z_]+'

rule all:
    input:
        'results/tables/05_runtime.md',
        SUM + '/checks.csv'

rule pilot:
    input:
        PLAN_FILES

rule runtime_data:
    input:
        CONFIG
    output:
        'data/runtime/manifest.json'
    container:
        PY_CONTAINER
    log:
        'logs/05_runtime/data.log'
    shell:
        'python -m sharedimp_exp.runtime_data {input} >& {log}'

rule pilot_plan:
    input:
        CONFIG
    output:
        RAW + '/pilot_plan.csv'
    container:
        PY_CONTAINER
    log:
        'logs/05_runtime/pilot_plan.log'
    shell:
        'python -m sharedimp_exp.runtime_plan pilot {input} {output} >& {log}'

def plan_of(wildcards):
    return RAW + '/pilot_plan.csv' if wildcards.stage == 'pilot' else SUM + '/plan.csv'

rule time_r:
    input:
        CONFIG,
        plan_of,
        'data/runtime/manifest.json'
    output:
        expand(RAW + '/{{stage}}/r_{{learner}}.{file}', file=FILES)
    threads:
        workflow.cores
    container:
        R_CONTAINER
    benchmark:
        'benchmarks/05_runtime/{stage}_r_{learner}.txt'
    log:
        'logs/05_runtime/{stage}_r_{learner}.log'
    shell:
        'Rscript R/runtime.R {input[0]} {input[1]} ' + RAW + '/{wildcards.stage} {wildcards.learner} {wildcards.stage} >& {log}'

rule time_python:
    input:
        CONFIG,
        plan_of,
        'data/runtime/manifest.json'
    output:
        expand(RAW + '/{{stage}}/python_{{learner}}.{file}', file=FILES)
    threads:
        workflow.cores
    container:
        PY_CONTAINER
    benchmark:
        'benchmarks/05_runtime/{stage}_python_{learner}.txt'
    log:
        'logs/05_runtime/{stage}_python_{learner}.log'
    shell:
        'python -m sharedimp_exp.runtime {input[0]} {input[1]} ' + RAW + '/{wildcards.stage} {wildcards.learner} {wildcards.stage} >& {log}'

rule plan:
    input:
        CONFIG,
        expand(RAW + '/pilot/{process}.{file}', process=PROCESSES, file=FILES)
    output:
        PLAN_FILES
    container:
        PY_CONTAINER
    log:
        'logs/05_runtime/plan.log'
    shell:
        'python -m sharedimp_exp.runtime_plan main {input[0]} ' + RAW + '/pilot ' + SUM + ' >& {log}'

rule summary:
    input:
        CONFIG,
        PLAN_FILES,
        expand(RAW + '/{stage}/{process}.{file}', stage=['pilot', 'main'], process=PROCESSES, file=FILES)
    output:
        expand(SUM + '/{name}.csv', name=['cells', 'comparisons', 'environment', 'checks']),
        'results/tables/05_runtime.md',
        'results/tables/05_runtime_checks.md'
    container:
        PY_CONTAINER
    log:
        'logs/05_runtime/summary.log'
    shell:
        'python -m sharedimp_exp.runtime_summary {input[0]} ' + RAW + ' ' + SUM + ' >& {log}'
