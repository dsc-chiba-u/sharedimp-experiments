"""Python counterparts of the learners named in the job files.

"linear" mirrors the R built-in `"linear"` learner (common specification 8.1):
closed-form OLS, unpenalized logistic regression, unpenalized multinomial
logistic regression. The logistic settings are those of the cross-language
test of sharedimp-py (tests/test_cross_language.py).

"rand_forest" mirrors the R built-in `"rand_forest"` learner as far as the
common specification 8.2 defines it (500 trees, mtry = floor(sqrt(q)),
min_n / min_samples_leaf = 5). The two forest implementations differ; no
numerical agreement between languages is expected or checked for it.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LinearRegression, LogisticRegression


def make_learner(name: str, task: str, n_classes: int | None, threads: int) -> tuple[Any, str]:
    if name == "linear":
        if task == "regression":
            return LinearRegression(), "LinearRegression()"
        if n_classes == 2:
            est = LogisticRegression(C=np.inf, solver="newton-cholesky", tol=1e-12, max_iter=1000)
            return est, "LogisticRegression(C=inf, solver='newton-cholesky', tol=1e-12, max_iter=1000)"
        est = LogisticRegression(C=np.inf, tol=1e-12, max_iter=20000)
        return est, "LogisticRegression(C=inf, solver='lbfgs', tol=1e-12, max_iter=20000)"
    if name == "rand_forest":
        kw = dict(n_estimators=500, min_samples_leaf=5, max_features="sqrt", bootstrap=True, n_jobs=threads)
        cls = RandomForestRegressor if task == "regression" else RandomForestClassifier
        return cls(**kw), f"{cls.__name__}({', '.join(f'{k}={v!r}' for k, v in kw.items())})"
    raise ValueError(f"unknown learner '{name}'")
