from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import shutil
import subprocess
import sys

p = Path(sys.argv[1])
s = p.read_text()
old = "!enemy_seen?.20:.08"
new = "(production_==ProductionState::HEALTHY&&!enemy_seen&&o.turn<=50)?.28:(!enemy_seen?.20:.08)"
if old not in s:
    raise SystemExit("search-share anchor not found")
if s.count(old) != 1:
    raise SystemExit(f"search-share anchor count={s.count(old)}")
p.write_text(s.replace(old, new, 1))

# Also keep the ZIP inside the normal loop artifact.
out = Path("/tmp/random-v75")
out.mkdir(parents=True, exist_ok=True)
artifact_zip = out / "picker9-search-t50-submission.zip"
with ZipFile(artifact_zip, "w", ZIP_DEFLATED) as z:
    for name in ("main.cpp", "core.hpp", "build.sh", "run.sh"):
        z.write(p.with_name(name), arcname=name)

# Materialize the exact same tested candidate on the permanent submission branch.
branch = "submission/picker9-search-t50-20260821"
subdir = Path("/tmp/picker9-submission-branch")
if subdir.exists():
    shutil.rmtree(subdir)
subprocess.run(["git", "fetch", "origin", branch], check=True)
subprocess.run(["git", "worktree", "add", "-B", branch, str(subdir), f"origin/{branch}"], check=True)
agent_dir = subdir / "competition/agents/juraj_v35_cpp"
shutil.copy2(p, agent_dir / "main.cpp")
branch_zip = subdir / "picker9-search-t50-submission.zip"
with ZipFile(branch_zip, "w", ZIP_DEFLATED) as z:
    for name in ("main.cpp", "core.hpp", "build.sh", "run.sh"):
        z.write(agent_dir / name, arcname=name)
subprocess.run(["git", "-C", str(subdir), "config", "user.name", "ChatGPT"], check=True)
subprocess.run(["git", "-C", str(subdir), "config", "user.email", "actions@users.noreply.github.com"], check=True)
subprocess.run(["git", "-C", str(subdir), "add", "competition/agents/juraj_v35_cpp/main.cpp", "picker9-search-t50-submission.zip"], check=True)
changed = subprocess.run(["git", "-C", str(subdir), "diff", "--cached", "--quiet"]).returncode != 0
if changed:
    subprocess.run(["git", "-C", str(subdir), "commit", "-m", "submission: picker9 healthy precontact search boost t50"], check=True)
    subprocess.run(["git", "-C", str(subdir), "push", "origin", f"HEAD:{branch}"], check=True)

print("experiment=healthy_precontact_search_share_020_to_028_t50_submission_materialized")
print(f"submission_branch={branch}")
print(f"submission_zip={artifact_zip}")
