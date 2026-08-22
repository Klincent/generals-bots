from __future__ import annotations
import random
from .schema import load_schema
from .genome import canonical_values

# picker_neutrals_max is currently retained in the schema for observability/backward
# compatibility only. X0 computes this value for telemetry but does not use it in
# the actual picker allow decision, so mutating it would create a fake gene.
NON_EVOLVABLE={'picker_neutrals_max'}

def mutate(values: dict, rng: random.Random, exploratory: bool=False, bias_chromosome: str|None=None) -> dict:
    data, _ = load_schema(); genes = [g for g in data['genes'] if g['name'] not in NON_EVOLVABLE]
    pool = genes
    if bias_chromosome and rng.random() < 0.70:
        q = [g for g in genes if g['chromosome'] == bias_chromosome]
        if q: pool = q
    count = rng.randint(4,8) if exploratory else rng.randint(1,3)
    chosen=[]
    # Turbo Evolution: structural genes are first-class mutations, not rare accidents.
    # Exploratory offspring almost always change at least one algorithm; ordinary
    # offspring still have a material chance of doing so while preserving local search.
    enum_genes=[g for g in genes if g['type']=='enum']
    structural_p=0.90 if exploratory else 0.40
    if enum_genes and rng.random()<structural_p:
        chosen.append(rng.choice(enum_genes))
    remaining=[g for g in pool if g not in chosen]
    need=max(0,min(count,len(genes))-len(chosen))
    if need:
        if len(remaining)<need:
            remaining=[g for g in genes if g not in chosen]
        chosen.extend(rng.sample(remaining,min(need,len(remaining))))
    out = dict(values)
    for g in chosen:
        n=g['name']; t=g['type']; old=out.get(n,g['default'])
        if t == 'bool': out[n] = not old
        elif t == 'enum':
            opts=[x for x in g['allowed'] if x != old]; out[n]=rng.choice(opts)
        elif t == 'int':
            step=int(g.get('mutation_step',1)); delta=rng.choice([-2,-1,1,2])*step
            out[n]=int(old)+delta
        elif t == 'float':
            sigma=float(g.get('mutation_sigma',0.05)); out[n]=float(old)+rng.gauss(0,sigma)
    return canonical_values(out)
