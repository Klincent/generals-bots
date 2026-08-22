from __future__ import annotations
import re
from pathlib import Path

def _nums(line:str):
    out={}
    for k,v in re.findall(r'([A-Za-z0-9_]+)=(-?[0-9]+(?:\.[0-9]+)?)',line):
        out[k]=float(v)
    return out

def aggregate(path:Path) -> dict:
    sums={}; counts={}; tags={}
    if not path.exists(): return {'means':{},'tags':{}}
    for f in path.rglob('*'):
        if not f.is_file() or f.stat().st_size>5_000_000: continue
        try: text=f.read_text(errors='ignore')
        except Exception: continue
        for line in text.splitlines():
            if not line.startswith('[v'): continue
            tag=line.split(']',1)[0]+']'; tags[tag]=tags.get(tag,0)+1
            for k,v in _nums(line).items(): sums[k]=sums.get(k,0.0)+v; counts[k]=counts.get(k,0)+1
    return {'means':{k:sums[k]/counts[k] for k in sums},'tags':tags}

def suggested_chromosome(t:dict, archetype_scores:dict|None=None) -> str|None:
    scores=archetype_scores or {}
    if scores:
        worst=min(scores,key=scores.get)
        if 'doomer' in worst or 'defense' in worst: return 'defense'
        if 'picker' in worst or 'muster' in worst: return 'picker'
        if 'search' in worst: return 'search'
        if 'logistics' in worst: return 'logistics'
        if 'expan' in worst or 'economy' in worst: return 'expansion'
        if 'attack' in worst: return 'attack'
    m=t.get('means',{})
    if m.get('pass',0)>25: return 'logistics'
    if m.get('mass_rejects',0)>m.get('starts',0)*3: return 'picker'
    if m.get('muster_windows',0)>5 and m.get('attack_moves',0)<1: return 'muster'
    return None
