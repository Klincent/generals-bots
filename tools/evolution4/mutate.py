from __future__ import annotations
import random
from .schema import load_schema
from .genome import canonical_values

# picker_neutrals_max is retained only for observability/backward compatibility.
# X0 computes it for telemetry but does not use it in the picker allow decision.
NON_EVOLVABLE={'picker_neutrals_max'}


def evolvable_genes():
    data,_=load_schema()
    return [g for g in data['genes'] if g['name'] not in NON_EVOLVABLE]


def mutate(values: dict, rng: random.Random, exploratory: bool=False, bias_chromosome: str|None=None) -> dict:
    genes=evolvable_genes(); pool=genes
    if bias_chromosome and rng.random()<0.70:
        q=[g for g in genes if g['chromosome']==bias_chromosome]
        if q: pool=q
    count=rng.randint(4,8) if exploratory else rng.randint(1,3)
    chosen=[]
    enum_genes=[g for g in genes if g['type']=='enum']
    structural_p=0.90 if exploratory else 0.40
    if enum_genes and rng.random()<structural_p:
        chosen.append(rng.choice(enum_genes))
    remaining=[g for g in pool if g not in chosen]
    need=max(0,min(count,len(genes))-len(chosen))
    if need:
        if len(remaining)<need: remaining=[g for g in genes if g not in chosen]
        chosen.extend(rng.sample(remaining,min(need,len(remaining))))
    out=dict(values)
    for g in chosen:
        n=g['name']; t=g['type']; old=out.get(n,g['default'])
        if t=='bool': out[n]=not old
        elif t=='enum':
            opts=[x for x in g['allowed'] if x!=old]
            if opts: out[n]=rng.choice(opts)
        elif t=='int':
            step=int(g.get('mutation_step',1)); out[n]=int(old)+rng.choice([-2,-1,1,2])*step
        elif t=='float':
            sigma=float(g.get('mutation_sigma',0.05)); out[n]=float(old)+rng.gauss(0,sigma)
    return canonical_values(out)


def structural_jump(values:dict,rng:random.Random,min_structural:int=2,max_structural:int=4)->dict:
    """Macro mutation: guaranteed real algorithm changes plus broad numeric mutation."""
    genes=evolvable_genes(); enums=[g for g in genes if g['type']=='enum']
    out=mutate(values,rng,True,None)
    if enums:
        k=min(len(enums),rng.randint(min_structural,max(min_structural,min(max_structural,len(enums)))))
        for g in rng.sample(enums,k):
            n=g['name']; old=out.get(n,g['default']); opts=[x for x in g['allowed'] if x!=old]
            if opts: out[n]=rng.choice(opts)
    # One extra local mutation makes macro jumps combine architecture and parameters.
    out=mutate(canonical_values(out),rng,False,None)
    return canonical_values(out)
