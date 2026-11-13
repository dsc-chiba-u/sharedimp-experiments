# syntax=docker/dockerfile:1
#
# koki/sharedimp-experiments-r
#
# The published sharedimp-r image (pinned by digest: R 4.5.3, sharedimp at
# commit cf2e1cc, ranger, tidymodels, ggplot2) plus what the experiments need
# on top of it:
#   - doParallel, foreach, rje : Imports of the official R package HydroML/UMFI
#     (experiment B). The official *code* is NOT in this image: the workflow
#     fetches it at a pinned commit into external/ at run time.
#   - patchwork                : figure layout (experiment E)
# sharedimp itself is not reinstalled, so it stays the pinned commit.
#
#   docker build -t koki/sharedimp-experiments-r:20261113 docker/experiments-r
#   docker push koki/sharedimp-experiments-r:20261113
ARG SHAREDIMP_R_DIGEST=sha256:869dbec7077cfbfcea4f0da25d8ce51e1c4e6d4297106d11a965cada1d8a0805
FROM ghcr.io/dsc-chiba-u/sharedimp-r@${SHAREDIMP_R_DIGEST}

LABEL org.opencontainers.image.title="sharedimp-experiments-r" \
      org.opencontainers.image.source="https://github.com/dsc-chiba-u/sharedimp-experiments" \
      org.opencontainers.image.description="sharedimp-r plus the dependencies of the official UMFI R package and plotting packages"

# rocker/r-ver pins CRAN to the Posit Package Manager snapshot of the R
# release, so these versions are reproducible.
RUN install2.r --error --skipinstalled --ncpus -1 \
      doParallel foreach rje patchwork \
    && rm -rf /tmp/downloaded_packages /tmp/Rtmp*

# Build-time check: everything loads, and sharedimp is still version 0.1.0.
RUN Rscript -e 'for (p in c("sharedimp", "ranger", "doParallel", "foreach", "rje", "ggplot2", "patchwork", "jsonlite")) library(p, character.only = TRUE); stopifnot(packageVersion("sharedimp") == "0.1.0")'

WORKDIR /work
CMD ["R"]
