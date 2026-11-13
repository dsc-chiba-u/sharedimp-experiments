#!/usr/bin/env bash
# Experiment A: environment record and smoke test (n = 20, p = 3).
# Thin wrapper around workflow/01_environment.smk (see there for outputs);
# extra arguments go to snakemake, e.g. `--forceall` or `-n`.
. "$(dirname "$0")/_snakemake.sh"
run_workflow workflow/01_environment.smk "$@"
