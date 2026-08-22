from __future__ import annotations
import json, random
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from . import orchestrator as b
from .genome import genome_id, save_genome, load_genome
from .mutate import mutate, structural_jump
from .crossover import crossover
from .selection import select
from .diversity import structural_distance, cohort_novelty
from .telemetry import suggested_chromosome
from .evaluator import AGENT, worktree, build, wrapper, plain_wrapper, paired

ADVERSARIES=b.E4/'adversaries'


def mutation_changes(a:dict,bv:dict):
    return {k:[a[k],bv[k]] for k in a if k in bv and a[k]!=bv[k]}


def decorate_novelty(rows:list[dict])->list[dict]:
    vals=[b.genome_values(r['genome_id']) for r in rows]
    for r,n in zip(rows,cohort_novelty(vals)):
        r['fitness']['novelty']=float(n)
    return rows


def build_adversaries(s:dict,t:Path,g:int):
    """Co-evolve a small adversary population from strong current lineages.

    Four macro-mutants are challenged against the official champion. The two
    variants that hurt the champion most are retained and become extra Stage-2
    and promotion-gate opponents for this generation.
    """
    rng=random.Random(970000+g)
    parent_ids=list(dict.fromkeys(list(s.get('breeding_elites',[]))+list(s.get('current_population',[]))[:4]))
    if not parent_ids:
        return [],{'generated':0,'selected':[]},[]
    known=set(parent_ids)|set(b.dead_genome_ids(s))|{x.get('genome_id') for x in s.get('adversary_hof',[]) if x.get('genome_id')}
    candidates=[]
    for i in range(4):
        parent=rng.choice(parent_ids); pv=b.genome_values(parent); v=structural_jump(pv,rng,2,4)
        for _ in range(40):
            gid=genome_id(v)
            if gid not in known: break
            v=structural_jump(v,rng,2,4)
        else:
            raise RuntimeError('unable to generate unique coevolution adversary')
        known.add(gid); p=ADVERSARIES/'genomes'/f'{gid}.json'
        save_genome(p,v,{'kind':'coevolved-adversary','generation':g,'parent':parent,'changes':mutation_changes(pv,v)})
        candidates.append({'genome_id':gid,'values':v,'parent':parent,'path':p,'source':'new'})
    for h in list(s.get('adversary_hof',[]))[:2]:
        gid=h.get('genome_id'); p=ADVERSARIES/'genomes'/f'{gid}.json'
        if gid and p.exists() and gid not in {x['genome_id'] for x in candidates}:
            try:
                candidates.append({'genome_id':gid,'values':load_genome(p)['values'],'parent':h.get('parent'),'path':p,'source':'hof'})
            except Exception:
                pass
    ctree=worktree(f'origin/{b.CHAMPION}',Path('/tmp/e4-coevo-champion')); build(ctree)
    champ=plain_wrapper(ctree/AGENT/'run.sh',b.RESULTS/f'g{g:02d}'/'coevolution'/'champion.sh')
    scored=[]
    for i,a in enumerate(candidates):
        aw=wrapper(t/AGENT/'run.sh',a['values'],b.RESULTS/f'g{g:02d}'/'coevolution'/f'{a["genome_id"][:12]}.sh')
        st=b.allocate(s,2,f'g{g:02d}-coevo-{i}')
        q=paired(champ,aw,st,2,b.RESULTS/f'g{g:02d}'/'coevolution'/a['genome_id'][:12])
        strength=1.0-float(q['score'])
        scored.append({**a,'run':str(aw),'champion_score':float(q['score']),'strength':strength,'summary':q})
    scored.sort(key=lambda x:(x['strength'],x['genome_id']),reverse=True); selected=scored[:2]
    old={x.get('genome_id'):x for x in s.get('adversary_hof',[]) if x.get('genome_id')}
    for a in selected:
        old[a['genome_id']]={'genome_id':a['genome_id'],'parent':a.get('parent'),'best_strength':max(float(old.get(a['genome_id'],{}).get('best_strength',0.0)),a['strength']),'last_generation':g,'champion_score':a['champion_score']}
    s['adversary_hof']=sorted(old.values(),key=lambda x:(float(x.get('best_strength',0.0)),x['genome_id']),reverse=True)[:8]
    opps=[{'archetype':f'coevo-{a["genome_id"][:8]}','ref':'coevolved','sha':a['genome_id'],'run':a['run'],'tree':'dynamic'} for a in selected]
    keep={a['genome_id'] for a in selected}; paths=[a['path'] for a in candidates if a['genome_id'] in keep]
    report={'generated':len(candidates),'selected':[{'genome_id':a['genome_id'],'parent':a.get('parent'),'strength':a['strength'],'champion_score':a['champion_score'],'source':a['source']} for a in selected]}
    print('[evolution4] COEVOLUTION selected '+', '.join(f"{x['genome_id'][:8]}:{x['strength']:.3f}" for x in report['selected']),flush=True)
    return opps,report,paths


def stage_population(s:dict,t:Path,opps:list[dict],ids:list[str],generation:int):
    template_run=t/AGENT/'run.sh'; rep_names=['aggressive-expansion','defense-turtle','doomer-rusher','recent-reference']; rep=[o for o in opps if o['archetype'] in rep_names]
    s1=2 if s.get('phase')=='exploration' else 3; s2=3 if s.get('phase')=='exploration' else 5
    starts1={o['archetype']:b.allocate(s,s1,f'g{generation:02d}-stage1-{o["archetype"]}') for o in rep}
    print(f'[evolution4] STAGE1 start generation={generation} genomes={len(ids)} seeds={s1} workers={min(4,len(ids))}',flush=True)
    def one1(gid):
        print(f'[evolution4] STAGE1 GENOME START {gid[:12]}',flush=True)
        out=b.RESULTS/f'g{generation:02d}'/'stage1'/gid[:12]; ev=b.eval_genome(b.genome_values(gid),template_run,rep,starts1,s1,out)
        print(f'[evolution4] STAGE1 GENOME DONE {gid[:12]} score={ev["fitness"]["aggregate"]:.4f}',flush=True)
        return {'genome_id':gid,'fitness':ev['fitness'],'stage1':ev}
    got={}
    with ThreadPoolExecutor(max_workers=min(4,len(ids))) as ex:
        futs={ex.submit(one1,gid):gid for gid in ids}
        for f in as_completed(futs): got[futs[f]]=f.result()
    rows=decorate_novelty([got[gid] for gid in ids]); top8=select(rows,8)
    starts2={o['archetype']:b.allocate(s,s2,f'g{generation:02d}-stage2-{o["archetype"]}') for o in opps}
    print(f'[evolution4] STAGE2 start generation={generation} genomes={len(top8)} opponents={len(opps)} seeds={s2} workers={min(4,len(top8))}',flush=True)
    stage1_by={r['genome_id']:r['stage1'] for r in top8}; top8_ids=[r['genome_id'] for r in top8]
    def one2(gid):
        print(f'[evolution4] STAGE2 GENOME START {gid[:12]}',flush=True)
        out=b.RESULTS/f'g{generation:02d}'/'stage2'/gid[:12]; ev=b.eval_genome(b.genome_values(gid),template_run,opps,starts2,s2,out)
        print(f'[evolution4] STAGE2 GENOME DONE {gid[:12]} score={ev["fitness"]["aggregate"]:.4f}',flush=True)
        return {'genome_id':gid,'fitness':ev['fitness'],'stage1':stage1_by[gid],'stage2':ev}
    got2={}
    with ThreadPoolExecutor(max_workers=min(4,len(top8_ids))) as ex:
        futs={ex.submit(one2,gid):gid for gid in top8_ids}
        for f in as_completed(futs): got2[futs[f]]=f.result()
    rows2=decorate_novelty([got2[gid] for gid in top8_ids]); top4=select(rows2,4)
    return rows,rows2,top4


def evolution_policy(s:dict,g:int,rows2:list[dict],top4:list[dict])->dict:
    scores=sorted(float(r['fitness'].get('aggregate',0.0)) for r in rows2); best=max(scores) if scores else 0.0; median=scores[len(scores)//2] if scores else 0.0
    tv=[b.genome_values(x['genome_id']) for x in top4]; ds=[]
    for i in range(len(tv)):
        for j in range(i+1,len(tv)): ds.append(structural_distance(tv[i],tv[j]))
    diversity=sum(ds)/len(ds) if ds else 0.0
    recent=[float(x.get('best_stage2',-1.0)) for x in s.get('generation_history',[])[-4:] if 'best_stage2' in x]
    plateau=len(recent)>=4 and best<=max(recent)+0.01
    epoch=int(s.get('architecture_epoch',0)); last=int(s.get('last_architecture_epoch_generation',-99))
    if plateau and g-last>=4:
        epoch+=1; s['architecture_epoch']=epoch; s['last_architecture_epoch_generation']=g
    phase=s.get('phase','exploration')
    if phase=='exploration': macro=5 if plateau else 4; local=3
    else: macro=3 if plateau else 2; local=4
    cross=12-macro-local
    return {'best_stage2':best,'median_stage2':median,'structural_diversity':diversity,'plateau':plateau,'architecture_epoch':epoch,'crossovers':cross,'locals':local,'macro_jumps':macro,'random_first':phase=='exploration'}


def next_population(top4:list[dict],g:int,dead_ids:set[str],phase:str,policy:dict):
    rng=random.Random(880000+g); elites=[x['genome_id'] for x in top4]; known=set(elites)|set(dead_ids); out=list(elites); vals={x:b.genome_values(x) for x in elites}
    worst=top4[0]['stage2']['archetypes']; bias=None if phase=='exploration' else suggested_chromosome({},worst)
    def add(v,meta): out.append(b.save_unique(v,meta,known))
    for _ in range(int(policy['crossovers'])):
        ia,ib=rng.sample(elites,2); base=crossover(vals[ia],vals[ib],rng); child=mutate(base,rng,False,None if phase=='exploration' or rng.random()<.5 else bias)
        add(child,{'generation':g+1,'kind':'crossover','parents':[ia,ib],'post_crossover_changes':mutation_changes(base,child),'bias':None if phase=='exploration' else bias})
    for _ in range(int(policy['locals'])):
        p=rng.choice(elites); pv=vals[p]; child=mutate(pv,rng,False,None if phase=='exploration' or rng.random()<.5 else bias)
        add(child,{'generation':g+1,'kind':'local','parent':p,'changes':mutation_changes(pv,child),'bias':None if phase=='exploration' else bias})
    for _ in range(int(policy['macro_jumps'])):
        p=rng.choice(elites); pv=vals[p]; child=structural_jump(pv,rng,2,4)
        add(child,{'generation':g+1,'kind':'macro-jump','parent':p,'changes':mutation_changes(pv,child),'architecture_epoch':policy.get('architecture_epoch',0)})
    if len(out)!=16: raise RuntimeError(f'next population size failure {len(out)}')
    return out,elites,bias
