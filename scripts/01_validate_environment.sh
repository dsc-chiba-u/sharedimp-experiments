#!/usr/bin/env bash
# Experiment A: environment record and smoke test (n = 20, p = 3).
#
#   raw      results/raw/01_environment/{system,r,python,docker_images}.json
#            results/raw/01_environment/{r,python}/<job>.{importance.csv,folds.csv,meta.json}
#   summary  results/summary/01_environment/{environment,checks,parity,importance_long}.csv
#   tables   results/tables/01_environment.md, results/tables/01_environment_checks.md
#
# Fails if the installed sharedimp packages are not the pinned commits, if a
# job fails in either language, or if a check fails.
. "$(dirname "$0")/_common.sh"
RAW=results/raw/01_environment; SUM=results/summary/01_environment
rm -rf "$RAW" "$SUM"; mkdir -p "$RAW" "$SUM"

"$PYTHON" -m sharedimp_exp.system_info "$RAW/system.json"
"$RSCRIPT" R/env_info.R "$RAW/r.json"
"$PYTHON" -m sharedimp_exp.env_info "$RAW/python.json"
"$PYTHON" -m sharedimp_exp.docker_info "$RAW/docker_images.json"
"$PYTHON" -m sharedimp_exp.env_summary "$RAW" "$SUM"

status=0
"$RSCRIPT" R/run_jobs.R config/01_smoke_jobs.json "$RAW/r" || status=1
"$PYTHON" -m sharedimp_exp.run_jobs config/01_smoke_jobs.json "$RAW/python" || status=1
"$PYTHON" -m sharedimp_exp.check_jobs config/01_smoke_jobs.json "$RAW" "$SUM" || status=1
[ "$status" -eq 0 ] && log "OK" || { log "FAILED"; exit 1; }
