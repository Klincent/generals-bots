from __future__ import annotations
import random
from . import orchestrator as b
from .genome import genome_id, load_genome, save_genome
from .mutate import mutate
from .schema import load_schema

VALID_STATUSES={'alive','elite','champion','dead','invalid','infra_unresolved'}
MEMORY_VERSION=2


def protected_genome_ids(s:dict)->set[str]:
    out=set()
    q=s.get('official_champion_genome_id')
    if q: out.add(q)
    for h in s.get('hall_of_fame',[]):
        q=h.get('genome_id')
        if q: out.add(q)
    return out


def dead_genome_ids(s:dict)->set[str]:
    return {gid for gid,rec in s.get('tested_genomes',{}).items() if rec.get('status')=='dead'}


def may_retest_existing(s:dict,gid:str)->bool:
    """Existing elites/champions may be re-evaluated; exact dead genomes may not."""
    return s.get('tested_genomes',{}).get(gid,{}).get('status')!='dead'


def reserved_newborn_ids(s:dict)->set[str]:
    """IDs that a newly bred child may not duplicate.

    infra_unresolved is intentionally not a permanent tombstone: it never
    received valid gameplay evidence and may therefore be retried later.
    """
    out=set(s.get('current_population',[]))|set(s.get('breeding_elites',[]))|protected_genome_ids(s)
    for gid,rec in s.get('tested_genomes',{}).items():
        if rec.get('status')!='infra_unresolved': out.add(gid)
    return out


def candidate_allowed(s:dict,gid:str,known:set[str]|None=None)->bool:
    if known is not None and gid in known: return False
    if gid in protected_genome_ids(s): return False
    status=s.get('tested_genomes',{}).get(gid,{}).get('status')
    return status not in {'dead','alive','elite','champion','invalid','survivor'}


def assert_population_admissible(s:dict,ids:list[str])->None:
    if len(ids)!=len(set(ids)): raise RuntimeError('duplicate genome in current population')
    bad=sorted(set(ids)&dead_genome_ids(s))
    if bad: raise RuntimeError('dead genome re-entered population: '+','.join(x[:12] for x in bad))


def _provenance(gid:str)->dict:
    try:
        raw=load_genome(b.genome_path(gid)); meta=dict(raw.get('meta') or {}); vals=raw['values']
        data,_=load_schema(); enums=[g['name'] for g in data['genes'] if g['type']=='enum']
        birth=meta.get('generation',meta.get('turbo_generation',meta.get('birth_generation')))
        parents=[]
        if meta.get('parent'): parents.append(meta['parent'])
        parents.extend(list(meta.get('parents') or []))
        return {
          'birth_generation':birth,
          'parentage':list(dict.fromkeys(parents)),
          'mutation_lineage':{'kind':meta.get('kind',meta.get('origin')),'changes':meta.get('changes',meta.get('post_crossover_changes',{})),'bias':meta.get('bias')},
          'structural_lineage':{n:vals[n] for n in enums if n in vals},
        }
    except Exception:
        return {'birth_generation':None,'parentage':[],'mutation_lineage':{},'structural_lineage':{}}


def migrate_state(s:dict)->dict:
    """Idempotently upgrade legacy survivor/dead records without advancing evolution."""
    archive=s.setdefault('tested_genomes',{}); protected=protected_genome_ids(s); elites=set(s.get('breeding_elites',[]))
    for gid,rec in archive.items():
        status=rec.get('status','alive')
        if status=='survivor': status='elite'
        if status not in VALID_STATUSES: status='alive'
        if gid in protected: status='champion'
        elif gid in elites and status!='dead': status='elite'
        rec['status']=status
        rec.setdefault('fitness_history',[])
        prov=_provenance(gid)
        for k,v in prov.items(): rec.setdefault(k,v)
        if status=='dead': rec.setdefault('death_generation',rec.get('last_tested_generation'))
    s['genome_memory_version']=MEMORY_VERSION
    s['tested_genome_count']=len(archive)
    s['dead_genome_count']=sum(1 for rec in archive.values() if rec.get('status')=='dead')
    return s


def mark_infra_unresolved(s:dict,gid:str,generation:int,reason:str)->None:
    archive=s.setdefault('tested_genomes',{}); rec=archive.setdefault(gid,{})
    if rec.get('status')=='dead': return
    if gid in protected_genome_ids(s): rec['status']='champion'
    elif rec.get('status')!='elite': rec['status']='infra_unresolved'
    rec['last_infra_generation']=generation; rec['last_infra_reason']=reason
    rec.setdefault('fitness_history',[])


def archive_generation_results(s:dict,g:int,rows1:list[dict],rows2:list[dict],top4:list[dict])->set[str]:
    """Tombstone only genomes eliminated after valid completed gameplay.

    This function is called only after Stage 1/2 return successfully. The outer
    transaction reloads durable state on infrastructure failure, so interrupted
    evaluations cannot become evolutionary deaths.
    """
    migrate_state(s); archive=s.setdefault('tested_genomes',{}); stage2={r['genome_id']:r for r in rows2}; survivors={r['genome_id'] for r in top4}; protected=protected_genome_ids(s)
    for r in rows1:
        gid=r['genome_id']; rec=archive.setdefault(gid,{})
        if rec.get('status')=='dead' and gid in survivors: raise RuntimeError(f'dead genome resurrected as survivor {gid}')
        prov=_provenance(gid)
        for k,v in prov.items(): rec.setdefault(k,v)
        rec.setdefault('first_tested_generation',g); rec['last_tested_generation']=g; rec['times_tested']=int(rec.get('times_tested',0))+1
        f1=r.get('fitness',{}); f2=stage2.get(gid,{}).get('fitness',{}) if gid in stage2 else {}
        hist=[x for x in rec.get('fitness_history',[]) if int(x.get('generation',-1))!=g]
        hist.append({
          'generation':g,
          'stage1_score':float(f1.get('aggregate',0.0)),
          'stage1_x0_score':None if 'x0_score' not in f1 else float(f1.get('x0_score',0.0)),
          'stage1_minimum':float(f1.get('minimum',0.0)),
          'stage1_novelty':float(f1.get('novelty',0.0)),
          'stage2_score':None if not f2 else float(f2.get('aggregate',0.0)),
        })
        rec['fitness_history']=hist
        rec['stage1_score']=float(f1.get('aggregate',0.0))
        if 'x0_score' in f1: rec['stage1_x0_score']=float(f1['x0_score'])
        if f2: rec['stage2_score']=float(f2.get('aggregate',0.0))
        if gid in protected:
            rec['status']='champion'; rec.pop('death_generation',None); rec.pop('death_reason',None)
        elif gid in survivors:
            if rec.get('status')=='dead': raise RuntimeError(f'exact dead tombstone would be revived {gid}')
            rec['status']='elite'; rec.pop('death_generation',None); rec.pop('death_reason',None)
        else:
            # Permanent tombstone. Never overwrite its original death generation.
            rec['status']='dead'; rec.setdefault('death_generation',g); rec.setdefault('death_reason','selection_eliminated')
    s['dead_genome_count']=sum(1 for rec in archive.values() if rec.get('status')=='dead'); s['tested_genome_count']=len(archive)
    return dead_genome_ids(s)


def strict_save_unique(values:dict,meta:dict,known:set[str],s:dict,stats:dict|None=None)->str:
    stats=stats if stats is not None else {}
    for _ in range(60):
        gid=genome_id(values); stats['generation_attempts']=int(stats.get('generation_attempts',0))+1
        if candidate_allowed(s,gid,known):
            save_genome(b.genome_path(gid),values,meta); known.add(gid); return gid
        stats['duplicate_rejections']=int(stats.get('duplicate_rejections',0))+1
        # Deterministic escape from an exact historical/current duplicate.
        seed=int(gid[:12],16)^len(known)^int(stats['generation_attempts'])*0x9E3779B1
        values=mutate(values,random.Random(seed),False)
    stats['convergence_exhaustions']=int(stats.get('convergence_exhaustions',0))+1
    raise RuntimeError('could not generate a genome outside durable exact-genome memory')
