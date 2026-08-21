from pathlib import Path
import sys

p = Path(sys.argv[1])
s = p.read_text()
old = "production_==ProductionState::SEVERE_DEFICIT?.62:production_==ProductionState::SOFT_DEFICIT?.45:.35"
new = "production_==ProductionState::SEVERE_DEFICIT?.62:production_==ProductionState::SOFT_DEFICIT?((!enemy_seen&&o.turn<=250)?.52:.45):((!enemy_seen&&o.turn<=250)?.40:.35)"
if old not in s:
    raise SystemExit("expansion-share anchor not found")
if s.count(old) != 1:
    raise SystemExit(f"expansion-share anchor count={s.count(old)}")
p.write_text(s.replace(old, new, 1))
print("experiment=healthy040_plus_soft052_precontact_t250")
