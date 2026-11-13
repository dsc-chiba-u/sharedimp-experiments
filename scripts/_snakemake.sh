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

run_workflow() {
  local smk="$1"; shift
  snakemake -s "$smk" --use-singularity --cores "${SHAREDIMP_EXP_CORES:-4}" --show-failed-logs "$@"
}
