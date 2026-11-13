#!/usr/bin/env bash
# Random-forest settings study (ranger vs scikit-learn).
# Thin wrapper around workflow/02b_rf_settings.smk (see there for outputs);
# extra arguments go to snakemake, e.g. `--forceall` or `-n`.
. "$(dirname "$0")/_snakemake.sh"
run_workflow workflow/02b_rf_settings.smk "$@"
