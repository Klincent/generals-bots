from __future__ import annotations
import math, random
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from . import orchestrator as b
from . import nested as n
from . import genome_memory as memory
from .genome import genome_id
from .mutate import mutate, structural_jump
from .crossover import crossover
from .selection import select
from .telemetry import suggested_chromosome
from .evaluator import AGENT, worktree, build, wrapper, plain_wrapper, paired, combine, color_imbalance

X0_STAGE1_TARGET_SHARE=0.30
X0_CATASTROPHIC_FLOOR=0.25


def x0_stage1_slots(specialized_slots:int,target:float=X0_STAGE1_TARGET_SHARE)->int:
    """Choose an integer number of equal-size X0 blocks nearest target share.

    With seven specialized slots this returns three: 3/(7+3)=30%.
    The calculation stays dynamic as the specialized/adversarial suite changes.
    """
    n=max(0,int(specialized_slots))
    if n==0: return 1
    raw=n*target/max(1e-12,1.0-target)
    candidates={max(1,int(math.floor(raw))),max(1,int(math.ceil(raw)))}
    return min(candidates,key=lambda k:(abs(k/(n+k)-target),k))


def x0_game_share(specialized_slots:int,x0_slots:int)->float:
    total=int(specialized_slots)+int(x0_slots)
    return float(x0_slots)/total if total else 0.0


def _frozen_x0_runner(generation:int)->Path:
    b.git('fetch','--no-tags','origin',b.XBR)
    tree=worktree(f'origin/{b.XBR}',Path('/tmp/e4-stage1-frozen-x0'))
    sha=b.git('rev-parse','HEAD',cwd=tree,capture=True).stdout.strip()
    if sha!=b.X0: raise RuntimeError(f'frozen X0 branch moved: {sha}')
    build(tree)
    return plain_wrapper(tree/AGENT/'run.sh',b.RESULTS/f'g{generation:02d}'/'stage1'/'frozen-x0.sh')


def _stage1_eval(values:dict,template_run:Path,rep:list[dict],starts:dict[str,int],s1:int,x0_run:Path,x0_starts:list[int],out:Path,mix:dict)->dict:
    wr=wrapper(template_run,values,out/'candidate.sh'); summaries={}; all_summaries=[]
    for o in rep:
        q=paired(wr,Path(o['run']),starts[o['archetype']],s1,out/'specialized'/o['archetype'])
        summaries[o['archetype']]=q; all_summaries.append(q)
    x0_blocks=[]
    for i,start in enumerate(x0_starts,1):
        q=paired(wr,x0_run,start,s1,out/'x0'/f'block-{i:02d}')
        x0_blocks.append(q); all_summaries.append(q)
    agg=combine(all_summaries); arch={k:float(v['score']) for k,v in summaries.items()}; x0agg=combine(x0_blocks); x0score=float(x0agg['score'])
    minimum=min(list(arch.values())+[x0score]) if (arch or x0_blocks) else 0.0
    fit={
      'aggregate':float(agg['score']),
      'minimum':float(minimum),
      'x0_score':x0score,
      'x0_raw_win_rate':float(x0agg.get('raw_win_rate',0.0)),
      'catastrophic_x0':1.0 if x0score<X0_CATASTROPHIC_FLOOR else 0.0,
      'hof':0.0,
      'color_imbalance':sum(color_imbalance(v) for v in all_summaries)/max(1,len(all_summaries)),
    }
    return {'summaries':summaries,'x0':{'blocks':x0_blocks,'aggregate':x0agg},'archetypes':arch,'aggregate':agg,'fitness':fit,'mix':dict(mix)}


def stage_population(s:dict,t:Path,opps:list[dict],ids:list[str],generation:int):
    memory.migrate_state(s); memory.assert_population_admissible(s,ids)
    template_run=t/AGENT/'run.sh'
    representative={'aggressive-expansion','defense-turtle','doomer-rusher','recent-reference'}
    # Keep the historical representatives and include currently selected co-evolved predators.
    rep=[o for o in opps if o['archetype'] in representative or o['archetype'].startswith('coevo-')]
    if not rep: raise RuntimeError('Stage1 has no specialized/adversarial opponents')
    s1=2 if s.get('phase')=='exploration' else 3; s2=3 if s.get('phase')=='exploration' else 5
    xslots=x0_stage1_slots(len(rep)); share=x0_game_share(len(rep),xslots)
    starts1={o['archetype']:b.allocate(s,s1,f'g{generation:02d}-stage1-{o["archetype"]}') for o in rep}
    x0_starts=[b.allocate(s,s1,f'g{generation:02d}-stage1-x0-{i+1:02d}') for i in range(xslots)]
    x0_run=_frozen_x0_runner(generation)
    mix={'target_x0_share':X0_STAGE1_TARGET_SHARE,'specialized_slots':len(rep),'x0_slots':xslots,'effective_x0_game_share':share,'seeds_per_slot':s1,'x0_sha':b.X0,'catastrophic_x0_floor':X0_CATASTROPHIC_FLOOR}
    print(f'[evolution4] STAGE1 start generation={generation} genomes={len(ids)} specialized={len(rep)} x0_slots={xslots} x0_share={share:.3f} seeds={s1} workers={min(4,len(ids))}',flush=True)
    def one1(gid):
        print(f'[evolution4] STAGE1 GENOME START {gid[:12]}',flush=True)
        out=b.RESULTS/f'g{generation:02d}'/'stage1'/gid[:12]
        ev=_stage1_eval(b.genome_values(gid),template_run,rep,starts1,s1,x0_run,x0_starts,out,mix)
        print(f'[evolution4] STAGE1 GENOME DONE {gid[:12]} score={ev["fitness"]["aggregate"]:.4f} x0={ev["fitness"]["x0_score"]:.4f}',flush=True)
        return {'genome_id':gid,'fitness':ev['fitness'],'stage1':ev}
    got={}
    with ThreadPoolExecutor(max_workers=min(4,len(ids))) as ex:
        futs={ex.submit(one1,gid):gid for gid in ids}
        for f in as_completed(futs): got[futs[f]]=f.result()
    rows=n.decorate_novelty([got[gid] for gid in ids]); top8=select(rows,8)

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
    rows2=n.decorate_novelty([got2[gid] for gid in top8_ids]); top4=select(rows2,4)
    return rows,rows2,top4


def stage1_x0_metrics(rows1:list[dict])->dict:
    scores=sorted(float(r.get('fitness',{}).get('x0_score',0.0)) for r in rows1)
    mix=(rows1[0].get('stage1',{}).get('mix',{}) if rows1 else {})
    return {
      'best':max(scores) if scores else 0.0,
      'median':scores[len(scores)//2] if scores else 0.0,
      'mean':sum(scores)/len(scores) if scores else 0.0,
      'minimum':min(scores) if scores else 0.0,
      'effective_game_share':float(mix.get('effective_x0_game_share',0.0)),
      'specialized_slots':int(mix.get('specialized_slots',0)),
      'x0_slots':int(mix.get('x0_slots',0)),
      'frozen_x0_sha':mix.get('x0_sha',b.X0),
    }


def next_population(top4:list[dict],g:int,s:dict,phase:str,policy:dict):
    rng=random.Random(880000+g); elites=[x['genome_id'] for x in top4]; known=memory.reserved_newborn_ids(s)|set(elites); out=list(elites); vals={x:b.genome_values(x) for x in elites}; stats={'duplicate_rejections':0,'generation_attempts':0,'convergence_exhaustions':0}
    worst=top4[0]['stage2']['archetypes']; bias=None if phase=='exploration' else suggested_chromosome({},worst)
    def add(v,meta): out.append(memory.strict_save_unique(v,meta,known,s,stats))
    for _ in range(int(policy['crossovers'])):
        ia,ib=rng.sample(elites,2); base=crossover(vals[ia],vals[ib],rng); child=mutate(base,rng,False,None if phase=='exploration' or rng.random()<.5 else bias)
        add(child,{'generation':g+1,'kind':'crossover','parents':[ia,ib],'post_crossover_changes':n.mutation_changes(base,child),'bias':None if phase=='exploration' else bias})
    for _ in range(int(policy['locals'])):
        p=rng.choice(elites); pv=vals[p]; child=mutate(pv,rng,False,None if phase=='exploration' or rng.random()<.5 else bias)
        add(child,{'generation':g+1,'kind':'local','parent':p,'changes':n.mutation_changes(pv,child),'bias':None if phase=='exploration' else bias})
    for _ in range(int(policy['macro_jumps'])):
        p=rng.choice(elites); pv=vals[p]; child=structural_jump(pv,rng,2,4)
        add(child,{'generation':g+1,'kind':'macro-jump','parent':p,'changes':n.mutation_changes(pv,child),'architecture_epoch':policy.get('architecture_epoch',0)})
    if len(out)!=16: raise RuntimeError(f'next population size failure {len(out)}')
    memory.assert_population_admissible(s,out)
    attempts=max(1,int(stats['generation_attempts'])); policy['duplicate_rejections']=int(stats['duplicate_rejections']); policy['genome_generation_attempts']=attempts; policy['duplicate_generation_rate']=float(stats['duplicate_rejections'])/attempts; policy['convergence_exhaustions']=int(stats['convergence_exhaustions'])
    return out,elites,bias
