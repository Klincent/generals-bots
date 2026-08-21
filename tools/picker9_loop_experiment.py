from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
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

out = Path("/tmp/random-v75")
out.mkdir(parents=True, exist_ok=True)
zip_path = out / "picker9-search-t50-submission.zip"
with ZipFile(zip_path, "w", ZIP_DEFLATED) as z:
    for name in ("main.cpp", "core.hpp", "build.sh", "run.sh"):
        src = p.with_name(name)
        z.write(src, arcname=name)

print("experiment=healthy_precontact_search_share_020_to_028_t50_submission")
print(f"submission_zip={zip_path}")
