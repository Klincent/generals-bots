from __future__ import annotations
import hashlib, json
from pathlib import Path
from tools.evolution4.genome import canonical_values, env_for as e4_env_for
from .graph import canonical_graph, compile_params, graph_hash


def canonical_genome(genome:dict)->dict:
    return {'graph':canonical_graph(genome['graph']),'params':canonical_values(genome['params'])}


def canonical_json(genome:dict)->str:
    return json.dumps(canonical_genome(genome),sort_keys=True,separators=(',',':'),allow_nan=False)


def genome_id(genome:dict)->str:
    return hashlib.sha256(canonical_json(genome).encode()).hexdigest()


def effective_params(genome:dict)->dict:
    c=canonical_genome(genome); return compile_params(c['graph'],c['params'])


def env_for(genome:dict)->dict[str,str]:
    c=canonical_genome(genome); out=e4_env_for(compile_params(c['graph'],c['params']))
    out.update({
        'EVO5_GRAPH_HASH':graph_hash(c['graph']),
        'EVO5_GRAPH_MODE':c['graph']['mode'],
        'EVO5_GRAPH_NODES':str(len(c['graph']['nodes'])),
        'EVO5_ACTIVE_MODULES':','.join(sorted({m for q in c['graph']['nodes'].values() for m in q['modules']})),
    })
    return out


def save_genome(path:Path,genome:dict,meta:dict|None=None)->str:
    c=canonical_genome(genome); gid=genome_id(c); path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps({'genome_id':gid,'genome':c,'meta':meta or {}},indent=2,sort_keys=True)+'\n')
    return gid


def load_genome(path:Path)->dict:
    p=json.loads(path.read_text()); c=canonical_genome(p['genome'])
    if p.get('genome_id')!=genome_id(c): raise ValueError('Evolution5 genome hash mismatch')
    return {'genome_id':p['genome_id'],'genome':c,'meta':p.get('meta',{})}
