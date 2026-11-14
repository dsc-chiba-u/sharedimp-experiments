#!/usr/bin/env bash
# Experiment C, follow-up: duplicated rows of the Maternal Health Risk data.
# Thin wrapper around workflow/04b_maternal.smk (see there for outputs);
# extra arguments go to snakemake, e.g. `--forceall` or `-n`.
. "$(dirname "$0")/_snakemake.sh"
run_workflow workflow/04b_maternal.smk "$@"
