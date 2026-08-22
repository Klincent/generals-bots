from __future__ import annotations

def dominates(a: dict, b: dict) -> bool:
    # maximize aggregate/min/hof, minimize color imbalance
    av=(a.get('aggregate',0.0),a.get('minimum',0.0),a.get('hof',0.0),-a.get('color_imbalance',1.0))
    bv=(b.get('aggregate',0.0),b.get('minimum',0.0),b.get('hof',0.0),-b.get('color_imbalance',1.0))
    return all(x>=y for x,y in zip(av,bv)) and any(x>y for x,y in zip(av,bv))

def non_dominated_sort(items: list[dict]) -> list[list[dict]]:
    remaining=list(items); fronts=[]
    while remaining:
        front=[x for x in remaining if not any(dominates(y['fitness'],x['fitness']) for y in remaining if y is not x)]
        if not front: front=[remaining[0]]
        fronts.append(front); ids={id(x) for x in front}; remaining=[x for x in remaining if id(x) not in ids]
    return fronts

def crowding(front: list[dict]) -> dict[str,float]:
    if not front: return {}
    d={x['genome_id']:0.0 for x in front}
    objectives=[('aggregate',1),('minimum',1),('hof',1),('color_imbalance',-1)]
    for key,sign in objectives:
        ordered=sorted(front,key=lambda x:sign*x['fitness'].get(key,0.0))
        d[ordered[0]['genome_id']]=d[ordered[-1]['genome_id']]=float('inf')
        lo=ordered[0]['fitness'].get(key,0.0); hi=ordered[-1]['fitness'].get(key,0.0); span=max(1e-12,abs(hi-lo))
        for i in range(1,len(ordered)-1):
            prev=ordered[i-1]['fitness'].get(key,0.0); nxt=ordered[i+1]['fitness'].get(key,0.0)
            d[ordered[i]['genome_id']]+=abs(nxt-prev)/span
    return d

def select(items: list[dict], n: int) -> list[dict]:
    out=[]
    for front in non_dominated_sort(items):
        if len(out)+len(front)<=n: out.extend(front); continue
        cd=crowding(front); front=sorted(front,key=lambda x:cd[x['genome_id']],reverse=True)
        out.extend(front[:n-len(out)]); break
    return out
