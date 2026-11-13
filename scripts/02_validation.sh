#!/usr/bin/env bash
# Validation: classification smoke tests and the positive control.
# Thin wrapper around workflow/02_validation.smk (see there for outputs);
# extra arguments go to snakemake, e.g. `--forceall` or `-n`.
. "$(dirname "$0")/_snakemake.sh"
run_workflow workflow/02_validation.smk "$@"
