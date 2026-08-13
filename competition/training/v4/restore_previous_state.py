#!/usr/bin/env python3
"""Restore the newest compatible v41-final-training-state from an earlier PR run.

Uses only GITHUB_TOKEN + GitHub Actions REST API.  It never writes repository
contents; it only downloads an artifact into --state-dir.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import shutil
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

EXPECTED_PACK_VERSION = 2
EXPECTED_FEATURE_SCHEMA = 2


def api_json(url: str, token: str) -> dict:
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def api_bytes(url: str, token: str) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def compatible_checkpoint(root: Path) -> bool:
    cp = root / "checkpoint.json"
    if not cp.exists():
        return False
    try:
        data = json.loads(cp.read_text())
    except Exception:
        return False
    cfg = data.get("config", {})
    return (
        cfg.get("pack_version") == EXPECTED_PACK_VERSION
        and cfg.get("feature_schema") == EXPECTED_FEATURE_SCHEMA
        and cfg.get("env_mode") == "competition"
    )


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--state-dir", type=Path, required=True)
    p.add_argument("--workflow", default="v41-train.yml")
    a = p.parse_args()

    repo = os.environ.get("GITHUB_REPOSITORY", "")
    branch = os.environ.get("GITHUB_HEAD_REF") or os.environ.get("GITHUB_REF_NAME", "")
    token = os.environ.get("GITHUB_TOKEN", "")
    api = os.environ.get("GITHUB_API_URL", "https://api.github.com")
    current_run = int(os.environ.get("GITHUB_RUN_ID", "0") or 0)
    if not repo or not branch or not token:
        print("cross-run restore: GitHub context/token unavailable; starting fresh")
        a.state_dir.mkdir(parents=True, exist_ok=True)
        return 0

    workflow = urllib.parse.quote(a.workflow, safe="")
    q = urllib.parse.urlencode(
        {"branch": branch, "event": "pull_request", "status": "completed", "per_page": 30}
    )
    runs_url = f"{api}/repos/{repo}/actions/workflows/{workflow}/runs?{q}"
    runs = api_json(runs_url, token).get("workflow_runs", [])
    for run in runs:
        run_id = int(run.get("id", 0))
        if not run_id or run_id == current_run:
            continue
        arts_url = f"{api}/repos/{repo}/actions/runs/{run_id}/artifacts?per_page=100"
        artifacts = api_json(arts_url, token).get("artifacts", [])
        target = next(
            (
                x
                for x in artifacts
                if x.get("name") == "v41-final-training-state" and not x.get("expired", False)
            ),
            None,
        )
        if not target:
            continue
        artifact_id = int(target["id"])
        blob = api_bytes(f"{api}/repos/{repo}/actions/artifacts/{artifact_id}/zip", token)
        tmp = a.state_dir.with_name(a.state_dir.name + ".restore-tmp")
        if tmp.exists():
            shutil.rmtree(tmp)
        tmp.mkdir(parents=True)
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            z.extractall(tmp)
        # upload-artifact(path=training-state/) normally stores the directory
        # contents at the ZIP root, but accept one extra wrapper directory too.
        candidate = tmp
        if not (candidate / "checkpoint.json").exists():
            children = [x for x in tmp.iterdir() if x.is_dir()]
            if len(children) == 1 and (children[0] / "checkpoint.json").exists():
                candidate = children[0]
        if not compatible_checkpoint(candidate):
            print(f"cross-run restore: run {run_id} artifact incompatible; trying older run")
            shutil.rmtree(tmp)
            continue
        if a.state_dir.exists():
            shutil.rmtree(a.state_dir)
        if candidate == tmp:
            os.replace(tmp, a.state_dir)
        else:
            shutil.move(str(candidate), str(a.state_dir))
            shutil.rmtree(tmp, ignore_errors=True)
        cp = json.loads((a.state_dir / "checkpoint.json").read_text())
        print(
            "cross-run restore: restored run "
            f"{run_id}, games={cp.get('games', 0)}, pairs={cp.get('usable_pairs', 0)}"
        )
        return 0

    a.state_dir.mkdir(parents=True, exist_ok=True)
    print("cross-run restore: no compatible previous final state found; starting fresh")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
