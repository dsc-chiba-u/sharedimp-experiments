"""Record and verify the container images pinned in config/pins.env.

    python -m sharedimp_exp.docker_info results/raw/01_environment/docker_images.json

Uses only the anonymous read API of the registry (no Docker daemon). For each
image it records the tag list, the digest of `latest`, the digest of the tag
named after the pinned commit (the package CI tags images with the
7-character commit SHA), the pinned digest the workflows actually run, and the
`org.opencontainers.image.revision` label stored in that pinned image.

Exit status 1 if the registry answers and
  - the pinned digest is not the digest of the commit tag, or
  - the revision label of the pinned image is not the pinned commit.
If the registry cannot be reached, the record says "unavailable" and the
checks are null (recorded, not hidden); the workflows still run the images by
digest, so what ran is unchanged.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from .common import write_json

ACCEPT = ", ".join(
    [
        "application/vnd.oci.image.index.v1+json",
        "application/vnd.docker.distribution.manifest.list.v2+json",
        "application/vnd.oci.image.manifest.v1+json",
        "application/vnd.docker.distribution.manifest.v2+json",
    ]
)


def _get(url: str, token: str | None = None, method: str = "GET"):
    req = urllib.request.Request(url, method=method, headers={"Accept": ACCEPT, "User-Agent": "sharedimp-experiments"})
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    return urllib.request.urlopen(req, timeout=30)


def _revision(host: str, repo: str, ref: str, token: str) -> str | None:
    """Revision label of the linux/amd64 image behind a tag or digest."""
    manifest = json.load(_get(f"https://{host}/v2/{repo}/manifests/{ref}", token))
    if "manifests" in manifest:  # image index: pick linux/amd64
        digest = next(
            m["digest"]
            for m in manifest["manifests"]
            if m.get("platform", {}).get("architecture") == "amd64" and m.get("platform", {}).get("os") == "linux"
        )
        manifest = json.load(_get(f"https://{host}/v2/{repo}/manifests/{digest}", token))
    config = json.load(_get(f"https://{host}/v2/{repo}/blobs/{manifest['config']['digest']}", token))
    return (config.get("config", {}).get("Labels") or {}).get("org.opencontainers.image.revision")


def image_record(image: str, commit: str, pinned_digest: str) -> dict:
    host, _, repo = image.partition("/")
    rec: dict = {
        "image": image,
        "pinned_commit": commit,
        "pinned_tag": commit[:7],
        "pinned_digest": pinned_digest,
        "pinned_digest_is_commit_tag": None,
        "revision_label_is_pinned_commit": None,
    }
    try:
        token = json.load(_get(f"https://{host}/token?scope=repository:{repo}:pull"))["token"]
        rec["tags"] = json.load(_get(f"https://{host}/v2/{repo}/tags/list", token))["tags"]
        digests = {}
        for tag in ("latest", commit[:7]):
            try:
                digests[tag] = _get(f"https://{host}/v2/{repo}/manifests/{tag}", token, "HEAD").headers.get(
                    "docker-content-digest"
                )
            except urllib.error.HTTPError as exc:
                digests[tag] = None
                rec.setdefault("errors", []).append(f"{tag}: HTTP {exc.code}")
        rec["digest_latest"] = digests["latest"]
        rec["digest_pinned_tag"] = digests[commit[:7]]
        rec["latest_is_pinned_commit"] = (
            digests["latest"] is not None and digests["latest"] == digests[commit[:7]]
        )
        rec["pinned_digest_is_commit_tag"] = digests[commit[:7]] == pinned_digest
        rec["revision_label"] = _revision(host, repo, pinned_digest, token)
        rec["revision_label_is_pinned_commit"] = rec["revision_label"] == commit
        rec["status"] = "ok"
    except Exception as exc:  # network unavailable etc.: recorded, not hidden
        rec["status"] = "unavailable"
        rec.setdefault("errors", []).append(f"{type(exc).__name__}: {exc}")
    return rec


def main(out: str) -> int:
    env = os.environ
    info = {
        "queried_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "images": [
            image_record(env["SHAREDIMP_R_IMAGE"], env["SHAREDIMP_R_COMMIT"], env["SHAREDIMP_R_IMAGE_DIGEST"]),
            image_record(env["SHAREDIMP_PY_IMAGE"], env["SHAREDIMP_PY_COMMIT"], env["SHAREDIMP_PY_IMAGE_DIGEST"]),
        ],
    }
    write_json(info, Path(out))
    bad = False
    for rec in info["images"]:
        print(
            f"[docker] {rec['image']}@{rec['pinned_digest']}: {rec['status']}; "
            f"is tag {rec['pinned_tag']}: {rec['pinned_digest_is_commit_tag']}; "
            f"revision label is pinned commit: {rec['revision_label_is_pinned_commit']}; "
            f"latest is pinned commit: {rec.get('latest_is_pinned_commit')}"
        )
        if rec["status"] == "ok" and not (rec["pinned_digest_is_commit_tag"] and rec["revision_label_is_pinned_commit"]):
            print(f"[docker] ERROR {rec['image']}: pinned digest does not identify the pinned commit", file=sys.stderr)
            bad = True
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
