#!/usr/bin/env bash
# Experiment D (Phase 3, not implemented yet: the workflow fails on purpose).
# Thin wrapper around workflow/05_runtime.smk (see there for outputs);
# extra arguments go to snakemake, e.g. `--forceall` or `-n`.
. "$(dirname "$0")/_snakemake.sh"
run_workflow workflow/05_runtime.smk "$@"
