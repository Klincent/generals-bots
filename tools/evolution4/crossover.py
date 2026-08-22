from __future__ import annotations
import random
from .schema import chromosomes
from .genome import canonical_values

def crossover(a: dict, b: dict, rng: random.Random, chromosome_probability: float=0.70) -> dict:
    out = dict(a); groups = chromosomes()
    for _, names in groups.items():
        if rng.random() < chromosome_probability:
            src = a if rng.random() < 0.5 else b
            for n in names: out[n] = src[n]
        else:
            for n in names: out[n] = a[n] if rng.random() < 0.5 else b[n]
    return canonical_values(out)
