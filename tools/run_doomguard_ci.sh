#!/usr/bin/env bash
set -u

BASE_SHA=e50123cee7d924f0d643acd372a5300971f93917
PICKER9_SHA=734355a44adf76f274892bf13804d638c52869b0
BRANCH=chatgpt/e50123-doomguard
mkdir -p validation /tmp/doom

patch=not_run
tests=not_run
prep=not_run
preserve=not_run
pressure=not_run
control=not_run

commit_status() {
  {
    echo "patch=$patch"
    echo "tests=$tests"
    echo "prep=$prep"
    echo "preserve=$preserve"
    echo "pressure=$pressure"
    echo "control=$control"
  } > validation/doomguard-status.txt

  if [[ -f /tmp/doom/champion/summary.json && -f /tmp/doom/doom-vs-p9/summary.json && -f /tmp/doom/champ-vs-p9/summary.json ]]; then
    python - <<'PY' >> validation/doomguard-status.txt
import json,re
from pathlib import Path
b=Path('/tmp/doom')
p=json.loads((b/'champion/summary.json').read_text())
d=json.loads((b/'doom-vs-p9/summary.json').read_text())
c=json.loads((b/'champ-vs-p9/summary.json').read_text())
games=[json.loads(x) for x in (b/'champion/games.jsonl').read_text().splitlines() if x.strip()]
starts=moves=windows=active=0
for g in games:
    lines=[x for x in g.get('stderr','').splitlines() if '[DOOM] [v35_doomguard]' in x]
    if not lines:
        continue
    vals={k:int(v) for k,v in re.findall(r'(\w+)=(-?\d+)',lines[-1])}
    starts += vals.get('starts',0)
    moves += vals.get('moves',0)
    windows += vals.get('windows',0)
    active += int(vals.get('starts',0)>0)
delta=d['score']-c['score']
pres_ok=p['score']>=0.475 and p['errors']==0 and p['illegal_actions']==0
pressure_ok=delta>=0.0
print(f"preserve_WDL={p['W']}/{p['D']}/{p['L']}")
print(f"preserve_score={p['score']:.6f}")
print(f"preserve_ci95={p['paired_ci95']}")
print(f"doom_vs_p9_WDL={d['W']}/{d['D']}/{d['L']}")
print(f"doom_vs_p9_score={d['score']:.6f}")
print(f"champ_vs_p9_WDL={c['W']}/{c['D']}/{c['L']}")
print(f"champ_vs_p9_score={c['score']:.6f}")
print(f"pressure_delta={delta:.6f}")
print(f"doom_active_games={active}")
print(f"doom_starts={starts}")
print(f"doom_windows={windows}")
print(f"doom_moves={moves}")
print('PRESERVATION_GATE=' + ('PASS' if pres_ok else 'FAIL'))
print('PRESSURE_GATE=' + ('PASS' if pressure_ok else 'FAIL'))
print('COMBINE_RECOMMENDATION=' + ('YES' if pres_ok and pressure_ok else 'NO'))
PY
  fi

  [[ -f /tmp/doom/test-build.log ]] && tail -120 /tmp/doom/test-build.log > validation/doomguard-test-tail.txt || true
  git config user.name 'github-actions[bot]'
  git config user.email '41898282+github-actions[bot]@users.noreply.github.com'
  git add validation/doomguard-status.txt
  [[ -f validation/doomguard-test-tail.txt ]] && git add validation/doomguard-test-tail.txt || true
  [[ "$tests" == success ]] && git add competition/agents/juraj_v35_cpp/main.cpp || true
  if ! git diff --cached --quiet; then
    git commit -m 'Validate gated DoomGuard defensive muster'
    git push origin "HEAD:$BRANCH"
  fi
}

if grep -q '\[v35_doomguard\]' competition/agents/juraj_v35_cpp/main.cpp; then
  patch=success
else
  python tools/apply_e50123_doomguard.py >/tmp/doom/patch.log 2>&1
  rc=$?
  if [[ $rc -ne 0 ]]; then
    patch=failed
    cp /tmp/doom/patch.log validation/doomguard-test-tail.txt
    commit_status
    exit $rc
  fi
  patch=success
fi

( bash competition/agents/juraj_v35_cpp/test.sh && bash competition/agents/juraj_v35_cpp/build.sh ) > /tmp/doom/test-build.log 2>&1
rc=$?
if [[ $rc -ne 0 ]]; then
  tests=failed
  commit_status
  exit $rc
fi
tests=success

python -m pip install -e . >/tmp/doom/pip.log 2>&1
rc=$?
if [[ $rc -ne 0 ]]; then
  prep=failed
  commit_status
  exit $rc
fi

git worktree add --detach /tmp/champion "$BASE_SHA" >/tmp/doom/worktree.log 2>&1
rc=$?
if [[ $rc -eq 0 ]]; then git worktree add --detach /tmp/picker9 "$PICKER9_SHA" >>/tmp/doom/worktree.log 2>&1; rc=$?; fi
if [[ $rc -eq 0 ]]; then bash /tmp/champion/competition/agents/juraj_v35_cpp/build.sh >>/tmp/doom/worktree.log 2>&1; rc=$?; fi
if [[ $rc -eq 0 ]]; then bash /tmp/picker9/competition/agents/juraj_v35_cpp/build.sh >>/tmp/doom/worktree.log 2>&1; rc=$?; fi
if [[ $rc -ne 0 ]]; then
  prep=failed
  tail -120 /tmp/doom/worktree.log >> /tmp/doom/test-build.log
  commit_status
  exit $rc
fi
prep=success

cat >/tmp/doom.sh <<'EOF'
#!/usr/bin/env bash
export V35_DOOMGUARD_ENABLED=1
"$GITHUB_WORKSPACE/competition/agents/juraj_v35_cpp/run.sh" "$@" 2> >(sed -u 's/^/[DOOM] /' >&2)
EOF
cat >/tmp/champ.sh <<'EOF'
#!/usr/bin/env bash
/tmp/champion/competition/agents/juraj_v35_cpp/run.sh "$@" 2> >(sed -u 's/^/[CHAMP] /' >&2)
EOF
cat >/tmp/picker9.sh <<'EOF'
#!/usr/bin/env bash
export V35_PICKER_ENABLED=1
/tmp/picker9/competition/agents/juraj_v35_cpp/run.sh "$@" 2> >(sed -u 's/^/[P9] /' >&2)
EOF
chmod +x /tmp/doom.sh /tmp/champ.sh /tmp/picker9.sh

python competition/agents/juraj_v35_cpp/paired_benchmark.py --candidate /tmp/doom.sh --baseline /tmp/champ.sh --start 36000 --seeds 30 --output /tmp/doom/champion >/tmp/doom/preserve.log 2>&1
rc=$?
if [[ $rc -ne 0 ]]; then preserve=failed; commit_status; exit $rc; fi
preserve=success

python competition/agents/juraj_v35_cpp/paired_benchmark.py --candidate /tmp/doom.sh --baseline /tmp/picker9.sh --start 36100 --seeds 20 --output /tmp/doom/doom-vs-p9 >/tmp/doom/pressure.log 2>&1
rc=$?
if [[ $rc -ne 0 ]]; then pressure=failed; commit_status; exit $rc; fi
pressure=success

(
  cd /tmp/champion
  python competition/agents/juraj_v35_cpp/paired_benchmark.py --candidate /tmp/champ.sh --baseline /tmp/picker9.sh --start 36100 --seeds 20 --output /tmp/doom/champ-vs-p9
) >/tmp/doom/control.log 2>&1
rc=$?
if [[ $rc -ne 0 ]]; then control=failed; commit_status; exit $rc; fi
control=success

commit_status
exit 0
