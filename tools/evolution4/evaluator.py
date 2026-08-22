from __future__ import annotations
import json, os, shutil, subprocess
from pathlib import Path
from .genome import env_for

ROOT=Path(__file__).resolve().parents[2]
AGENT=Path('competition/agents/juraj_v35_cpp')
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

def run(cmd,cwd=ROOT,check=True,capture=False,env=None):
    p=subprocess.run(cmd,cwd=cwd,text=True,capture_output=capture,env=env)
    if check and p.returncode:
        raise RuntimeError(f'command failed {p.returncode}: {cmd}\n{p.stdout if capture else ""}\n{p.stderr if capture else ""}')
    return p

def worktree(ref:str,dest:Path)->Path:
    run(['git','worktree','remove','--force',str(dest)],check=False)
    shutil.rmtree(dest,ignore_errors=True)
    run(['git','worktree','add','--detach',str(dest),ref])
    return dest

def build(tree:Path): run(['bash',str(tree/AGENT/'build.sh')])

def wrapper(run_sh:Path, values:dict, out:Path)->Path:
    out.parent.mkdir(parents=True,exist_ok=True)
    lines=['#!/usr/bin/env bash','set -euo pipefail']
    for k,v in env_for(values).items(): lines.append(f"export {k}={json.dumps(v)}")
    lines.append(f'exec {json.dumps(str(run_sh))}')
    out.write_text('\n'.join(lines)+'\n'); out.chmod(0o755); return out

def plain_wrapper(run_sh:Path,out:Path)->Path:
    out.parent.mkdir(parents=True,exist_ok=True); out.write_text('#!/usr/bin/env bash\nset -euo pipefail\nexec '+json.dumps(str(run_sh))+'\n'); out.chmod(0o755); return out

def resolve_opponents()->list[dict]:
    run(['git','fetch','--no-tags','origin']+[r for _,rs in OPPONENT_SPECS for r in rs],check=False)
    used=set(); ready=[]
    for i,(cat,refs) in enumerate(OPPONENT_SPECS):
        chosen=None
        for ref in refs:
            if ref in used: continue
            ok=run(['git','rev-parse','--verify',f'origin/{ref}'],check=False,capture=True)
            if ok.returncode: continue
            tree=worktree(f'origin/{ref}',Path(f'/tmp/e4-opp-{i}'))
            try: build(tree)
            except Exception: continue
            chosen={'archetype':cat,'ref':ref,'tree':str(tree),'run':str(tree/AGENT/'run.sh'),'sha':run(['git','rev-parse','HEAD'],cwd=tree,capture=True).stdout.strip()}; break
        if chosen: ready.append(chosen); used.add(chosen['ref'])
    core={'normal-expansion','defense-turtle','logistics-recenter','attack-pass','search-hunter','doomer-rusher','picker-muster','gatherer-economy'}
    have={x['archetype'] for x in ready}
    if not core.issubset(have) or len(ready)<8: raise RuntimeError(f'opponent suite insufficient: {len(ready)} {sorted(have)}')
    return ready

def paired(candidate:Path,baseline:Path,start:int,seeds:int,out:Path)->dict:
    shutil.rmtree(out,ignore_errors=True); out.mkdir(parents=True,exist_ok=True)
    cmd=['python','competition/agents/juraj_v35_cpp/paired_benchmark.py','--candidate',str(candidate),'--baseline',str(baseline),'--start',str(start),'--seeds',str(seeds),'--output',str(out)]
    p=run(cmd,check=False,capture=True)
    (out/'driver.stdout').write_text(p.stdout); (out/'driver.stderr').write_text(p.stderr)
    if p.returncode: raise RuntimeError(f'paired benchmark failed {p.returncode}: {p.stderr[-3000:]}')
    s=json.loads((out/'summary.json').read_text())
    if s.get('errors',0) or s.get('illegal_actions',0): raise RuntimeError(f'benchmark protocol failure {s}')
    return s

def combine(summaries:list[dict])->dict:
    W=sum(int(x.get('W',0)) for x in summaries); D=sum(int(x.get('D',0)) for x in summaries); L=sum(int(x.get('L',0)) for x in summaries); games=W+D+L
    return {'W':W,'D':D,'L':L,'games':games,'score':(W+.5*D)/games if games else 0.0,'raw_win_rate':W/games if games else 0.0,'errors':sum(int(x.get('errors',0)) for x in summaries),'illegal_actions':sum(int(x.get('illegal_actions',0)) for x in summaries)}

def color_imbalance(summary:dict)->float:
    # paired_benchmark schema differs across revisions; gracefully use known seat/color fields when present.
    vals=[]
    for k in ('candidate_as_p1_score','candidate_as_p2_score','seat1_score','seat2_score','color1_score','color2_score'):
        if k in summary:
            try: vals.append(float(summary[k]))
            except Exception: pass
    return abs(vals[0]-vals[1]) if len(vals)>=2 else 0.0
