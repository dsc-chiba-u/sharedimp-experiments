#!/usr/bin/env bash
# Experiment B: comparison with the official UMFI-LR code.
# Thin wrapper around workflow/03_official_umfi.smk (see there for outputs);
# extra arguments go to snakemake, e.g. `--forceall` or `-n`.
. "$(dirname "$0")/_snakemake.sh"
run_workflow workflow/03_official_umfi.smk "$@"
