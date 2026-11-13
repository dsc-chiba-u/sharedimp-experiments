"""Generate the synthetic data sets of Phase 1 (smoke tests, positive control).

    python -m sharedimp_exp.make_synthetic            # (re)write the files
    python -m sharedimp_exp.make_synthetic --check    # regenerate elsewhere and compare

Writes data/synthetic/*.csv and data/synthetic/manifest.json. Everything is a
deterministic function of the seeds below (NumPy PCG64). Values are rounded to
6 decimals before writing, so the CSV text *is* the data: R and Python parse
identical doubles from it. Fold labels are stored in the `fold` column and are
the only source of train/assessment splits in both languages.

The files are committed; re-running this script must reproduce them byte for
byte. `--check` regenerates everything in a temporary directory, compares it
with the committed files and exits with status 1 on any difference
(used by workflow/02_validation.smk, which passes a file name after `--check`
to which the list of compared files and their sha256 is written).
"""

from __future__ import annotations

import filecmp
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from .common import DATA, sha256, write_json

OUT = DATA / "synthetic"
DECIMALS = 6


def balanced_folds(rng: np.random.Generator, n: int, v: int, strata: np.ndarray | None = None) -> np.ndarray:
    """Fold labels 1..v from a seeded permutation, balanced (within strata if given)."""
    fold = np.empty(n, dtype=int)
    groups = [np.arange(n)] if strata is None else [np.flatnonzero(strata == s) for s in np.unique(strata)]
    offset = 0
    for idx in groups:
        perm = rng.permutation(idx)
        fold[perm] = (np.arange(len(idx)) + offset) % v + 1
        offset += len(idx)
    return fold


def smoke_regression(seed: int = 20261113, n: int = 20, v: int = 4):
    rng = np.random.default_rng(seed)
    x1 = rng.normal(size=n)
    x2 = 0.7 * x1 + 0.7 * rng.normal(size=n)  # correlated with x1
    x3 = rng.normal(size=n)  # independent of x1, x2; no effect on y
    y = 1.5 * x1 - 1.0 * x2 + 0.5 * rng.normal(size=n)
    df = pd.DataFrame({"fold": balanced_folds(rng, n, v), "y": y, "x1": x1, "x2": x2, "x3": x3})
    gen = {"seed": seed, "n": n, "v": v, "model": "x1~N(0,1); x2=0.7*x1+0.7*N(0,1); x3~N(0,1); y=1.5*x1-x2+0.5*N(0,1)"}
    return df, "regression", gen, None


def smoke_classification(k: int, seed: int, n: int, v: int = 3):
    """Noisy labels (no separation) so that unpenalized logistic regression is well defined."""
    rng = np.random.default_rng(seed)
    x1 = rng.normal(size=n)
    x2 = 0.7 * x1 + 0.7 * rng.normal(size=n)
    x3 = rng.normal(size=n)
    if k == 2:
        eta = np.column_stack([np.zeros(n), 1.0 * x1 - 0.8 * x2])
        model = "P(y=b) = logistic(x1 - 0.8*x2)"
    else:
        eta = np.column_stack([np.zeros(n), 1.0 * x1 - 0.8 * x2, -1.0 * x1 + 0.5 * x3])
        model = "softmax(0, x1 - 0.8*x2, -x1 + 0.5*x3)"
    prob = np.exp(eta - eta.max(axis=1, keepdims=True))
    prob /= prob.sum(axis=1, keepdims=True)
    u = rng.uniform(size=n)
    y = np.array(list("abc"))[(u[:, None] > prob.cumsum(axis=1)).sum(axis=1).clip(max=k - 1)]
    df = pd.DataFrame({"fold": balanced_folds(rng, n, v, strata=y), "y": y, "x1": x1, "x2": x2, "x3": x3})
    gen = {"seed": seed, "n": n, "v": v, "model": f"x as in smoke_regression; {model}; folds stratified by y"}
    return df, "classification", gen, None


def positive_control(seed: int = 20261114, n: int = 2000, v: int = 5):
    """Linear-Gaussian design with a closed-form target for OLS + MSE.

    With an OLS learner the Full model spans the same space as the raw
    features and the Reduced model is orthogonal to the anchor, so the
    population MSE importance of anchor i is Cov(y, x_i)^2 / Var(x_i)
    (derivation in docs/experiment_plan.md).
    """
    rng = np.random.default_rng(seed)
    x1 = rng.normal(size=n)  # direct effect 2
    x2 = 0.8 * x1 + 0.6 * rng.normal(size=n)  # no direct effect; corr(x1, x2) = 0.8
    x3 = rng.normal(size=n)  # direct effect 1
    x4 = rng.normal(size=n)  # pure noise
    x5 = x3 + 0.1 * rng.normal(size=n)  # near-duplicate of x3, no direct effect
    y = 2.0 * x1 + 1.0 * x3 + rng.normal(size=n)
    df = pd.DataFrame({"fold": balanced_folds(rng, n, v), "y": y, "x1": x1, "x2": x2, "x3": x3, "x4": x4, "x5": x5})
    gen = {
        "seed": seed,
        "n": n,
        "v": v,
        "model": "x1,x3,x4~N(0,1); x2=0.8*x1+0.6*N(0,1); x5=x3+0.1*N(0,1); y=2*x1+x3+N(0,1)",
    }
    reference = {
        "quantity": "MSE importance of UMFI-LR with an OLS learner: Cov(y, x_i)^2 / Var(x_i)",
        "population": {"x1": 4.0, "x2": 1.6**2, "x3": 1.0, "x4": 0.0, "x5": 1.0 / 1.01},
    }
    return df, "regression", gen, reference


def generate(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    specs = {
        "smoke_reg_n20_p3": smoke_regression(),
        "smoke_bin_n60_p3": smoke_classification(2, seed=20261115, n=60),
        "smoke_multi_n90_p3": smoke_classification(3, seed=20261116, n=90),
        "pc_linear_n2000_p5": positive_control(),
    }
    datasets = {}
    for name, (df, task, gen, reference) in specs.items():
        num = df.select_dtypes("float").columns
        df[num] = df[num].round(DECIMALS)
        path = out / f"{name}.csv"
        df.to_csv(path, index=False, float_format=f"%.{DECIMALS}f", lineterminator="\n")
        df = pd.read_csv(path)  # what every consumer will see
        features = [c for c in df.columns if c not in ("fold", "y")]
        entry = {
            "file": path.name,
            "task": task,
            "target": "y",
            "fold": "fold",
            "features": features,
            "n": len(df),
            "p": len(features),
            "n_folds": int(df["fold"].nunique()),
            "sha256": sha256(path),
            "generator": {"script": "python/sharedimp_exp/make_synthetic.py", "decimals": DECIMALS, **gen},
        }
        if task == "classification":
            entry["classes"] = sorted(df["y"].unique().tolist())
            entry["class_counts"] = {k: int(v) for k, v in df["y"].value_counts().sort_index().items()}
        if reference is not None:
            # Full-sample plug-in of the same closed form, computed from the stored values.
            y = df["y"].to_numpy()
            reference["sample_plugin"] = {
                f: float(np.cov(df[f], y, ddof=0)[0, 1] ** 2 / np.var(df[f])) for f in features
            }
            entry["reference"] = reference
        datasets[name] = entry
        print(f"{path.name}: n={entry['n']} p={entry['p']} folds={entry['n_folds']} sha256={entry['sha256'][:12]}")
    write_json({"description": "Synthetic data of Phase 1; see generator docstrings.", "datasets": datasets}, out / "manifest.json")


def main(argv: list[str]) -> int:
    if "--check" not in argv:
        generate(OUT)
        return 0
    with tempfile.TemporaryDirectory() as tmp:
        generate(Path(tmp))
        names = sorted(p.name for p in Path(tmp).iterdir())
        _, mismatch, errors = filecmp.cmpfiles(tmp, OUT, names, shallow=False)
    for name in mismatch + errors:
        print(f"ERROR: regenerated {name} differs from data/synthetic/{name}", file=sys.stderr)
    if not (mismatch or errors):
        print(f"[make_synthetic] {len(names)} files reproduce data/synthetic byte for byte")
        record = [a for a in argv[1:] if a != "--check"]
        if record:
            write_json({"reproduced_byte_for_byte": True, "files": {n: sha256(OUT / n) for n in names}}, Path(record[0]))
    return 1 if (mismatch or errors) else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
