from __future__ import annotations
import random
from .schema import load_schema
from .genome import canonical_values

def mutate(values: dict, rng: random.Random, exploratory: bool=False, bias_chromosome: str|None=None) -> dict:
    data, _ = load_schema(); genes = data['genes']
    pool = genes
    if bias_chromosome and rng.random() < 0.70:
        q = [g for g in genes if g['chromosome'] == bias_chromosome]
        if q: pool = q
    count = rng.randint(4,8) if exploratory else rng.randint(1,3)
    out = dict(values)
    chosen = rng.sample(pool, min(count, len(pool)))
    for g in chosen:
        n=g['name']; t=g['type']; old=out[n]
        if t == 'bool': out[n] = not old
        elif t == 'enum':
            opts=[x for x in g['allowed'] if x != old]; out[n]=rng.choice(opts)
        elif t == 'int':
            step=int(g.get('mutation_step',1)); delta=rng.choice([-2,-1,1,2])*step
            out[n]=int(old)+delta
        elif t == 'float':
            sigma=float(g.get('mutation_sigma',0.05)); out[n]=float(old)+rng.gauss(0,sigma)
    return canonical_values(out)
