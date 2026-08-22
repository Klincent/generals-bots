from __future__ import annotations
from .schema import load_schema

def genome_distance(a: dict, b: dict) -> float:
    data,_=load_schema(); total=0.0
    for g in data['genes']:
        n=g['name']; t=g['type']
        if t=='bool' or t=='enum': total += 1.0 if a[n]!=b[n] else 0.0
        else:
            span=max(1e-12,float(g['maximum'])-float(g['minimum']))
            total += abs(float(a[n])-float(b[n]))/span
    return total/max(1,len(data['genes']))
