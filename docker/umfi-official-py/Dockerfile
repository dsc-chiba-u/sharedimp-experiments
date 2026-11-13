# syntax=docker/dockerfile:1
#
# koki/umfi-official-py
#
# Environment for running the official Python UMFI code (guanton/umfi_python)
# unmodified in experiment B. Versions follow that repository's `umfi.yml`
# (Python 3.9, numpy 1.26.4, pandas 2.2.1, scipy 1.13.1, scikit-learn 1.5.0,
# minepy 1.2.6, POT 0.9.3, ...). The official *code* is NOT in this image (the
# repository has no license): the workflow fetches it at a pinned commit into
# external/ at run time. sharedimp is not installed here either (it needs
# Python >= 3.10); the two sides exchange CSV files.
#
#   docker build -t koki/umfi-official-py:20261113 docker/umfi-official-py
#   docker push koki/umfi-official-py:20261113
FROM python:3.9-slim-bookworm

LABEL org.opencontainers.image.title="umfi-official-py" \
      org.opencontainers.image.source="https://github.com/dsc-chiba-u/sharedimp-experiments" \
      org.opencontainers.image.description="Dependencies of the official Python UMFI code at the versions of its umfi.yml (code not included)"

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# minepy 1.2.6 has no wheel and its setup.py imports numpy, so numpy goes in
# first and minepy is built without build isolation (needs a C compiler).
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && pip install numpy==1.26.4 setuptools wheel \
    && pip install --no-build-isolation minepy==1.2.6 \
    && pip install \
         pandas==2.2.1 scipy==1.13.1 scikit-learn==1.5.0 threadpoolctl==3.5.0 joblib==1.4.0 \
         POT==0.9.3 tqdm==4.66.4 matplotlib==3.8.4 seaborn==0.12.2 pyreadr==0.5.0 statsmodels==0.14.2

# Build-time check: every import of the official modules resolves.
RUN python -c "import numpy, pandas, scipy, sklearn, ot, tqdm, matplotlib, seaborn, pyreadr, statsmodels; from minepy import MINE; MINE(); assert numpy.__version__ == '1.26.4' and sklearn.__version__ == '1.5.0'"

WORKDIR /work
CMD ["python"]
