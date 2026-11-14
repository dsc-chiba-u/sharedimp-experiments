# Container images

Every computation in this repository runs inside a container image through
Singularity (`snakemake --use-singularity`); nothing is installed on the host
except Snakemake and Singularity (`environment.yml`). All images are
referenced by the digests in `config/pins.env`.

| image | built from | contents | used by |
|---|---|---|---|
| `ghcr.io/dsc-chiba-u/sharedimp-r` (tag `cf2e1cc`) | `sharedimp-r` repository, its CI | R 4.5.3, `sharedimp` (R) at the pinned commit | 01, 02, 02b, 04, 04a, 04b, 04c, 05 |
| `ghcr.io/dsc-chiba-u/sharedimp-py` (tag `bacc5d8`) | `sharedimp-py` repository, its CI | Python 3.13, `sharedimp` (Python) at the pinned commit | 01, 02, 02b, 03, 04, 04a, 04b, 04c, 05 |
| `ghcr.io/dsc-chiba-u/sharedimp-experiments-r` (tag `408e962`) | `docker/experiments-r/Dockerfile` | the `sharedimp-r` image (by digest) + `doParallel`, `foreach`, `rje` (Imports of the official R package `HydroML/UMFI`) + `patchwork` | 03, 06 |
| `ghcr.io/dsc-chiba-u/umfi-official-py` (tag `408e962`) | `docker/umfi-official-py/Dockerfile` | Python 3.9 and the packages of the official `umfi.yml` (numpy 1.26.4, pandas 2.2.1, scipy 1.13.1, scikit-learn 1.5.0, minepy 1.2.6, POT 0.9.3, ...) | 03 |

## Building

`.github/workflows/docker.yml` builds the two images of this directory on a
push to `main` that changes a Dockerfile (or by a manual run), and pushes
`latest` and the 7-character commit SHA to GHCR. Each Dockerfile ends with a
`RUN` that loads every package, so a successful build is a tested build.

After a rebuild that should be used: put the new digest and the commit of
this repository that built it (`PHASE2_IMAGES_COMMIT`) into `config/pins.env`
and re-run everything. Workflow 01 checks against the registry that each
pinned digest is the image tagged with that commit and carries it as its
`org.opencontainers.image.revision` label.

## Docker Hub

The workflow also pushes to `docker.io/koki/<name>` **if** the repository
secrets `DOCKER_USERNAME` and `DOCKER_PASSWORD` exist. On 2026-11-13 this
repository has no such secrets (the two package repositories have them), so
the images are on GHCR only and the run prints a warning. To publish on
Docker Hub as well: add the two secrets under Settings → Secrets and
variables → Actions and re-run the workflow ("Run workflow"). The image
content, and therefore the digest, is the same in both registries only if
the push comes from the same build; after such a re-run compare the digest
with `config/pins.env`.

## What the images do not contain

No official UMFI code (two of the three upstream repositories have no
license). `sharedimp-experiments-r` contains the *dependencies* of the
official R package; `umfi-official-py` the dependencies of the official
Python code. `umfi-official-py` does not contain sharedimp either
(sharedimp-py needs Python ≥ 3.10; `minepy`, which the official module
imports, did not build under Python 3.13 with default `pip` settings), so
the official Python code and sharedimp-py exchange CSV files.

An image for building the manuscript (R Markdown, `rticles`, LaTeX with the
Elsevier class) is not defined yet; it will be specified in Phase 4 after
the SoftwareX template has been checked.
