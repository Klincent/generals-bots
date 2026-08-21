#!/usr/bin/env python3
# trigger: 5x(10 evolution + regression)
from __future__ import annotations
import argparse, json, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path

REPO = Path.cwd()
AGENT = Path('competition/agents/juraj_v35_cpp')
PARENT = '9cc3b78a0003dd17079cd2aa8d6439321fedccc0'
START_REF = 'submission/picker9-search-t50-20260821'
OPPONENTS = [
    'v35-champion-70fresh', 'v35-defense-fresh', 'v35-heuristic-rebuild',
    'v35-logistics-recenter', 'juraj-v3.6-iter1-attack-pass',
    'juraj-v3.6-search-refactor',
]

def run(cmd, cwd=None, check=True, capture=False):
    kw={'cwd':cwd or REPO,'text':True,'check':check}
    if capture: kw.update(stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    p=subprocess.run(cmd, **kw)
    return p.stdout if capture else p.returncode

def patch_one(s, old, new):
    if s.count(old)!=1: raise RuntimeError(f'anchor count {s.count(old)} for {old!r}')
    return s.replace(old,new,1)

def mutate(src: str, iteration: int, phase: str) -> tuple[str,str]:
    if phase=='defense':
        choices=[
          ('doom_floor_15_to_13','std::max(1,o.opp_army)*15/100','std::max(1,o.opp_army)*13/100'),
          ('doom_eta_12_to_14','doom_eta_now<=12','doom_eta_now<=14'),
          ('doom_peak_45_to_50','own_peak*100<std::max(1,o.my_army)*45','own_peak*100<std::max(1,o.my_army)*50'),
          ('general_reserve_12_to_10','o.opp_army/12','o.opp_army/10'),
          ('doom_floor_18_to_16','std::max(18,','std::max(16,'),
        ]
    else:
        choices=[
          ('search_t50_028_to_030','o.turn<=50)?.28','o.turn<=50)?.30'),
          ('search_t50_028_to_032','o.turn<=50)?.28','o.turn<=50)?.32'),
          ('muster_threshold_8_to_7','int muster_threshold_=8;','int muster_threshold_=7;'),
          ('picker_threshold_16_to_14','int edge_picker_threshold_=16','int edge_picker_threshold_=14'),
          ('late_muster_300_to_280','o.turn>=300&&production_','o.turn>=280&&production_'),
        ]
    name,old,new=choices[(iteration-1)%len(choices)]
    if old not in src:
        return src, name+'-inert'
    return patch_one(src,old,new),name

def build_source(src: str, label: str) -> Path:
    d=Path(tempfile.mkdtemp(prefix=f'p9-{label}-'))
    run(['git','worktree','add','--detach',str(d),START_REF])
    p=d/AGENT/'main.cpp'; p.write_text(src)
    run(['bash',str(d/AGENT/'build.sh')],cwd=d)
    wrapper=d/f'{label}.sh'
    wrapper.write_text(f'#!/usr/bin/env bash\nexport V35_PICKER_ENABLED=1 V35_DOOMGUARD_ENABLED=1\nexec "{d/AGENT/"run.sh"}" "$@"\n')
    wrapper.chmod(0o755)
    return wrapper

def bench(candidate:Path, baseline:Path, seed:int, seeds:int, out:Path):
    if out.exists(): shutil.rmtree(out)
    run(['python',str(AGENT/'paired_benchmark.py'),'--candidate',str(candidate),'--baseline',str(baseline),'--start',str(seed),'--seeds',str(seeds),'--output',str(out)])
    return json.load(open(out/'summary.json'))

def losses(out:Path):
    rows=[json.loads(x) for x in open(out/'games.jsonl')]
    bad=[]
    for r in rows:
        val=str(r.get('result',r.get('winner',''))).lower()
        if val in ('loss','l','baseline','1') or r.get('candidate_score')==0:
            bad.append({'seed':r.get('seed'),'seat':r.get('candidate_seat'),'turns':r.get('turns')})
    return bad[:20]

def better(a,b):
    if a.get('errors',0) or a.get('illegal_actions',0): return False
    if b.get('errors',0) or b.get('illegal_actions',0): return True
    return (a.get('score',0),a.get('W',0),-a.get('L',0)) > (b.get('score',0),b.get('W',0),-b.get('L',0))

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--outer',type=int,required=True); args=ap.parse_args()
    outer=args.outer
    state_path=Path('tools/picker9_evolution_state.json')
    if state_path.exists(): state=json.load(open(state_path))
    else: state={'outer_done':0,'history':[],'best_source':None,'best_score':0.0}
    start_src=run(['git','show',f'{START_REF}:{AGENT}/main.cpp'],capture=True)
    src=state.get('best_source') or start_src
    base=build_source(src,f'outer{outer}-base')
    for i in range(1,11):
        seed=60000+outer*1000+i*20
        control_src=src
        control=build_source(control_src,f'o{outer}i{i}-control')
        out=Path(f'/tmp/p9-o{outer}-i{i}-control')
        control_summary=bench(control,base,seed,4,out)
        loss_rows=losses(out)
        dsrc,dname=mutate(control_src,i,'defense')
        defense=build_source(dsrc,f'o{outer}i{i}-def')
        dout=Path(f'/tmp/p9-o{outer}-i{i}-def')
        dsum=bench(defense,control,seed+4,4,dout)
        chosen_src=dsrc if better(dsum,{'score':.5,'W':0,'L':0,'errors':0,'illegal_actions':0}) else control_src
        chosen=defense if chosen_src==dsrc else control
        asrc,aname=mutate(chosen_src,i,'attack')
        attack=build_source(asrc,f'o{outer}i{i}-atk')
        aout=Path(f'/tmp/p9-o{outer}-i{i}-atk')
        asum=bench(attack,chosen,seed+8,4,aout)
        if better(asum,{'score':.5,'W':0,'L':0,'errors':0,'illegal_actions':0}):
            src=asrc; final=asum; decision='attack'
        else:
            src=chosen_src; final=dsum if chosen_src==dsrc else control_summary; decision='defense' if chosen_src==dsrc else 'control'
        base=build_source(src,f'o{outer}i{i}-best')
        state['history'].append({'outer':outer,'inner':i,'losses':loss_rows,'defense_mutation':dname,'defense':dsum,'attack_mutation':aname,'attack':asum,'decision':decision,'final':final})
    regression=[]; total={'W':0,'D':0,'L':0,'games':0,'errors':0,'illegal_actions':0}
    cand=build_source(src,f'outer{outer}-reg')
    for j,ref in enumerate(OPPONENTS):
        od=Path(tempfile.mkdtemp(prefix=f'p9-opp-{j}-'))
        run(['git','worktree','add','--detach',str(od),ref])
        run(['bash',str(od/AGENT/'build.sh')],cwd=od)
        opp=od/'opp.sh'; opp.write_text(f'#!/usr/bin/env bash\nexec "{od/AGENT/"run.sh"}" "$@"\n'); opp.chmod(0o755)
        sm=bench(cand,opp,65000+outer*100+j*10,4,Path(f'/tmp/p9-reg-{outer}-{j}'))
        regression.append({'opponent':ref,**sm})
        for k in total: total[k]+=sm.get(k,0)
    total['raw_win_rate']=total['W']/total['games'] if total['games'] else 0
    total['score']=(total['W']+.5*total['D'])/total['games'] if total['games'] else 0
    state['outer_done']=outer; state['best_source']=src; state['best_score']=total['score']; state['last_regression']={'opponents':regression,'aggregate':total}
    state_path.write_text(json.dumps(state,indent=2,sort_keys=True)+'\n')
    Path('/tmp/picker9_evolution_result.json').write_text(json.dumps(state['last_regression'],indent=2,sort_keys=True)+'\n')
    print(json.dumps({'outer':outer,'aggregate':total},sort_keys=True))

if __name__=='__main__': main()
