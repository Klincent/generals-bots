from __future__ import annotations
import hashlib, json
from pathlib import Path
from .schema import load_schema, defaults

def canonical_values(values: dict) -> dict:
    _, by = load_schema()
    out = {}
    for name, spec in by.items():
        v = values.get(name, spec['default'])
        t = spec['type']
        if t == 'bool': v = bool(v)
        elif t == 'int': v = int(round(float(v)))
        elif t == 'float': v = float(v)
        elif t == 'enum':
            if v not in spec['allowed']: raise ValueError(f'{name}: invalid enum {v}')
        if t in ('int','float'):
            v = max(spec['minimum'], min(spec['maximum'], v))
        out[name] = v
    return repair_genome(out)

def repair_genome(v: dict) -> dict:
    v = dict(v)
    if v['production_soft_gap'] >= v['production_severe_gap']:
        v['production_soft_gap'] = max(2, v['production_severe_gap'] - 2)
    if v['castle1_target_turn'] >= v['castle2_target_turn']:
        v['castle2_target_turn'] = min(420, v['castle1_target_turn'] + 50)
        if v['castle2_target_turn'] <= v['castle1_target_turn']:
            v['castle1_target_turn'] = max(90, v['castle2_target_turn'] - 50)
    if v['muster_ratio_num'] <= 0: v['muster_ratio_num'] = 1
    if v['muster_ratio_den'] <= 0: v['muster_ratio_den'] = 1
    if v['precontact_expansion_until'] < -1: v['precontact_expansion_until'] = -1
    return v

def validate_genome(v: dict) -> None:
    _, by = load_schema()
    if set(v) != set(by): raise ValueError('genome keys differ from schema')
    for name, spec in by.items():
        x = v[name]; t = spec['type']
        if t == 'bool' and not isinstance(x, bool): raise ValueError(name)
        if t == 'int' and (not isinstance(x, int) or isinstance(x, bool)): raise ValueError(name)
        if t == 'float' and not isinstance(x, (int,float)): raise ValueError(name)
        if t in ('int','float') and not (spec['minimum'] <= x <= spec['maximum']): raise ValueError(name)
    if v['production_soft_gap'] >= v['production_severe_gap']: raise ValueError('production gaps')
    if v['castle1_target_turn'] >= v['castle2_target_turn']: raise ValueError('castle turns')

def canonical_json(v: dict) -> str:
    c = canonical_values(v); validate_genome(c)
    return json.dumps(c, sort_keys=True, separators=(',',':'), allow_nan=False)

def genome_id(v: dict) -> str:
    return hashlib.sha256(canonical_json(v).encode()).hexdigest()

def save_genome(path: Path, values: dict, meta: dict | None = None) -> str:
    c = canonical_values(values); gid = genome_id(c)
    payload = {'genome_id':gid,'values':c,'meta':meta or {}}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True)+'\n')
    return gid

def load_genome(path: Path) -> dict:
    p = json.loads(path.read_text())
    v = canonical_values(p['values']); validate_genome(v)
    if p.get('genome_id') != genome_id(v): raise ValueError('genome hash mismatch')
    return p

def founder_x0() -> dict:
    return defaults()

def founder_y0() -> dict:
    v = defaults(); v['precontact_expansion_until'] = 250; v['expansion_share_precontact'] = 0.40
    return canonical_values(v)

def env_for(values: dict) -> dict[str,str]:
    _, by = load_schema(); c = canonical_values(values)
    out = {}
    for name, spec in by.items():
        x = c[name]
        if spec['type'] == 'bool': out[spec['env']] = '1' if x else '0'
        elif spec['type'] == 'float': out[spec['env']] = format(float(x), '.12g')
        else: out[spec['env']] = str(x)
    return out
