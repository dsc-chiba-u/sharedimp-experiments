#!/usr/bin/env bash
# Null-design forest study (follow-up of experiment B6).
# Thin wrapper around workflow/04c_null_forest.smk (see there for outputs);
# extra arguments go to snakemake, e.g. `--forceall` or `-n`.
. "$(dirname "$0")/_snakemake.sh"
run_workflow workflow/04c_null_forest.smk "$@"
