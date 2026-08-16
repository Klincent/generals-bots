#!/usr/bin/env python3
"""Audited deterministic paired-seat benchmark against a pinned agent tree."""
import argparse, json, os, re, statistics, subprocess, sys
from pathlib import Path
import numpy as np

p=argparse.ArgumentParser()
p.add_argument('--candidate',type=Path,required=True); p.add_argument('--baseline',type=Path,required=True)
p.add_argument('--start',type=int,required=True); p.add_argument('--seeds',type=int,required=True)
p.add_argument('--output',type=Path,required=True); p.add_argument('--diagnostics',action='store_true')
a=p.parse_args(); a.output.mkdir(parents=True,exist_ok=True)
raw=a.output/'games.jsonl'; traces=a.output/'traces'; games=[]
if a.diagnostics: traces.mkdir(exist_ok=True)

def git_sha(path):
 try:
  return subprocess.check_output(['git','rev-parse','HEAD'],cwd=path.resolve().parent,text=True).strip()
 except subprocess.CalledProcessError:
  return 'unknown'

metadata={'candidate_path':str(a.candidate.resolve()),'baseline_path':str(a.baseline.resolve()),
          'candidate_sha':os.environ.get('CANDIDATE_SHA','unknown'),
          'baseline_sha':os.environ.get('BASELINE_SHA','unknown'),
          'seed_start':a.start,'seed_end':a.start+a.seeds-1,'maps':a.seeds,'paired_seats':True}
(a.output/'metadata.json').write_text(json.dumps(metadata,indent=2,sort_keys=True)+'\n')
for seed in range(a.start,a.start+a.seeds):
 rng_seed=(seed*0x9E3779B1+0x35)&0xffffffff
 for swap in (False,True):
  candidate_seat=1 if swap else 0; agents=[a.candidate,a.baseline] if not swap else [a.baseline,a.candidate]
  audit=a.output/f'audit-{seed}-{candidate_seat}.json'; env=os.environ.copy(); env['JURAJ_RNG_SEED']=str(rng_seed); env['JURAJ_V35_TRACE']='1'
  cmd=[sys.executable,'competition/matchup.py',*[str(x.resolve()) for x in agents],'--mode','competition','--seed',str(seed),'--audit-json',str(audit)]
  if a.diagnostics: cmd += ['--diagnostic-json',str(traces/f'trace-{seed}-{candidate_seat}.json')]
  try: r=subprocess.run(cmd,text=True,capture_output=True,timeout=180,env=env)
  except subprocess.TimeoutExpired:
   games.append({'seed':seed,'candidate_seat':candidate_seat,'rng_seed':rng_seed,'error':'timeout'}); continue
  row={'seed':seed,'candidate_seat':candidate_seat,'rng_seed':rng_seed,'returncode':r.returncode,'stderr':r.stderr[-100000:]}
  if r.returncode or not audit.exists(): row['error']='process_or_protocol'
  else:
   row.update(json.loads(audit.read_text())); w=row['winner']; row['result']='draw' if w<0 else ('win' if w==candidate_seat else 'loss')
   row['candidate_illegal']=row['illegal_actions'][candidate_seat]; row['candidate_timing']=row['decision_ms'][candidate_seat]
   row['candidate_castles_built']=row['castles_built'][candidate_seat]
  games.append(row)
with raw.open('w') as f:
 for row in games: f.write(json.dumps(row,sort_keys=True)+'\n')
valid=[g for g in games if 'result'in g]; W=sum(g['result']=='win' for g in valid); D=sum(g['result']=='draw' for g in valid); L=sum(g['result']=='loss' for g in valid)
score=(W+.5*D)/max(1,len(valid)); seat={}
for s in (0,1):
 x=[g for g in valid if g['candidate_seat']==s]; seat[str(s)]=(sum(g['result']=='win' for g in x)+.5*sum(g['result']=='draw' for g in x))/max(1,len(x))
paired=[]
for seed in range(a.start,a.start+a.seeds):
 x=[g for g in valid if g['seed']==seed]; paired.append(sum((1 if g['result']=='win' else .5 if g['result']=='draw' else 0) for g in x)/2 if len(x)==2 else 0)
rng=np.random.default_rng(0x35); boots=[float(np.mean(rng.choice(paired,len(paired),replace=True))) for _ in range(10000)] if paired else [0]

def tagged(stderr,tag):
 m=re.search(r'^\['+re.escape(tag)+r'\](.*)$',stderr,re.M)
 return {k:int(v) for k,v in re.findall(r'(\w+)=(-?\d+)',m.group(1) if m else '')}

def lands(stderr):
 m=re.search(r'^\[v35_land\](.*)$',stderr,re.M)
 return {int(k):int(v) for k,v in re.findall(r'(\d+):(\d+)',m.group(1) if m else '')}
telemetry={}
for tag in ('v35_actions','v35_threat','v35_escape','v35_castle_live'):
 rows=[tagged(g['stderr'],tag) for g in valid]
 for key in set().union(*(x.keys() for x in rows)): telemetry[key]=sum(x.get(key,0) for x in rows)
telemetry['castles_completed']=sum(g.get('candidate_castles_built',0) for g in valid)
telemetry['turns_total']=sum(g['turns'] for g in valid); telemetry['pass_rate']=telemetry.get('pass',0)/max(1,telemetry['turns_total'])
land_summary={}
for turn in (50,100,150,200):
 vals=[lands(g['stderr']).get(turn) for g in valid]; vals=[x for x in vals if x is not None]
 land_summary[str(turn)]={'mean':statistics.mean(vals) if vals else None,'games':len(vals)}
timing={k:(float(np.quantile([g['candidate_timing'][k] for g in valid],.5)) if valid else 0) for k in ('p50','p95','p99','max')}
summary={'seed_start':a.start,'seed_end':a.start+a.seeds-1,'maps':a.seeds,'games':len(games),'W':W,'D':D,'L':L,'score':score,'seat_score':seat,'paired_score':statistics.mean(paired) if paired else 0,'paired_ci95':[float(np.quantile(boots,.025)),float(np.quantile(boots,.975))],'errors':sum('error'in g for g in games),'illegal_actions':sum(g.get('candidate_illegal',0) for g in games),'turns_mean':statistics.mean([g['turns'] for g in valid]) if valid else 0,'decision_roundtrip_ms':timing,'telemetry':telemetry,'land':land_summary}
(a.output/'summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
print(json.dumps(summary,sort_keys=True)); raise SystemExit(summary['errors']>0 or summary['illegal_actions']>0)
