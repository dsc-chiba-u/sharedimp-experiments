#!/usr/bin/env bash
# Manuscript: paper figures, PDF and checks (Phase 4).
# Thin wrapper around workflow/07_manuscript.smk (see there for outputs);
# extra arguments go to snakemake, e.g. `--forceall` or `-n`.
. "$(dirname "$0")/_snakemake.sh"
run_workflow workflow/07_manuscript.smk "$@"
