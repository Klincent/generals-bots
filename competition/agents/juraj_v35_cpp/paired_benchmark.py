#!/usr/bin/env python3
"""Deterministic paired-seat smoke benchmark; never uses held-out seeds."""
import argparse, re, subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--baseline',type=Path,required=True);p.add_argument('--seeds',type=int,default=20);p.add_argument('--start',type=int,default=12000);a=p.parse_args()
wdl=[0,0,0];seat=[0,0];errors=0
for seed in range(a.start,a.start+a.seeds):
 for swap in (False,True):
  agents=[a.candidate,a.baseline] if not swap else [a.baseline,a.candidate]
  r=subprocess.run(['python','competition/matchup.py',*[str(x) for x in agents],'--mode','competition','--seed',str(seed)],text=True,capture_output=True,timeout=180)
  m=re.search(r'player (\d) captured',r.stdout)
  if r.returncode or (not m and 'draw' not in r.stdout):errors+=1;print(r.stderr);continue
  if not m:wdl[1]+=1
  elif int(m.group(1))==(1 if swap else 0):wdl[0]+=1;seat[1 if swap else 0]+=1
  else:wdl[2]+=1
print(f'V35_BENCHMARK W={wdl[0]} D={wdl[1]} L={wdl[2]} seat0_wins={seat[0]} seat1_wins={seat[1]} paired_score={(wdl[0]+.5*wdl[1])/max(1,sum(wdl)):.4f} errors={errors}')
raise SystemExit(errors>0)
