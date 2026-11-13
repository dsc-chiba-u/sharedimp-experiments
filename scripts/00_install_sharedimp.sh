#!/usr/bin/env bash
# Install the two sharedimp packages at the commits pinned in config/pins.env
# into the sharedimp-exp environment, from `git archive` snapshots (never from
# a working tree, never in editable mode), and record what was installed.
#
# Source of each snapshot: the sibling checkout (../sharedimp-r, ../sharedimp-py)
# if it contains the pinned commit, otherwise a fresh clone of the public
# repository. The sibling checkouts are only read.
. "$(dirname "$0")/_common.sh"

WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"' EXIT

snapshot() { # name sibling_dir repo commit -> prints "<dir> <source>"
  local name="$1" sib="$2" repo="$3" commit="$4" src
  if git -C "$sib" cat-file -e "${commit}^{commit}" 2>/dev/null; then
    src="$sib"
  else
    log "$name: pinned commit not in $sib; cloning $repo" >&2
    git clone --quiet "$repo" "$WORK/$name.git" >&2
    src="$WORK/$name.git"
  fi
  mkdir -p "$WORK/$name"
  git -C "$src" archive "$commit" | tar -x -C "$WORK/$name"
  if [ "$src" = "$sib" ]; then echo "$WORK/$name sibling-checkout"; else echo "$WORK/$name $repo"; fi
}

read -r R_DIR R_SRC < <(snapshot sharedimp-r "$ROOT/../sharedimp-r" "$SHAREDIMP_R_REPO" "$SHAREDIMP_R_COMMIT")
read -r PY_DIR PY_SRC < <(snapshot sharedimp-py "$ROOT/../sharedimp-py" "$SHAREDIMP_PY_REPO" "$SHAREDIMP_PY_COMMIT")

log "installing R package at $SHAREDIMP_R_COMMIT"
"$SHAREDIMP_EXP_ENV/bin/R" CMD INSTALL --no-test-load "$R_DIR" >"$WORK/r_install.log" 2>&1 \
  || { cat "$WORK/r_install.log" >&2; exit 1; }

log "installing Python package at $SHAREDIMP_PY_COMMIT"
"$PYTHON" -m pip uninstall -y sharedimp >/dev/null 2>&1 || true
"$PYTHON" -m pip install --no-deps --no-build-isolation --no-cache-dir "$PY_DIR" >"$WORK/py_install.log" 2>&1 \
  || { cat "$WORK/py_install.log" >&2; exit 1; }

mkdir -p "$(dirname "$SHAREDIMP_INSTALL_MANIFEST")"
R_VER="$("$RSCRIPT" -e 'cat(as.character(utils::packageVersion("sharedimp")))')"
PY_VER="$("$PYTHON" -c 'import sharedimp; print(sharedimp.__version__)')"
cat >"$SHAREDIMP_INSTALL_MANIFEST" <<JSON
{
  "installed_at_utc": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "method": "git archive <commit> | R CMD INSTALL / pip install --no-deps (non-editable)",
  "sharedimp_r": {"commit": "$SHAREDIMP_R_COMMIT", "repo": "$SHAREDIMP_R_REPO", "source": "$R_SRC", "version": "$R_VER"},
  "sharedimp_py": {"commit": "$SHAREDIMP_PY_COMMIT", "repo": "$SHAREDIMP_PY_REPO", "source": "$PY_SRC", "version": "$PY_VER"}
}
JSON
log "R sharedimp $R_VER, Python sharedimp $PY_VER"
log "manifest: $SHAREDIMP_INSTALL_MANIFEST"
