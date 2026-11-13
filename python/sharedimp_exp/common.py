"""Paths, dataset loading and exact CSV/JSON output shared by the Python scripts."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(os.environ.get("SHAREDIMP_EXP_ROOT", Path(__file__).resolve().parents[2]))
DATA = ROOT / "data"
RESULTS = ROOT / "results"
FLOAT_FORMAT = "%.17g"  # round-trip exact for IEEE doubles


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(Path(path).read_text())


def write_json(obj: Any, path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=False, default=_jsonable) + "\n")


def _jsonable(o: Any) -> Any:
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, Path):
        return str(o)
    raise TypeError(f"not JSON serializable: {type(o)}")


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, float_format=FLOAT_FORMAT, na_rep="NA", lineterminator="\n")


def load_manifest(group: str) -> dict[str, Any]:
    """Read data/<group>/manifest.json (group: 'synthetic' or 'real')."""
    return read_json(DATA / group / "manifest.json")


def find_dataset(dataset_id: str) -> tuple[dict[str, Any], Path]:
    for group in ("synthetic", "real"):
        mpath = DATA / group / "manifest.json"
        if not mpath.exists():
            continue
        entry = read_json(mpath)["datasets"].get(dataset_id)
        if entry is not None:
            return entry, DATA / group / entry["file"]
    raise KeyError(f"dataset '{dataset_id}' is not in any data/*/manifest.json")


def load_dataset(dataset_id: str) -> dict[str, Any]:
    """Load a dataset and verify its checksum against the manifest."""
    entry, path = find_dataset(dataset_id)
    digest = sha256(path)
    if digest != entry["sha256"]:
        raise RuntimeError(f"{path}: sha256 {digest} != manifest {entry['sha256']}")
    df = pd.read_csv(path)
    X = df[entry["features"]].astype(float)
    y = df[entry["target"]]
    y = y.to_numpy(dtype=float) if entry["task"] == "regression" else y.astype(str).to_numpy()
    return {
        "id": dataset_id,
        "entry": entry,
        "X": X,
        "y": y,
        "fold": df[entry["fold"]].to_numpy(dtype=int),
        "sha256": digest,
    }


def splits_from_labels(fold: np.ndarray) -> tuple[list[int], list[tuple[np.ndarray, np.ndarray]]]:
    """Explicit splits, one per fold label in increasing order (same rule as R)."""
    labels = sorted(int(v) for v in np.unique(fold))
    idx = np.arange(len(fold))
    return labels, [(idx[fold != lab], idx[fold == lab]) for lab in labels]
