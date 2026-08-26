from __future__ import annotations
from .graph import graph_distance

CAPACITY=8
PROTECTED_LABELS={'X0','Y0'}


def _coverage_gain(candidate:dict,league:list[dict])->float:
    arch=candidate.get('fresh',{}).get('archetypes',{})
    if not arch: return 0.0
    gains=[]
    for name,score in arch.items():
        old=max((float(x.get('archetypes',{}).get(name,0.0)) for x in league),default=0.0)
        gains.append(max(0.0,float(score)-old))
    return max(gains,default=0.0)


def _novelty(candidate_gid:str,league:list[dict],load_genome)->float:
    if not league: return 1.0
    cg=load_genome(candidate_gid)['graph']
    vals=[]
    for x in league:
        try: vals.append(graph_distance(cg,load_genome(x['genome_id'])['graph']))
        except Exception: pass
    return min(vals) if vals else 1.0


def consider(state:dict,candidates:list[dict],load_genome,generation:int)->list[dict]:
    league=state.setdefault('league',[]); changes=[]
    for row in sorted(candidates,key=lambda r:(float(r['fresh']['fitness'].get('aggregate',0)),float(r['fresh']['fitness'].get('minimum',0))),reverse=True):
        gid=row['genome_id']
        if any(x.get('genome_id')==gid for x in league): continue
        fresh=row['fresh']; fit=fresh['fitness']; agg=fresh['aggregate']; score=float(fit.get('aggregate',0)); win=float(agg.get('raw_win_rate',0)); minimum=float(fit.get('minimum',0))
        if int(agg.get('errors',0)) or int(agg.get('illegal_actions',0)) or minimum<.25 or score<.48: continue
        gain=_coverage_gain(row,league); novelty=_novelty(gid,league,load_genome)
        h2h=row.get('head_to_head',{}); h2h_scores=[float(v.get('score',0.0)) for v in h2h.values()]
        counter=max(h2h_scores,default=.5)
        entry={'genome_id':gid,'generation':generation,'fresh_score':score,'fresh_win_rate':win,'minimum':minimum,'archetypes':dict(fresh.get('archetypes',{})),'coverage_gain':gain,'novelty':novelty,'counter_score':counter,'protected':False}
        if len(league)<CAPACITY:
            if score>=.52 or gain>=.05 or (novelty>=.20 and counter>=.60):
                league.append(entry); changes.append({'action':'admit','genome_id':gid,'reason':'open_slot'})
            continue
        replaceable=[x for x in league if not x.get('protected')]
        if not replaceable: continue
        victim=min(replaceable,key=lambda x:(float(x.get('fresh_score',0)),float(x.get('minimum',0)),float(x.get('coverage_gain',0))))
        better=score>=float(victim.get('fresh_score',0))+.015
        complementary=gain>=.08 and novelty>=.15
        countering=counter>=.65 and novelty>=.18
        if better or complementary or countering:
            league.remove(victim); league.append(entry); changes.append({'action':'replace','genome_id':gid,'victim':victim['genome_id'],'reason':'better' if better else 'coverage'})
    league.sort(key=lambda x:(bool(x.get('protected')),float(x.get('fresh_score',0)),float(x.get('minimum',0))),reverse=True)
    state['league']=league[:CAPACITY]
    return changes
