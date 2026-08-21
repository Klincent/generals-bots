from pathlib import Path
import sys

p = Path(sys.argv[1])
s = p.read_text()
old = "!enemy_seen?.20:.08"
new = "(production_==ProductionState::HEALTHY&&!enemy_seen&&o.turn<=50)?.29:(!enemy_seen?.20:.08)"
if old not in s:
    raise SystemExit("search-share anchor not found")
if s.count(old) != 1:
    raise SystemExit(f"search-share anchor count={s.count(old)}")
p.write_text(s.replace(old, new, 1))
print("experiment=healthy_precontact_search_share_020_to_029_t50")
