from pathlib import Path
import subprocess
import sys

FINAL = "2260b6f19d51a14d7c68770677f22d04dfd88022"
REL = "competition/agents/juraj_v35_cpp/main.cpp"

p = Path(sys.argv[1])
final_src = subprocess.check_output(["git", "show", f"{FINAL}:{REL}"], text=True)
old = "!enemy_seen?.20:.08"
new = "(production_==ProductionState::HEALTHY&&!enemy_seen&&o.turn<=50)?.29:(!enemy_seen?.20:.08)"
if final_src.count(old) != 1:
    raise SystemExit(f"final search-share anchor count={final_src.count(old)}")

# Candidate: final 2260b6f + exactly one gameplay change.
p.write_text(final_src.replace(old, new, 1))

# Baseline wrapper built by picker9-loop points at /tmp/parent. Replace only its
# ephemeral source with unmodified final so random screen is final+patch vs final.
parent = Path("/tmp/parent") / REL
if not parent.exists():
    raise SystemExit("ephemeral /tmp/parent source missing")
parent.write_text(final_src)

print("experiment=final_2260b6f_healthy_precontact_search_share_020_to_029_t50")
