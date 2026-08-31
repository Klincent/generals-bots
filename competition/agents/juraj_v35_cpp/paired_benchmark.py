#!/usr/bin/env python3
"""Audited deterministic paired-seat benchmark against a pinned agent tree."""
import argparse, json, os, re, statistics, subprocess, sys
from pathlib import Path
import numpy as np
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--baseline',type=Path,required=True);p.add_argument('--start',type=int,required=True);p.add_argument('--seeds',type=int,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
def executable(path):
 if path.is_dir(): path=path/'run.sh'
 if not path.is_file(): p.error(f'agent executable does not exist: {path}')
 return path.resolve()
a.candidate=executable(a.candidate);a.baseline=executable(a.baseline)
a.output.mkdir(parents=True,exist_ok=True); raw=a.output/'games.jsonl'; games=[]
for seed in range(a.start,a.start+a.seeds):
 rng_seed=(seed*0x9E3779B1+0x35)&0xffffffff
 for swap in (False,True):
  candidate_seat=1 if swap else 0; agents=[a.candidate,a.baseline] if not swap else [a.baseline,a.candidate]
  audit=a.output/f'audit-{seed}-{candidate_seat}.json'; env=os.environ.copy();env['JURAJ_RNG_SEED']=str(rng_seed);env['JURAJ_V35_TRACE']='1';env['PYTHONPATH']=str(Path.cwd())+os.pathsep+env.get('PYTHONPATH','')
  try:r=subprocess.run([sys.executable,'competition/matchup.py',*[str(x.resolve()) for x in agents],'--mode','competition','--seed',str(seed),'--audit-json',str(audit)],text=True,capture_output=True,timeout=180,env=env)
  except subprocess.TimeoutExpired as e:
   games.append({'seed':seed,'candidate_seat':candidate_seat,'rng_seed':rng_seed,'error':'timeout'});continue
  row={'seed':seed,'candidate_seat':candidate_seat,'rng_seed':rng_seed,'returncode':r.returncode,'stderr':r.stderr[-30000:]}
  if r.returncode or not audit.exists():row['error']='process_or_protocol'
  else:
   row.update(json.loads(audit.read_text()));w=row['winner'];row['result']='draw' if w<0 else ('win' if w==candidate_seat else 'loss');row['candidate_illegal']=row['illegal_actions'][candidate_seat];row['candidate_timing']=row['decision_ms'][candidate_seat]
  games.append(row)
with raw.open('w') as f:
 for row in games:f.write(json.dumps(row,sort_keys=True)+'\n')
valid=[g for g in games if 'result'in g]; W=sum(g['result']=='win' for g in valid);D=sum(g['result']=='draw' for g in valid);L=sum(g['result']=='loss' for g in valid);score=(W+.5*D)/max(1,len(valid))
seat={};
for s in (0,1):
 x=[g for g in valid if g['candidate_seat']==s];seat[str(s)]=(sum(g['result']=='win' for g in x)+.5*sum(g['result']=='draw' for g in x))/max(1,len(x))
paired=[]
for seed in range(a.start,a.start+a.seeds):
 x=[g for g in valid if g['seed']==seed];paired.append(sum((1 if g['result']=='win' else .5 if g['result']=='draw' else 0) for g in x)/2 if len(x)==2 else 0)
rng=np.random.default_rng(0x35);boots=[float(np.mean(rng.choice(paired,len(paired),replace=True))) for _ in range(10000)] if paired else [0]
timing=[g['candidate_timing'][k] for g in valid for k in ('p50','p95','p99','max') if k=='p50']
summary={'seed_start':a.start,'seed_end':a.start+a.seeds-1,'maps':a.seeds,'games':len(games),'W':W,'D':D,'L':L,'score':score,'seat_score':seat,'paired_score':statistics.mean(paired),'paired_ci95':[float(np.quantile(boots,.025)),float(np.quantile(boots,.975))],'errors':sum('error'in g for g in games),'illegal_actions':sum(g.get('candidate_illegal',0) for g in games),'turns_mean':statistics.mean([g['turns'] for g in valid]) if valid else 0,'decision_roundtrip_ms':{'p50':float(np.quantile(timing,.5)) if timing else 0,'p95':float(np.quantile(timing,.95)) if timing else 0,'p99':float(np.quantile(timing,.99)) if timing else 0,'max':max((g['candidate_timing']['max'] for g in valid),default=0)}}
(a.output/'summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
# Preserve compact chronological evidence for three wins and three losses.
selected=[]
for result in ('win','loss'):
 for g in [x for x in valid if x['result']==result][:3]:
  lines=[z for z in g['stderr'].splitlines() if z.startswith(('[v35_plan]','[v35_castles]','[v35_production]','[v35_front]','[v35_opponent]','[v35_logistics]','[v35_search]'))]
  selected.append({'seed':g['seed'],'seat':g['candidate_seat'],'result':result,'events':lines[:12]+lines[-8:]})
(a.output/'selected-traces.json').write_text(json.dumps(selected,indent=2)+'\n')
(a.output/'telemetry-summary.json').write_text(json.dumps({'note':'raw tagged telemetry is retained per game','selected_games':len(selected)},indent=2)+'\n')
print(json.dumps(summary,sort_keys=True));raise SystemExit(summary['errors']>0 or summary['illegal_actions']>0)
