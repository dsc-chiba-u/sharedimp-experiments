#!/usr/bin/env bash
# Experiment E: figures of Phase 2 (run workflows 01-04 first).
# Thin wrapper around workflow/06_figures.smk (see there for outputs);
# extra arguments go to snakemake, e.g. `--forceall` or `-n`.
. "$(dirname "$0")/_snakemake.sh"
run_workflow workflow/06_figures.smk "$@"
