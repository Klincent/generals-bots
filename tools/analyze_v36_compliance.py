#!/usr/bin/env python3
# Analyzer for the committed compliance-fix benchmark; runtime patching is no longer needed.
import json,re,sys
from pathlib import Path
games=[json.loads(x) for x in Path(sys.argv[1]).read_text().splitlines() if x.strip() and 'result' in json.loads(x)]
def lines(g): return [x[7:] for x in g.get('stderr','').splitlines() if x.startswith('[CAND] ')]
def last(g,t):
 xs=[x for x in lines(g) if x.startswith(t)]; return xs[-1] if xs else ''
def ints(s): return {k:int(v) for k,v in re.findall(r'(\w+)=(-?\d+)',s)}
rows=[]
for g in games:
 c=ints(last(g,'[v35_castle_deadline]')); a=ints(last(g,'[v35_actions]')); s=ints(last(g,'[v36_search]')); p=ints(last(g,'[v36_picker]')); f=ints(last(g,'[v35_front]')); ps=ints(last(g,'[v35_pass]'))
 cb=g['castles_built'][g['candidate_seat']]
 rows.append({'seed':g['seed'],'seat':g['candidate_seat'],'result':g['result'],'turns':g['turns'],'castles':cb,'c1':c.get('c1_build_turn',-1),'c2':c.get('c2_build_turn',-1),'touched':s.get('touched',0),'swept':s.get('swept',0),'search':a.get('search',0),'picker_starts':p.get('starts',0),'picker_done':p.get('completions',0),'picker_delivered':p.get('delivered',0),'enemy':a.get('enemy',0),'war':a.get('war',0),'pass':a.get('pass',0),'pass_other':ps.get('pass_other',0),'contact':f.get('meaningful_contact',-1)})
for r in rows:
 if r['result']=='loss': print('LOSS',json.dumps(r,sort_keys=True))
print('=== COMPLIANCE GROUPS ===')
for result in ('win','draw','loss'):
 xs=[r for r in rows if r['result']==result]
 if not xs: continue
 def avg(k): return sum(r[k] for r in xs)/len(xs)
 print(json.dumps({'result':result,'n':len(xs),'avg_castles':avg('castles'),'c1_missing':sum(r['turns']>=180 and r['c1']<0 for r in xs),'c2_missing':sum(r['turns']>=300 and r['c2']<0 for r in xs),'avg_touched':avg('touched'),'avg_swept':avg('swept'),'avg_search':avg('search'),'avg_picker_starts':avg('picker_starts'),'avg_picker_delivered':avg('picker_delivered'),'avg_enemy':avg('enemy'),'avg_war':avg('war'),'avg_pass':avg('pass'),'avg_pass_other':avg('pass_other')},sort_keys=True))
