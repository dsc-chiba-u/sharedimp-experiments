# Sourced by the numbered scripts: run one workflow inside the containers.
#   run_workflow workflow/NN_name.smk [extra snakemake arguments]
# Cores: $SHAREDIMP_EXP_CORES (default 4). Snakemake and Singularity are taken
# from the PATH, else from the conda environment `snakemake` (environment.yml).
# shellcheck shell=bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

if ! command -v snakemake >/dev/null 2>&1 || ! command -v singularity >/dev/null 2>&1; then
  if command -v conda >/dev/null 2>&1 && [ -x "$(conda info --base)/envs/snakemake/bin/snakemake" ]; then
    PATH="$(conda info --base)/envs/snakemake/bin:$PATH"
  else
    echo "error: snakemake and singularity not found; run 'conda env create -f environment.yml' and activate it." >&2
    exit 1
  fi
fi

# Singularity (without setuid) unpacks an image into a temporary sandbox for
# every job (0.4-1.3 GB each). On a nearly full system disk parallel jobs fail
# with "No space left on device"; use the RAM disk unless the caller chose a
# directory.
if [ -z "${SINGULARITY_TMPDIR:-}" ] && [ -d /dev/shm ] && [ -w /dev/shm ]; then
  export SINGULARITY_TMPDIR="/dev/shm/sharedimp-exp-$(id -u)"
  mkdir -p "$SINGULARITY_TMPDIR"
fi

run_workflow() {
  local smk="$1"; shift
  snakemake -s "$smk" --use-singularity --cores "${SHAREDIMP_EXP_CORES:-4}" --show-failed-logs "$@"
}
