#!/usr/bin/env python3
import json,re,sys
from pathlib import Path

games=[json.loads(x) for x in Path(sys.argv[1]).read_text().splitlines() if x.strip()]

def cand_lines(g):
    return [x[7:] for x in g.get('stderr','').splitlines() if x.startswith('[CAND] ')]

def last(g,prefix):
    xs=[x for x in cand_lines(g) if x.startswith(prefix)]
    return xs[-1] if xs else ''

def ints(s):
    return {k:int(v) for k,v in re.findall(r'(\w+)=(-?\d+)',s)}

rows=[]
for g in games:
    a=ints(last(g,'[v35_actions]'))
    p=ints(last(g,'[v35_pass]'))
    s=ints(last(g,'[v36_search]'))
    f=ints(last(g,'[v35_front]'))
    rows.append({
        'result':g['result'],
        'seed':g['seed'],
        'seat':g['candidate_seat'],
        'turns':g['turns'],
        'pass':a.get('pass',0),
        'pass_other':p.get('pass_other',0),
        'search':a.get('search',0),
        'enemy':a.get('enemy',0),
        'war':a.get('war',0),
        'touched':s.get('touched',0),
        'swept':s.get('swept',0),
        'contact':f.get('meaningful_contact',-1),
    })

for result in ('win','draw','loss'):
    xs=[r for r in rows if r['result']==result]
    if not xs: continue
    avg=lambda k: sum(r[k] for r in xs)/len(xs)
    print(json.dumps({
        'result':result,'n':len(xs),
        'avg_pass':avg('pass'),'avg_pass_other':avg('pass_other'),
        'avg_search':avg('search'),'avg_enemy':avg('enemy'),'avg_war':avg('war'),
        'avg_touched':avg('touched'),'avg_swept':avg('swept'),
    },sort_keys=True))

worst=sorted(rows,key=lambda r:(-r['pass_other'],-r['pass'],r['seed']))[:8]
print('WORST_PASS')
for r in worst: print(json.dumps(r,sort_keys=True))
