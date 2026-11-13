# Container images

Every computation in this repository runs inside a container image through
Singularity (`snakemake --use-singularity`); nothing is installed on the host
except Snakemake and Singularity (`environment.yml`).

| image | used by | status |
|---|---|---|
| `ghcr.io/dsc-chiba-u/sharedimp-r@sha256:869dbec7…` (tag `cf2e1cc`) | workflows 01, 02: R side | published by the `sharedimp-r` CI; in use |
| `ghcr.io/dsc-chiba-u/sharedimp-py@sha256:c88b48a5…` (tag `bacc5d8`) | workflows 01, 02: Python side, checks; 04, 05 Python side | published by the `sharedimp-py` CI; in use |
| `koki/sharedimp-experiments-r:20261113` | 03 (sharedimp-r and official `HydroML/UMFI` in one R session), 04/05 R side, 06 figures | **to be built** from `docker/experiments-r/Dockerfile` |
| `koki/umfi-official-py:20261113` | 03 (official `guanton/umfi_python`, unmodified) | **to be built** from `docker/umfi-official-py/Dockerfile` |

The two package images are referenced by the digests in `config/pins.env`.
After the two images below are pushed, their digests are added to
`config/pins.env` in the same way and the workflows refer to them by digest.

```sh
docker build -t koki/sharedimp-experiments-r:20261113 docker/experiments-r
docker push koki/sharedimp-experiments-r:20261113
docker build -t koki/umfi-official-py:20261113 docker/umfi-official-py
docker push koki/umfi-official-py:20261113
```

Notes

- No official UMFI code is in any image (two of the three upstream
  repositories have no license); only its dependencies are.
- `docker/umfi-official-py` was checked on 2026-11-13 by installing the same
  pins with `pip` inside `docker://python:3.9-bookworm` under Singularity
  (all imports succeed, `minepy` builds). The Dockerfile itself has not been
  built here: this account cannot reach the Docker daemon.
- `docker/experiments-r` has not been built or tested here for the same reason.
- An image for building the manuscript (R Markdown, `rticles`, LaTeX with the
  Elsevier class) is not defined yet; it will be specified in Phase 4 after
  the SoftwareX template has been checked.
