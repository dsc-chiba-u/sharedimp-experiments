#!/usr/bin/env bash
# Validation of the two implementations in the experiment environment:
# classification smoke tests and the linear-Gaussian positive control.
# (Cross-language parity itself is tested in the packages; this script only
# confirms it on the data and through the runners used by the experiments.)
#
#   raw      results/raw/02_validation/{r,python}/<job>.{importance.csv,folds.csv,meta.json}
#   summary  results/summary/02_validation/{checks,parity,importance_long,positive_control}.csv
#   tables   results/tables/02_validation_checks.md
#
# The synthetic data are regenerated first and must reproduce the committed
# files byte for byte.
. "$(dirname "$0")/_common.sh"
RAW=results/raw/02_validation; SUM=results/summary/02_validation
rm -rf "$RAW" "$SUM"; mkdir -p "$RAW" "$SUM"

"$PYTHON" -m sharedimp_exp.make_synthetic --check

status=0
"$RSCRIPT" R/run_jobs.R config/02_validation_jobs.json "$RAW/r" || status=1
"$PYTHON" -m sharedimp_exp.run_jobs config/02_validation_jobs.json "$RAW/python" || status=1
"$PYTHON" -m sharedimp_exp.check_jobs config/02_validation_jobs.json "$RAW" "$SUM" || status=1
[ "$status" -eq 0 ] && log "OK" || { log "FAILED"; exit 1; }
