from __future__ import annotations

CATASTROPHIC_X0_FLOOR=0.25


def _x0(f:dict)->float:
    v=f.get('x0_score')
    return 0.0 if v is None else float(v)


def dominates(a:dict,b:dict)->bool:
    # Maximize performance/robustness/X0 competence/novelty/HOF, minimize colour imbalance.
    av=(a.get('aggregate',0.0),a.get('minimum',0.0),_x0(a),a.get('novelty',0.0),a.get('hof',0.0),-a.get('color_imbalance',1.0))
    bv=(b.get('aggregate',0.0),b.get('minimum',0.0),_x0(b),b.get('novelty',0.0),b.get('hof',0.0),-b.get('color_imbalance',1.0))
    return all(x>=y for x,y in zip(av,bv)) and any(x>y for x,y in zip(av,bv))


def non_dominated_sort(items:list[dict])->list[list[dict]]:
    remaining=list(items); fronts=[]
    while remaining:
        front=[x for x in remaining if not any(dominates(y['fitness'],x['fitness']) for y in remaining if y is not x)]
        if not front: front=[remaining[0]]
        fronts.append(front); ids={id(x) for x in front}; remaining=[x for x in remaining if id(x) not in ids]
    return fronts


def crowding(front:list[dict])->dict[str,float]:
    if not front:return {}
    d={x['genome_id']:0.0 for x in front}
    objectives=[('aggregate',1),('minimum',1),('x0_score',1),('novelty',1),('hof',1),('color_imbalance',-1)]
    for key,sign in objectives:
        ordered=sorted(front,key=lambda x:sign*float(x['fitness'].get(key,0.0) or 0.0))
        d[ordered[0]['genome_id']]=d[ordered[-1]['genome_id']]=float('inf')
        lo=float(ordered[0]['fitness'].get(key,0.0) or 0.0); hi=float(ordered[-1]['fitness'].get(key,0.0) or 0.0); span=max(1e-12,abs(hi-lo))
        for i in range(1,len(ordered)-1):
            prev=float(ordered[i-1]['fitness'].get(key,0.0) or 0.0); nxt=float(ordered[i+1]['fitness'].get(key,0.0) or 0.0)
            d[ordered[i]['genome_id']]+=abs(nxt-prev)/span
    return d


def select(items:list[dict],n:int)->list[dict]:
    if not items:return []
    # In Stage 1, explicit X0 evidence is present. Novelty is not allowed to
    # rescue a genome that is catastrophically weak against the frozen ancestor
    # when enough non-catastrophic candidates are available.
    x0_safe=[x for x in items if x['fitness'].get('x0_score') is None or float(x['fitness'].get('x0_score',0.0))>=CATASTROPHIC_X0_FLOOR]
    base=x0_safe if len(x0_safe)>=n else list(items)
    # Novelty may preserve a somewhat weaker lineage, but never a grossly weak
    # aggregate organism purely because it is different.
    best=max(float(x['fitness'].get('aggregate',0.0)) for x in base)
    viable=[x for x in base if float(x['fitness'].get('aggregate',0.0))>=best-0.20]
    pool=viable if len(viable)>=n else base
    out=[]
    for front in non_dominated_sort(pool):
        if len(out)+len(front)<=n:
            out.extend(front); continue
        cd=crowding(front); front=sorted(front,key=lambda x:cd[x['genome_id']],reverse=True)
        out.extend(front[:n-len(out)]); break
    return out
