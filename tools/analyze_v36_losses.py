#!/usr/bin/env python3
import json,re,sys
from pathlib import Path
p=Path(sys.argv[1]); games=[json.loads(x) for x in p.read_text().splitlines() if x.strip()]
valid=[g for g in games if 'result' in g]

def cand_lines(g):
    return [ln[len('[CAND] '):] for ln in g.get('stderr','').splitlines() if ln.startswith('[CAND] ')]

def last_tag(g,tag):
    xs=[ln for ln in cand_lines(g) if ln.startswith(tag)]
    return xs[-1] if xs else ''

def ints(line):
    return {k:int(v) for k,v in re.findall(r'(\w+)=(-?\d+)',line)}

def row(g):
    c=ints(last_tag(g,'[v35_castle_deadline]')); s=ints(last_tag(g,'[v36_search]')); pk=ints(last_tag(g,'[v36_picker]')); a=ints(last_tag(g,'[v35_actions]')); f=ints(last_tag(g,'[v35_front]')); cy=ints(last_tag(g,'[v35_cycles]'))
    snaps={int(t):int(v) for t,v in re.findall(r'(\d+):(\d+)',last_tag(g,'[v35_land]'))}
    cb=g.get('castles_built',[0,0])[g['candidate_seat']]
    m=re.search(r'miss_reason=([^ ]+)',last_tag(g,'[v35_castle_deadline]')); castle_miss=m.group(1) if m else 'none'
    reachable=s.get('reachable',0); touched=s.get('touched',0); swept=s.get('swept',0); starts=pk.get('starts',0); completes=pk.get('completions',0); contact=f.get('meaningful_contact',-1)
    flags=[]
    if g['turns']>=180 and cb<1: flags.append('C1_NOT_BUILT')
    if g['turns']>=300 and cb<2: flags.append('C2_NOT_BUILT')
    if reachable and g['turns']>=250 and touched<reachable and contact<0: flags.append('EXPLORE_UNTOUCHED_NO_CONTACT')
    if reachable and g['turns']>=350 and swept<max(1,reachable-1) and contact<0: flags.append('EXPLORE_UNSWEPT_NO_CONTACT')
    if starts>completes+pk.get('aborts',0): flags.append('PICKER_STUCK')
    if pk.get('active',0): flags.append('PICKER_ACTIVE_AT_END')
    if contact>=0 and g['turns']-contact>=120 and a.get('enemy',0)+a.get('war',0)==0: flags.append('NO_ATTACK_AFTER_CONTACT')
    if contact>=0 and g['turns']-contact>=200 and a.get('enemy',0)==0: flags.append('NO_DIRECT_ENEMY_ATTACK')
    return {'seed':g['seed'],'seat':g['candidate_seat'],'result':g['result'],'turns':g['turns'],'castles_built':cb,'c1_build':c.get('c1_build_turn',-1),'c2_build':c.get('c2_build_turn',-1),'castle_miss':castle_miss,'reachable':reachable,'touched':touched,'swept':swept,'probe_moves':s.get('probe_moves',0),'forced_moves':s.get('forced_moves',0),'picker_starts':starts,'picker_completions':completes,'picker_moves':pk.get('moves',0),'picker_delivered':pk.get('delivered',0),'picker_aborts':pk.get('aborts',0),'picker_active':pk.get('active',0),'picker_blocked':pk.get('blocked_ticks',0),'contact':contact,'fronts_max':f.get('max_active',0),'expansion':a.get('expansion',0),'neutral':a.get('neutral',0),'enemy_actions':a.get('enemy',0),'war_actions':a.get('war',0),'search_actions':a.get('search',0),'passes':a.get('pass',0),'land':snaps,'cycle_reject':cy.get('candidate_route_rejections',0),'flags':flags}
rows=[row(g) for g in valid]; losses=[x for x in rows if x['result']=='loss']; wins=[x for x in rows if x['result']=='win']
print('=== LOSS FORENSICS ===')
for x in losses: print(json.dumps(x,sort_keys=True))
print('=== AGGREGATE ===')
allflags=sorted({z for x in rows for z in x['flags']})
for label,xs in [('loss',losses),('win',wins)]:
    if not xs: continue
    def avg(k): return sum(float(x.get(k,0)) for x in xs)/len(xs)
    print(json.dumps({'group':label,'n':len(xs),'avg_turns':avg('turns'),'avg_castles':avg('castles_built'),'avg_touched':avg('touched'),'avg_swept':avg('swept'),'avg_probe_moves':avg('probe_moves'),'avg_picker_starts':avg('picker_starts'),'avg_picker_completions':avg('picker_completions'),'avg_picker_delivered':avg('picker_delivered'),'avg_enemy_actions':avg('enemy_actions'),'avg_war_actions':avg('war_actions'),'avg_search_actions':avg('search_actions'),'avg_expansion':avg('expansion'),'flag_counts':{f:sum(f in x['flags'] for x in xs) for f in allflags}},sort_keys=True))
print('=== RAW CANDIDATE FINAL TELEMETRY FOR LOSSES ===')
for g in valid:
    if g['result']!='loss': continue
    print(f"--- seed={g['seed']} seat={g['candidate_seat']} turns={g['turns']} ---")
    for tag in ('[v35_castle_deadline]','[v35_actions]','[v35_pass]','[v35_land]','[v35_front]','[v35_cycles]','[v35_logistics]','[v36_picker]','[v36_search]','[v35_timing]'):
        z=last_tag(g,tag)
        if z: print(z)
