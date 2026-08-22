from __future__ import annotations
import json, os, shutil, subprocess, time, threading
from pathlib import Path
from .genome import env_for

ROOT=Path(__file__).resolve().parents[2]
AGENT=Path('competition/agents/juraj_v35_cpp')
EVAL_SHA='2260b6f19d51a14d7c68770677f22d04dfd88022'
PINNED_MATCHUP=ROOT/'competition'/'evolution4_matchup_pinned.py'
PINNED_PAIRED=ROOT/'competition'/'evolution4_paired_benchmark_pinned.py'
_PIN_LOCK=threading.Lock()
OPPONENT_SPECS=[
 ('normal-expansion',['juraj-v3.6-expansion-cycle-hardening']),
 ('aggressive-expansion',['juraj-v3.6-short-cycle-only','juraj-v3.6-cycle-per-packet']),
 ('defense-turtle',['v35-defense-fresh','v35-logistics-conservative']),
 ('logistics-recenter',['v35-logistics-recenter','v35-logistics-conservative']),
 ('attack-pass',['juraj-v3.6-iter1-attack-pass','juraj-v3.6-cycle-per-packet']),
 ('search-hunter',['juraj-v3.6-search-refactor','juraj-v3.6-loss-forensics']),
 ('doomer-rusher',['chatgpt/picker9-doomguard-rusher','chatgpt/picker9-doomguard']),
 ('picker-muster',['chatgpt/picker-v9-muster-castle','juraj-v3.6-edge-picker']),
 ('gatherer-economy',['juraj-v3.6-edge-picker-economics','v35-heuristic-rebuild','v35-iterative-1to6']),
 ('recent-reference',['chatgpt/picker9-opponent-suite-75','v35-heuristic-rebuild','v35-castle-recapture'])]

def run(cmd,cwd=ROOT,check=True,capture=False,env=None,timeout=None):
    try:
        p=subprocess.run(cmd,cwd=cwd,text=True,capture_output=capture,env=env,timeout=timeout)
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(f'command timeout after {timeout}s: {cmd}') from e
    if check and p.returncode:
        raise RuntimeError(f'command failed {p.returncode}: {cmd}\n{p.stdout if capture else ""}\n{p.stderr if capture else ""}')
    return p

def _git_show(spec:str)->str:
    p=run(['git','show',spec],capture=True,timeout=30)
    return p.stdout

def ensure_pinned_evaluator():
    # Four genome workers share these files: serialize materialization to avoid races.
    with _PIN_LOCK:
        matchup=_git_show(f'{EVAL_SHA}:competition/matchup.py')
        paired_src=_git_show(f'{EVAL_SHA}:competition/agents/juraj_v35_cpp/paired_benchmark.py')
        paired_src=paired_src.replace("'competition/matchup.py'", "'competition/evolution4_matchup_pinned.py'")
        if "competition/evolution4_matchup_pinned.py" not in paired_src:
            raise RuntimeError('failed to pin paired benchmark matchup path')
        PINNED_MATCHUP.parent.mkdir(parents=True,exist_ok=True)
        if not PINNED_MATCHUP.exists() or PINNED_MATCHUP.read_text()!=matchup:
            PINNED_MATCHUP.write_text(matchup)
        if not PINNED_PAIRED.exists() or PINNED_PAIRED.read_text()!=paired_src:
            PINNED_PAIRED.write_text(paired_src)

def worktree(ref:str,dest:Path)->Path:
    listed=run(['git','worktree','list','--porcelain'],capture=True,timeout=30).stdout
    marker=f'worktree {dest}\n'
    if marker in listed:
        run(['git','worktree','remove','--force',str(dest)],timeout=30)
    elif dest.exists():
        shutil.rmtree(dest,ignore_errors=True)
    run(['git','worktree','prune'],check=False,capture=True,timeout=30)
    print(f'[evolution4] prepare worktree {dest.name} <- {ref}',flush=True)
    run(['git','worktree','add','--detach',str(dest),ref],timeout=60)
    return dest

def build(tree:Path):
    print(f'[evolution4] build {tree}',flush=True)
    run(['bash',str(tree/AGENT/'build.sh')],timeout=120)

def wrapper(run_sh:Path, values:dict, out:Path)->Path:
    out.parent.mkdir(parents=True,exist_ok=True)
    lines=['#!/usr/bin/env bash','set -euo pipefail']
    for k,v in env_for(values).items(): lines.append(f"export {k}={json.dumps(v)}")
    lines.append(f'exec {json.dumps(str(run_sh))}')
    out.write_text('\n'.join(lines)+'\n'); out.chmod(0o755); return out

def plain_wrapper(run_sh:Path,out:Path)->Path:
    out.parent.mkdir(parents=True,exist_ok=True); out.write_text('#!/usr/bin/env bash\nset -euo pipefail\nexec '+json.dumps(str(run_sh))+'\n'); out.chmod(0o755); return out

def resolve_opponents()->list[dict]:
    run(['git','fetch','--no-tags','origin','+refs/heads/*:refs/remotes/origin/*'],timeout=120)
    used=set(); ready=[]
    for i,(cat,refs) in enumerate(OPPONENT_SPECS):
        chosen=None
        for ref in refs:
            if ref in used: continue
            ok=run(['git','rev-parse','--verify',f'origin/{ref}'],check=False,capture=True,timeout=15)
            if ok.returncode: continue
            tree=worktree(f'origin/{ref}',Path(f'/tmp/e4-opp-{i}'))
            try: build(tree)
            except Exception as e:
                print(f'[evolution4] opponent rejected {cat} {ref}: {e}',flush=True)
                continue
            chosen={'archetype':cat,'ref':ref,'tree':str(tree),'run':str(tree/AGENT/'run.sh'),'sha':run(['git','rev-parse','HEAD'],cwd=tree,capture=True,timeout=15).stdout.strip()}; break
        if chosen:
            print(f'[evolution4] opponent ready {i+1}/{len(OPPONENT_SPECS)} {cat} {chosen["ref"]}',flush=True)
            ready.append(chosen); used.add(chosen['ref'])
    core={'normal-expansion','defense-turtle','logistics-recenter','attack-pass','search-hunter','doomer-rusher','picker-muster','gatherer-economy'}
    have={x['archetype'] for x in ready}
    if not core.issubset(have) or len(ready)<8: raise RuntimeError(f'opponent suite insufficient: {len(ready)} {sorted(have)}')
    print(f'[evolution4] opponent suite ready: {len(ready)} archetypes',flush=True)
    return ready

def paired(candidate:Path,baseline:Path,start:int,seeds:int,out:Path)->dict:
    ensure_pinned_evaluator()
    cmd=['python',str(PINNED_PAIRED.relative_to(ROOT)),'--candidate',str(candidate),'--baseline',str(baseline),'--start',str(start),'--seeds',str(seeds),'--output',str(out)]
    tag=str(out.relative_to(ROOT)) if out.is_relative_to(ROOT) else str(out)
    timeout=max(420, int(seeds)*2*70+120)
    for attempt in (1,2):
        shutil.rmtree(out,ignore_errors=True); out.mkdir(parents=True,exist_ok=True)
        print(f'[evolution4] BENCH START {tag} attempt={attempt} seeds={seeds} games={seeds*2} seed_start={start} timeout={timeout}s',flush=True)
        t0=time.monotonic()
        try:
            p=run(cmd,check=False,capture=True,timeout=timeout)
        except Exception as e:
            print(f'[evolution4] BENCH TIMEOUT/ERROR {tag} attempt={attempt} elapsed={time.monotonic()-t0:.1f}s: {e}',flush=True)
            if attempt==1:
                print(f'[evolution4] BENCH RETRY {tag} reason=driver_exception',flush=True); continue
            raise
        (out/'driver.stdout').write_text(p.stdout); (out/'driver.stderr').write_text(p.stderr)
        s=None
        if (out/'summary.json').exists():
            try: s=json.loads((out/'summary.json').read_text())
            except Exception: s=None
        illegal=int((s or {}).get('illegal_actions',0))
        errors=int((s or {}).get('errors',0))
        if p.returncode==0 and s is not None and not errors and not illegal:
            print(f'[evolution4] BENCH DONE {tag} elapsed={time.monotonic()-t0:.1f}s W/D/L={s.get("W")}/{s.get("D")}/{s.get("L")} score={s.get("score",s.get("paired_score"))}',flush=True)
            return s
        games_tail=''
        gp=out/'games.jsonl'
        if gp.exists(): games_tail=gp.read_text(errors='ignore')[-4000:]
        diagnostic=f'rc={p.returncode} errors={errors} illegal={illegal} stdout={p.stdout[-1500:]} stderr={p.stderr[-1500:]} games={games_tail}'
        print(f'[evolution4] BENCH FAILED {tag} attempt={attempt} {diagnostic}',flush=True)
        if illegal:
            raise RuntimeError(f'benchmark illegal action: {diagnostic}')
        if attempt==1:
            evidence=out.with_name(out.name+'.attempt1')
            shutil.rmtree(evidence,ignore_errors=True)
            out.rename(evidence)
            print(f'[evolution4] BENCH RETRY {tag} reason=infra_or_protocol_error',flush=True)
            continue
        raise RuntimeError(f'paired benchmark failed after retry: {diagnostic}')
    raise RuntimeError('unreachable paired benchmark retry state')

def combine(summaries:list[dict])->dict:
    W=sum(int(x.get('W',0)) for x in summaries); D=sum(int(x.get('D',0)) for x in summaries); L=sum(int(x.get('L',0)) for x in summaries); games=W+D+L
    return {'W':W,'D':D,'L':L,'games':games,'score':(W+.5*D)/games if games else 0.0,'raw_win_rate':W/games if games else 0.0,'errors':sum(int(x.get('errors',0)) for x in summaries),'illegal_actions':sum(int(x.get('illegal_actions',0)) for x in summaries)}

def color_imbalance(summary:dict)->float:
    vals=[]
    seat=summary.get('seat_score')
    if isinstance(seat,dict) and '0' in seat and '1' in seat:
        try: return abs(float(seat['0'])-float(seat['1']))
        except Exception: pass
    for k in ('candidate_as_p1_score','candidate_as_p2_score','seat1_score','seat2_score','color1_score','color2_score'):
        if k in summary:
            try: vals.append(float(summary[k]))
            except Exception: pass
    return abs(vals[0]-vals[1]) if len(vals)>=2 else 0.0
