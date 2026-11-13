# Sourced by every numbered script. Resolves the repository root and the conda
# environment, pins the number of threads, and defines $RSCRIPT / $PYTHON.
# shellcheck shell=bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export SHAREDIMP_EXP_ROOT="$ROOT"
cd "$ROOT"

# shellcheck disable=SC1091
set -a; . "$ROOT/config/pins.env"; set +a

# Environment prefix: $SHAREDIMP_EXP_ENV, else the active env if it is
# sharedimp-exp, else <conda base>/envs/sharedimp-exp.
if [ -z "${SHAREDIMP_EXP_ENV:-}" ]; then
  if [ "$(basename "${CONDA_PREFIX:-}")" = "sharedimp-exp" ]; then
    SHAREDIMP_EXP_ENV="$CONDA_PREFIX"
  elif command -v conda >/dev/null 2>&1; then
    SHAREDIMP_EXP_ENV="$(conda info --base)/envs/sharedimp-exp"
  fi
fi
if [ ! -x "${SHAREDIMP_EXP_ENV:-/nonexistent}/bin/Rscript" ] || [ ! -x "$SHAREDIMP_EXP_ENV/bin/python" ]; then
  echo "error: environment not found at '${SHAREDIMP_EXP_ENV:-}'." >&2
  echo "       Run 'mamba env create -f environment.yml' or set SHAREDIMP_EXP_ENV." >&2
  exit 1
fi
export SHAREDIMP_EXP_ENV
export PATH="$SHAREDIMP_EXP_ENV/bin:$PATH"
RSCRIPT="$SHAREDIMP_EXP_ENV/bin/Rscript"
PYTHON="$SHAREDIMP_EXP_ENV/bin/python"
export SHAREDIMP_INSTALL_MANIFEST="$SHAREDIMP_EXP_ENV/share/sharedimp-experiments/install_manifest.json"

# Thread control: one thread everywhere unless the caller overrides
# SHAREDIMP_EXP_THREADS. Recorded in every result's metadata.
export SHAREDIMP_EXP_THREADS="${SHAREDIMP_EXP_THREADS:-1}"
export OMP_NUM_THREADS="$SHAREDIMP_EXP_THREADS"
export OPENBLAS_NUM_THREADS="$SHAREDIMP_EXP_THREADS"
export MKL_NUM_THREADS="$SHAREDIMP_EXP_THREADS"
export R_RANGER_NUM_THREADS="$SHAREDIMP_EXP_THREADS"

# Keep the run independent of the user's own R/Python configuration.
export R_PROFILE_USER=/dev/null R_ENVIRON_USER=/dev/null R_LIBS_USER=/nonexistent R_LIBS=
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$ROOT/python"
export LC_ALL=C.UTF-8 TZ=UTC

log() { printf '[%s] %s\n' "$(basename "$0")" "$*"; }
