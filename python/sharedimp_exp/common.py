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


def container_record() -> dict[str, Any] | None:
    """The Singularity image this process runs in (None outside a container).

    Singularity stores the reference the image was built from in
    /.singularity.d/labels.json; the workflows reference images by digest.
    """
    labels = Path("/.singularity.d/labels.json")
    if not labels.is_file():
        return None
    lab = read_json(labels)
    return {
        "runtime": "singularity",
        "runtime_version": lab.get("org.label-schema.usage.singularity.version"),
        "image": lab.get("org.label-schema.usage.singularity.deffile.from"),
    }


def pinned_image(lang: str) -> str:
    """`<image>@<digest>` pinned in config/pins.env for lang = 'R' or 'PY'."""
    return f"{os.environ[f'SHAREDIMP_{lang}_IMAGE']}@{os.environ[f'SHAREDIMP_{lang}_IMAGE_DIGEST']}"


def provenance(lang: str) -> dict[str, Any]:
    """Container and commit fields written into every raw result.

    `sharedimp_commit` is the pinned commit only if the process runs inside
    the pinned image (whose revision label docker_info.py checks against the
    pin); otherwise it is null, because nothing else identifies the commit.
    """
    rec = container_record()
    in_pinned = rec is not None and rec["image"] == pinned_image(lang)
    return {
        "container": rec,
        "in_pinned_image": in_pinned,
        "sharedimp_commit": os.environ[f"SHAREDIMP_{lang}_COMMIT"] if in_pinned else None,
        "experiments_commit": os.environ.get("SHAREDIMP_EXP_COMMIT") or None,
        "experiments_code_dirty": os.environ.get("SHAREDIMP_EXP_DIRTY") == "1",
    }


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, float_format=FLOAT_FORMAT, na_rep="NA", lineterminator="\n")


def load_manifest(group: str) -> dict[str, Any]:
    """Read data/<group>/manifest.json (group: 'synthetic' or 'real')."""
    return read_json(DATA / group / "manifest.json")


def find_dataset(dataset_id: str, manifest_dir: Path | None = None) -> tuple[dict[str, Any], Path]:
    """Look a data set up in `manifest_dir` (if given), then in data/synthetic and data/real."""
    dirs = ([Path(manifest_dir)] if manifest_dir is not None else []) + [DATA / "synthetic", DATA / "real"]
    for d in dirs:
        mpath = d / "manifest.json"
        if not mpath.exists():
            continue
        entry = read_json(mpath)["datasets"].get(dataset_id)
        if entry is not None:
            return entry, d / entry["file"]
    raise KeyError(f"dataset '{dataset_id}' is not in any manifest.json")


def load_dataset(dataset_id: str, manifest_dir: Path | None = None) -> dict[str, Any]:
    """Load a dataset and verify its checksum against the manifest."""
    entry, path = find_dataset(dataset_id, manifest_dir)
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
