from __future__ import annotations
import json, random, shutil
from datetime import datetime, timezone
from pathlib import Path
from tools.evolution4.genome import canonical_values, genome_id, save_genome
from tools.evolution4.mutate import mutate
from tools.evolution4.crossover import crossover
from tools.evolution4.schema import load_schema

ROOT=Path(__file__).resolve().parents[2]
E4=ROOT/'evolution4'; STATE=E4/'state.json'; GENOMES=E4/'genomes'; LEGACY=E4/'legacy_genomes_v1'

def dump(path:Path,obj):
    path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n')

def load_raw(path:Path): return json.loads(path.read_text())

def main():
    s=load_raw(STATE)
    if int(s.get('genome_schema_version',1))>=2 and s.get('mode')=='turbo_structural':
        print('turbo migration already applied'); return
    old_state=json.loads(json.dumps(s))
    LEGACY.mkdir(parents=True,exist_ok=True)
    mapping={}; values_by_new={}; meta_by_new={}
    for p in sorted(GENOMES.glob('*.json')):
        raw=load_raw(p)
        if 'values' not in raw: continue
        oldid=str(raw.get('genome_id',''))
        vals=canonical_values(raw['values']); newid=genome_id(vals)
        if oldid: mapping[oldid]=newid
        values_by_new[newid]=vals; meta_by_new[newid]=dict(raw.get('meta') or {})
        shutil.copy2(p,LEGACY/p.name)
    for newid,vals in values_by_new.items():
        save_genome(GENOMES/f'{newid}.json',vals,{**meta_by_new.get(newid,{}),'schema_migrated_from_v1':True})
    for named in ('founder-x0.json','founder-y0.json'):
        p=GENOMES/named
        if p.exists():
            raw=load_raw(p); vals=canonical_values(raw['values']); save_genome(p,vals,{**(raw.get('meta') or {}),'schema_migrated_from_v1':True})

    def mid(x): return mapping.get(x,x)
    old_elites=list(s.get('breeding_elites') or [])
    if not old_elites:
        raise RuntimeError('no breeding elites to seed turbo population')
    elites=[mid(x) for x in old_elites[:4]]
    elite_vals=[]
    for gid in elites:
        p=GENOMES/f'{gid}.json'
        if not p.exists(): raise RuntimeError(f'migrated elite missing {gid}')
        elite_vals.append(load_raw(p)['values'])

    old_archive=s.get('tested_genomes',{})
    mapped_archive={}
    for oldgid,rec in old_archive.items():
        ng=mid(oldgid); q=dict(rec); q['legacy_v1_genome_id']=oldgid; q['schema_migrated']=True; mapped_archive[ng]=q
    dead={gid for gid,r in mapped_archive.items() if r.get('status')=='dead'}
    known=set(mapped_archive)|set(elites)
    data,_=load_schema(); enum_names=[g['name'] for g in data['genes'] if g['type']=='enum']
    rng=random.Random(505001)

    def structural_changed(child,parent): return any(child[n]!=parent[n] for n in enum_names)
    def force_structural(child,parent):
        if structural_changed(child,parent): return child
        specs=[g for g in data['genes'] if g['type']=='enum']
        g=rng.choice(specs); out=dict(child); opts=[x for x in g['allowed'] if x!=out[g['name']]]; out[g['name']]=rng.choice(opts); return canonical_values(out)
    def save_unique(v,meta,parent=None):
        if parent is not None: v=force_structural(v,parent)
        for _ in range(100):
            gid=genome_id(v)
            if gid not in known and gid not in dead:
                save_genome(GENOMES/f'{gid}.json',v,meta); known.add(gid); return gid
            base=parent if parent is not None else v
            v=force_structural(mutate(v,rng,True),base)
        raise RuntimeError('cannot create unique turbo genome')

    pop=list(elites)
    for i in range(6):
        ia,ib=rng.sample(range(len(elite_vals)),2); base=crossover(elite_vals[ia],elite_vals[ib],rng); child=mutate(base,rng,True)
        pop.append(save_unique(child,{'turbo_generation':0,'kind':'structural-crossover','parents':[elites[ia],elites[ib]]},base))
    for i in range(4):
        k=rng.randrange(len(elite_vals)); base=elite_vals[k]; child=mutate(base,rng,True)
        pop.append(save_unique(child,{'turbo_generation':0,'kind':'structural-local','parent':elites[k]},base))
    for i in range(2):
        k=rng.randrange(len(elite_vals)); base=elite_vals[k]; child=mutate(mutate(base,rng,True),rng,True)
        pop.append(save_unique(child,{'turbo_generation':0,'kind':'macro-jump','parent':elites[k]},base))
    if len(pop)!=16 or len(set(pop))!=16: raise RuntimeError('turbo population diversity failure')

    if 'generation_history' in s: s['legacy_generation_history']=s.get('generation_history',[])
    if 'rejected_promotions' in s: s['legacy_rejected_promotions']=s.get('rejected_promotions',[])
    s['generation_history']=[]; s['rejected_promotions']=[]
    s['current_population']=pop; s['breeding_elites']=elites
    s['official_champion_genome_id']=mid(s.get('official_champion_genome_id'))
    for key in ('founder_x0','founder_y0'):
        if isinstance(s.get(key),dict) and s[key].get('genome_id'): s[key]['genome_id']=mid(s[key]['genome_id'])
    for h in s.get('hall_of_fame',[]):
        if h.get('genome_id'): h['genome_id']=mid(h['genome_id'])
    s['tested_genomes']=mapped_archive; s['tested_genome_count']=len(mapped_archive); s['dead_genome_count']=sum(1 for r in mapped_archive.values() if r.get('status')=='dead')
    s['phase']='exploration'; s['generation']=0; s['experiment_version']=5; s['genome_schema_version']=2; s['mode']='turbo_structural'
    s['turbo_origin']={'source_branch':'evolution4/control','source_generation':old_state.get('generation'),'source_phase':old_state.get('phase'),'started_at':datetime.now(timezone.utc).isoformat(),'structural_gene_count':len(enum_names),'seed_elites_old':old_elites,'seed_elites_new':elites}
    s['pending_promotion']=None; s['retry_count']=0; s['last_error']=None; s['last_successful_transaction_id']=None; s['last_successful_state_hash']=None
    s['last_checkpoint_generation']=-1; s['champion_promotions_since_checkpoint']=0
    dump(E4/'turbo_migration.json',{'mapping':mapping,'source_generation':old_state.get('generation'),'new_population':pop,'new_elites':elites,'structural_genes':enum_names})
    dump(STATE,s)
    print(f'turbo migration complete: mapped={len(mapping)} dead={s["dead_genome_count"]} population={len(pop)} structural_genes={len(enum_names)}')

if __name__=='__main__': main()
