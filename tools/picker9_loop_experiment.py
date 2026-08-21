from pathlib import Path
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

build = p.with_name("build.sh")
b = build.read_text()
hook = r'''

# picker9-loop hard holdout hook; injected only in the ephemeral Actions worktree.
if [[ ! -e /tmp/picker9-hard-holdout-ran ]]; then
  touch /tmp/picker9-hard-holdout-ran
  cat >/tmp/picker9-holdout-candidate.sh <<'EOF'
#!/usr/bin/env bash
export V35_PICKER_ENABLED=1 V35_DOOMGUARD_ENABLED=1
exec "$GITHUB_WORKSPACE/competition/agents/juraj_v35_cpp/run.sh" "$@"
EOF
  chmod +x /tmp/picker9-holdout-candidate.sh

  refs=(
    "v35-champion-70fresh"
    "origin/v35-defense-fresh"
    "origin/v35-heuristic-rebuild"
    "origin/v35-logistics-recenter"
    "origin/juraj-v3.6-iter1-attack-pass"
    "origin/juraj-v3.6-search-refactor"
  )
  names=(
    "v35-champion-70fresh"
    "v35-defense-fresh"
    "v35-heuristic-rebuild"
    "v35-logistics-recenter"
    "juraj-v3.6-iter1-attack-pass"
    "juraj-v3.6-search-refactor"
  )

  for i in "${!refs[@]}"; do
    dir="/tmp/picker9-holdout-${i}"
    out="/tmp/picker9-holdout-out-${i}"
    git worktree add --detach "$dir" "${refs[$i]}"
    bash "$dir/competition/agents/juraj_v35_cpp/build.sh"
    echo "=== HARD_HOLDOUT ${names[$i]} ==="
    python competition/agents/juraj_v35_cpp/paired_benchmark.py \
      --candidate /tmp/picker9-holdout-candidate.sh \
      --baseline "$dir/competition/agents/juraj_v35_cpp/run.sh" \
      --start 55800 --seeds 8 --output "$out"
    cat "$out/summary.json"
  done

  python - <<'PY'
import json
from pathlib import Path
names = [
    "v35-champion-70fresh",
    "v35-defense-fresh",
    "v35-heuristic-rebuild",
    "v35-logistics-recenter",
    "juraj-v3.6-iter1-attack-pass",
    "juraj-v3.6-search-refactor",
]
rows=[]
for i,name in enumerate(names):
    s=json.load(open(f"/tmp/picker9-holdout-out-{i}/summary.json"))
    rows.append({"opponent":name, **s})
W=sum(r["W"] for r in rows); D=sum(r["D"] for r in rows); L=sum(r["L"] for r in rows)
games=sum(r["games"] for r in rows)
errors=sum(r["errors"] for r in rows); illegal=sum(r["illegal_actions"] for r in rows)
out={
    "candidate":"healthy_precontact_search_share_020_to_028_t50",
    "seeds_per_opponent":8,
    "opponents":rows,
    "aggregate":{"W":W,"D":D,"L":L,"games":games,"raw_win_rate":W/games if games else 0.0,"score":(W+0.5*D)/games if games else 0.0,"errors":errors,"illegal_actions":illegal},
}
Path("/tmp/picker9_hard_holdout.json").write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
print("=== PICKER9_HARD_HOLDOUT_AGGREGATE ===")
print(json.dumps(out["aggregate"],sort_keys=True))
PY
fi
'''
if "picker9-loop hard holdout hook" in b:
    raise SystemExit("hard holdout hook already present")
build.write_text(b + hook)
print("experiment=healthy_precontact_search_share_020_to_028_t50_hard_holdout")
