# Experiment B: comparison with the official UMFI-LR code.
#
#   snakemake -s workflow/03_official_umfi.smk --use-singularity -c8
#
# The official sources are fetched at the pinned commits into external/
# (git-ignored) and evaluated unmodified; none of it is in this repository or
# in an image. Three official implementations:
#   official_r   HydroML/UMFI          (R package, MIT)        -> EXP_R image, same R session as sharedimp-r
#   original_r   joej1997/UMFI         (R script, no license)  -> EXP_R image
#   official_py  guanton/umfi_python   (Python, no license)    -> UMFI_PY image (Python 3.9; exchanges CSV files with sharedimp-py)
#
#   raw      results/raw/03_official_umfi/      sources.json, designs/, representations*.csv, gates.csv,
#                                               identical_{r,python}.csv, importance/, leak.csv, structural_*.json, api_*.json
#   summary  results/summary/03_official_umfi/  checks.csv, residualization.csv, identical_condition.csv,
#                                               importance_by_design.csv, negative_importance.csv, leak.csv, api.csv
#   tables   results/tables/03_official_umfi*.md
include: "common.smk"

CONFIG = 'config/03_official_umfi.json'
CFG = json.load(open(CONFIG))
RAW = 'results/raw/03_official_umfi'
SUM = 'results/summary/03_official_umfi'
SOURCES = RAW + '/sources.json'
DESIGNS = CFG['designs']['official_generators'] + [CFG['designs']['null']['name']]
DESIGN_FILES = expand(RAW + '/designs/{design}_seed{seed:02d}.csv', design=DESIGNS, seed=CFG['designs']['seeds'])
SUMMARY = ['checks', 'residualization', 'identical_condition', 'importance_by_design', 'negative_importance', 'leak', 'api']

rule all:
    input:
        expand(SUM + '/{name}.csv', name=SUMMARY),
        'results/tables/03_official_umfi.md',
        'results/tables/03_official_umfi_checks.md'

# Host rule (git): no container.
rule fetch_official:
    input:
        CONFIG,
        'config/pins.env'
    output:
        SOURCES
    params:
        python=sys.executable
    log:
        'logs/03_official_umfi/fetch_official.log'
    shell:
        '{params.python} python/sharedimp_exp/official_fetch.py {input[0]} {output} >& {log}'

rule designs:
    input:
        CONFIG,
        SOURCES
    output:
        DESIGN_FILES,
        RAW + '/designs/manifest.json'
    container:
        UMFI_PY_CONTAINER
    log:
        'logs/03_official_umfi/designs.log'
    shell:
        'python -m sharedimp_exp.official_designs {input} ' + RAW + '/designs >& {log}'

rule representations_r:
    input:
        CONFIG,
        SOURCES
    output:
        RAW + '/representations_r.csv',
        RAW + '/gates.csv'
    container:
        EXP_R_CONTAINER
    log:
        'logs/03_official_umfi/representations_r.log'
    shell:
        'Rscript R/official_umfi.R representations {input} ' + RAW + ' >& {log}'

rule representations_official_py:
    input:
        CONFIG,
        SOURCES
    output:
        RAW + '/representations_official_py.csv'
    container:
        UMFI_PY_CONTAINER
    log:
        'logs/03_official_umfi/representations_official_py.log'
    shell:
        'python -m sharedimp_exp.official_py representations {input} {output} >& {log}'

rule representations_sharedimp_py:
    input:
        CONFIG
    output:
        RAW + '/representations_sharedimp_py.csv'
    container:
        PY_CONTAINER
    log:
        'logs/03_official_umfi/representations_sharedimp_py.log'
    shell:
        'python -m sharedimp_exp.official_sharedimp_py representations {input} {output} >& {log}'

rule identical_r:
    input:
        CONFIG,
        SOURCES
    output:
        RAW + '/identical_r.csv'
    container:
        EXP_R_CONTAINER
    log:
        'logs/03_official_umfi/identical_r.log'
    shell:
        'Rscript R/official_umfi.R identical {input} {output} >& {log}'

rule identical_python:
    input:
        CONFIG,
        SOURCES,
        RAW + '/representations_sharedimp_py.csv'
    output:
        RAW + '/identical_python.csv'
    container:
        UMFI_PY_CONTAINER
    log:
        'logs/03_official_umfi/identical_python.log'
    shell:
        'python -m sharedimp_exp.official_py replica {input} {output} >& {log}'

rule importance_r:
    input:
        CONFIG,
        SOURCES,
        RAW + '/designs/manifest.json',
        DESIGN_FILES
    output:
        RAW + '/importance/{design}.official_r.csv',
        RAW + '/importance/{design}.sharedimp_r.csv'
    container:
        EXP_R_CONTAINER
    benchmark:
        'benchmarks/03_official_umfi/importance_r_{design}.txt'
    log:
        'logs/03_official_umfi/importance_r_{design}.log'
    shell:
        'Rscript R/official_umfi.R importance {input[0]} {input[1]} ' + RAW + '/designs {wildcards.design} {output} >& {log}'

rule importance_official_py:
    input:
        CONFIG,
        SOURCES,
        RAW + '/designs/manifest.json',
        DESIGN_FILES
    output:
        RAW + '/importance/{design}.official_py.csv'
    container:
        UMFI_PY_CONTAINER
    benchmark:
        'benchmarks/03_official_umfi/importance_official_py_{design}.txt'
    log:
        'logs/03_official_umfi/importance_official_py_{design}.log'
    shell:
        'python -m sharedimp_exp.official_py importance {input[0]} {input[1]} ' + RAW + '/designs {wildcards.design} {output} >& {log}'

rule importance_sharedimp_py:
    input:
        CONFIG,
        RAW + '/designs/manifest.json',
        DESIGN_FILES
    output:
        RAW + '/importance/{design}.sharedimp_py.csv'
    container:
        PY_CONTAINER
    benchmark:
        'benchmarks/03_official_umfi/importance_sharedimp_py_{design}.txt'
    log:
        'logs/03_official_umfi/importance_sharedimp_py_{design}.log'
    shell:
        'python -m sharedimp_exp.official_sharedimp_py importance {input[0]} ' + RAW + '/designs {wildcards.design} {output} >& {log}'

rule leak:
    input:
        CONFIG,
        SOURCES
    output:
        RAW + '/leak.csv'
    container:
        EXP_R_CONTAINER
    log:
        'logs/03_official_umfi/leak.log'
    shell:
        'Rscript R/official_umfi.R leak {input} {output} >& {log}'

rule structural_r:
    input:
        CONFIG,
        SOURCES
    output:
        RAW + '/structural_r.json'
    container:
        EXP_R_CONTAINER
    log:
        'logs/03_official_umfi/structural_r.log'
    shell:
        'Rscript R/official_umfi.R structural {input} {output} >& {log}'

rule structural_python:
    input:
        CONFIG
    output:
        RAW + '/structural_python.json'
    container:
        PY_CONTAINER
    log:
        'logs/03_official_umfi/structural_python.log'
    shell:
        'python -m sharedimp_exp.official_sharedimp_py structural {input} {output} >& {log}'

rule api_r:
    input:
        CONFIG,
        SOURCES
    output:
        RAW + '/api_r.json'
    container:
        EXP_R_CONTAINER
    log:
        'logs/03_official_umfi/api_r.log'
    shell:
        'Rscript R/official_umfi.R api {input} {output} >& {log}'

rule api_official_py:
    input:
        CONFIG,
        SOURCES
    output:
        RAW + '/api_official_py.json'
    container:
        UMFI_PY_CONTAINER
    log:
        'logs/03_official_umfi/api_official_py.log'
    shell:
        'python -m sharedimp_exp.official_py api {input} {output} >& {log}'

rule api_sharedimp_py:
    input:
        CONFIG
    output:
        RAW + '/api_sharedimp_py.json'
    container:
        PY_CONTAINER
    log:
        'logs/03_official_umfi/api_sharedimp_py.log'
    shell:
        'python -m sharedimp_exp.official_sharedimp_py api {input} {output} >& {log}'

rule summary:
    input:
        CONFIG,
        'config/03_api_comparison.json',
        SOURCES,
        RAW + '/gates.csv',
        expand(RAW + '/representations_{impl}.csv', impl=['r', 'official_py', 'sharedimp_py']),
        expand(RAW + '/identical_{lang}.csv', lang=['r', 'python']),
        expand(RAW + '/importance/{design}.{impl}.csv', design=DESIGNS, impl=['official_r', 'sharedimp_r', 'official_py', 'sharedimp_py']),
        RAW + '/leak.csv',
        expand(RAW + '/structural_{lang}.json', lang=['r', 'python']),
        expand(RAW + '/api_{impl}.json', impl=['r', 'official_py', 'sharedimp_py'])
    output:
        expand(SUM + '/{name}.csv', name=SUMMARY),
        'results/tables/03_official_umfi.md',
        'results/tables/03_official_umfi_checks.md'
    container:
        PY_CONTAINER
    log:
        'logs/03_official_umfi/summary.log'
    shell:
        'python -m sharedimp_exp.official_summary {input[0]} {input[1]} ' + RAW + ' ' + SUM + ' >& {log}'
