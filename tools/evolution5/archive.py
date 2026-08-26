from __future__ import annotations
from .graph import descriptor, descriptor_key


def update_archive(state:dict,rows:list[dict],load_genome,generation:int)->int:
    archive=state.setdefault('map_elites',{})
    changed=0
    for row in rows:
        gid=row['genome_id']; genome=load_genome(gid)
        key=descriptor_key(genome); fit=row.get('fitness',{})
        score=float(fit.get('aggregate',0.0)); win=float(fit.get('raw_win_rate',0.0)); minimum=float(fit.get('minimum',0.0))
        cur=archive.get(key)
        if cur is None or (score,minimum,win)>(float(cur.get('score',0)),float(cur.get('minimum',0)),float(cur.get('win_rate',0))):
            archive[key]={'genome_id':gid,'generation':generation,'score':score,'win_rate':win,'minimum':minimum,'descriptor':descriptor(genome)}; changed+=1
    return changed


def archive_ids(state:dict)->set[str]:
    return {x.get('genome_id') for x in state.get('map_elites',{}).values() if x.get('genome_id')}
