#!/usr/bin/env bash
# Experiment C: screening of the candidates for the multiclass data set.
# Thin wrapper around workflow/04a_multiclass_selection.smk (see there for outputs);
# extra arguments go to snakemake, e.g. `--forceall` or `-n`.
. "$(dirname "$0")/_snakemake.sh"
run_workflow workflow/04a_multiclass_selection.smk "$@"
