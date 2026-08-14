#!/usr/bin/env python3
"""Download one known GitHub Actions artifact by ID and validate its training state."""
from __future__ import annotations

import argparse
import io
import os
import shutil
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

from validate_training_state_v41 import validate_state


class SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Never forward the GitHub bearer token to the signed storage host."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if redirected is None:
            return None
        old_host = urllib.parse.urlparse(req.full_url).netloc
        new_host = urllib.parse.urlparse(newurl).netloc
        if old_host != new_host:
            redirected.remove_header("Authorization")
            redirected.remove_header("Accept")
            redirected.remove_header("X-GitHub-Api-Version")
        return redirected


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--artifact-id", type=int, required=True)
    p.add_argument("--state-dir", type=Path, required=True)
    a = p.parse_args()

    repo = os.environ.get("GITHUB_REPOSITORY", "")
    token = os.environ.get("GITHUB_TOKEN", "")
    api = os.environ.get("GITHUB_API_URL", "https://api.github.com")
    if not repo or not token:
        raise SystemExit("GITHUB_REPOSITORY/GITHUB_TOKEN unavailable")

    url = f"{api}/repos/{repo}/actions/artifacts/{a.artifact_id}/zip"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    opener = urllib.request.build_opener(SafeRedirectHandler())
    with opener.open(req, timeout=180) as r:
        blob = r.read()

    tmp = a.state_dir.with_name(a.state_dir.name + ".download-tmp")
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        z.extractall(tmp)

    candidate = tmp
    if not (candidate / "checkpoint.json").exists():
        children = [x for x in tmp.iterdir() if x.is_dir()]
        if len(children) == 1 and (children[0] / "checkpoint.json").exists():
            candidate = children[0]

    result = validate_state(candidate)
    shutil.rmtree(a.state_dir, ignore_errors=True)
    if candidate == tmp:
        os.replace(tmp, a.state_dir)
    else:
        shutil.move(str(candidate), str(a.state_dir))
        shutil.rmtree(tmp, ignore_errors=True)
    print(
        f"downloaded artifact {a.artifact_id}: "
        f"games={result['checkpoint']['games']} pairs={result['checkpoint']['usable_pairs']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
