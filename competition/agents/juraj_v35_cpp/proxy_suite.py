#!/usr/bin/env python3
"""Run paired seats against an equal-weight, deterministic competition proxy suite."""
import argparse, json, subprocess, sys
from pathlib import Path

INVENTORY = {
    "v34_exact": ("competition/agents/juraj_cpp/run.sh", "archived Juraj V3.4; strongest pinned historical baseline"),
    "juraj_current": ("competition/agents/juraj_cpp/run.sh", "archived configurable Juraj family; balanced/defensive"),
    "expander_cpp": ("competition/agents/expander_cpp/run.sh", "fast deterministic expansion/economy pressure"),
    "expander_rust": ("competition/agents/expander_rust/run.sh", "independent deterministic expansion implementation"),
    "expander_python": ("competition/agents/expander_python/run.sh", "simple expansion control and protocol diversity"),
}
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--start',type=int,required=True);p.add_argument('--seeds',type=int,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--opponents',nargs='*',default=list(INVENTORY));a=p.parse_args()
a.output.mkdir(parents=True,exist_ok=True); summaries={}
for name in a.opponents:
    if name not in INVENTORY: raise SystemExit(f'unknown proxy: {name}')
    run=Path(INVENTORY[name][0]); out=a.output/name
    cmd=[sys.executable,str(Path(__file__).with_name('paired_benchmark.py')),'--candidate',str(a.candidate),'--baseline',str(run),'--start',str(a.start),'--seeds',str(a.seeds),'--output',str(out)]
    subprocess.run(cmd,check=True); summaries[name]=json.loads((out/'summary.json').read_text())
scores=[v['score'] for v in summaries.values()]
report={'seed_start':a.start,'seed_end':a.start+a.seeds-1,'equal_weighted':True,'inventory':{k:{'run':v[0],'style':v[1]} for k,v in INVENTORY.items()},'opponents':summaries,'macro_score':sum(scores)/len(scores),'worst_score':min(scores),'best_score':max(scores),'limitations':['Repository proxies skew toward expansion; no submitted external competition bots are available.','v34_exact requires JURAJ_VERSION=V34 in the environment.']}
(a.output/'proxy-summary.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n');print(json.dumps(report,sort_keys=True))
