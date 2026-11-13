"""Record tags and digests of the public sharedimp container images.

python -m sharedimp_exp.docker_info results/raw/environment/docker_images.json

Uses only the anonymous read API of the registry (no Docker daemon needed), so
it also works where `docker` cannot be run. For each image it records the tag
list, the digest of `latest`, the digest of the tag named after the pinned
commit (the images are tagged with the 7-character commit SHA), and whether
the two digests are identical, i.e. whether `latest` *is* the pinned commit.
Nothing here asserts that the experiments ran inside these images; the
"experiments_ran_in_container" field says whether they did.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
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


def image_record(image: str, commit: str) -> dict:
    host, _, repo = image.partition("/")
    rec: dict = {"image": image, "pinned_commit": commit, "pinned_tag": commit[:7]}
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
        rec["status"] = "ok"
    except Exception as exc:  # network unavailable etc.: recorded, not hidden
        rec["status"] = "unavailable"
        rec.setdefault("errors", []).append(f"{type(exc).__name__}: {exc}")
    return rec


def docker_daemon() -> dict:
    exe = shutil.which("docker")
    if exe is None:
        return {"usable": False, "reason": "docker executable not found"}
    proc = subprocess.run([exe, "version", "--format", "{{.Server.Version}}"], capture_output=True, text=True)
    if proc.returncode == 0:
        return {"usable": True, "server_version": proc.stdout.strip()}
    return {"usable": False, "reason": (proc.stderr or proc.stdout).strip().splitlines()[-1][:300]}


def main(out: str) -> None:
    info = {
        "queried_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "docker_daemon": docker_daemon(),
        "experiments_ran_in_container": Path("/.dockerenv").exists(),
        "images": [
            image_record(os.environ["SHAREDIMP_R_IMAGE"], os.environ["SHAREDIMP_R_COMMIT"]),
            image_record(os.environ["SHAREDIMP_PY_IMAGE"], os.environ["SHAREDIMP_PY_COMMIT"]),
        ],
    }
    write_json(info, Path(out))
    for rec in info["images"]:
        print(
            f"[docker] {rec['image']}: {rec['status']}; latest={rec.get('digest_latest')}; "
            f"latest is pinned commit {rec['pinned_tag']}: {rec.get('latest_is_pinned_commit')}"
        )
    print(f"[docker] daemon usable: {info['docker_daemon']['usable']}")


if __name__ == "__main__":
    main(sys.argv[1])
