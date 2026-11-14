# syntax=docker/dockerfile:1
#
# koki/sharedimp-manuscript
#
# Builds paper/manuscript.Rmd (workflow/07_manuscript.smk). The pinned
# sharedimp-experiments-r image (R 4.5.3, knitr, rmarkdown, ggplot2,
# patchwork, jsonlite) plus what the manuscript needs on top of it:
#   - pandoc                              : R Markdown -> LaTeX
#   - TeX Live (Ubuntu packages)          : pdflatex, bibtex, the Elsevier class elsarticle
#     (texlive-publishers) and the packages the template loads
#   - rticles, bookdown                   : the Elsevier article format and cross-references
# No experiment is run in this image.
#
# Built and pushed by .github/workflows/docker.yml to ghcr.io/dsc-chiba-u/sharedimp-manuscript
# (and docker.io/koki/sharedimp-manuscript when the Docker Hub secrets are set).
ARG EXP_R_DIGEST=sha256:803daedb5ce5b39246eefb63c823e0f0a7b5c8bb869f6d4283884d7142d84c1f
FROM ghcr.io/dsc-chiba-u/sharedimp-experiments-r@${EXP_R_DIGEST}

LABEL org.opencontainers.image.title="sharedimp-manuscript" \
      org.opencontainers.image.source="https://github.com/dsc-chiba-u/sharedimp-experiments" \
      org.opencontainers.image.description="Build environment of the sharedimp SoftwareX manuscript (R Markdown, rticles, TeX Live)"

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
         pandoc \
         texlive-latex-base texlive-latex-recommended texlive-latex-extra \
         texlive-fonts-recommended texlive-publishers texlive-bibtex-extra \
         texlive-science lmodern \
    && rm -rf /var/lib/apt/lists/*

RUN install2.r --error --skipinstalled --ncpus -1 rticles bookdown \
    && rm -rf /tmp/downloaded_packages /tmp/Rtmp*

# Build-time check: the Elsevier skeleton of rticles renders to PDF with the
# installed TeX Live (no package is downloaded at run time).
RUN mkdir /tmp/check && cd /tmp/check \
    && Rscript -e 'options(tinytex.install_packages = FALSE); rmarkdown::draft("check.Rmd", template = "elsevier", package = "rticles", create_dir = FALSE, edit = FALSE); rmarkdown::render("check.Rmd", quiet = TRUE)' \
    && test -s check.pdf \
    && Rscript -e 'for (p in c("rmarkdown", "knitr", "rticles", "bookdown", "ggplot2", "patchwork", "jsonlite")) library(p, character.only = TRUE); cat("pandoc", as.character(rmarkdown::pandoc_version()), "\n")' \
    && cd / && rm -rf /tmp/check

WORKDIR /work
CMD ["R"]
