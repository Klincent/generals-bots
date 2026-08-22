from __future__ import annotations
from .schema import load_schema


def genome_distance(a:dict,b:dict)->float:
    data,_=load_schema(); total=0.0
    for g in data['genes']:
        n=g['name']; t=g['type']
        if t in ('bool','enum'): total+=1.0 if a[n]!=b[n] else 0.0
        else:
            span=max(1e-12,float(g['maximum'])-float(g['minimum']))
            total+=abs(float(a[n])-float(b[n]))/span
    return total/max(1,len(data['genes']))


def structural_distance(a:dict,b:dict)->float:
    data,_=load_schema(); genes=[g for g in data['genes'] if g['type']=='enum']
    if not genes: return 0.0
    return sum(1.0 for g in genes if a[g['name']]!=b[g['name']])/len(genes)


def cohort_novelty(values:list[dict])->list[float]:
    if len(values)<=1: return [0.0 for _ in values]
    out=[]
    for i,a in enumerate(values):
        ds=sorted(structural_distance(a,b) for j,b in enumerate(values) if i!=j)
        # Local novelty: mean distance to the three closest structural neighbours.
        k=min(3,len(ds)); out.append(sum(ds[:k])/k if k else 0.0)
    return out
