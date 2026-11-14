#!/usr/bin/env bash
# Experiment D: runtime benchmark. `bash scripts/05_runtime.sh pilot` runs the
# pilot and writes the plan; without a target the main benchmark follows.
# Thin wrapper around workflow/05_runtime.smk; one core, so that nothing else
# of the workflow runs next to a timing process. Do not run other work on the
# machine at the same time.
. "$(dirname "$0")/_snakemake.sh"
SHAREDIMP_EXP_CORES=1 run_workflow workflow/05_runtime.smk "$@"
