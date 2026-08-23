from __future__ import annotations
import os, uuid
from pathlib import Path
from . import orchestrator as b
from .nested import build_adversaries, evolution_policy
from .selection_memory import stage_population, stage1_x0_metrics, next_population
from . import genome_memory as memory


def generation(s:dict,txid:str):
    memory.migrate_state(s)
    pre=int(s['generation']); g=pre+1; b.stop_check(f'nested generation {g}')
    t=b.ensure_template(); fixed=b.resolve_opponents()
    # The pinned competition matchup automatically invokes build.sh when a
    # runner lives next to one. Stage1/Stage2 evaluate genomes in parallel, so
    # handing every worker the same opponent worktree run.sh caused concurrent
    # g++ processes to replace the same `agent` binary. resolve_opponents() has
    # already built each opponent once; expose read-only wrapper runners.
    for i,o in enumerate(fixed):
        src=Path(o['run']).resolve(); safe=b.plain_wrapper(src,Path(f'/tmp/e4-fixed-opponent-{i}.sh')); o['run']=str(safe)

    coevo,coevo_report,adv_paths=build_adversaries(s,t,g); opps=fixed+coevo
    ids=list(s['current_population']); memory.assert_population_admissible(s,ids)
    rows1,rows2,top4=stage_population(s,t,opps,ids,g)
    x0metrics=stage1_x0_metrics(rows1)

    proposal=top4[0]; accepted,evidence=b.promotion_screen(s,proposal,t,opps,g); promoted=None
    if accepted:
        promoted=b.promote(s,proposal['genome_id'],t,evidence,g,txid)
    else:
        s.setdefault('rejected_promotions',[]).append({'generation':g,**evidence})

    dead=memory.archive_generation_results(s,g,rows1,rows2,top4)
    policy=evolution_policy(s,g,rows2,top4); policy['stage1_x0']=x0metrics
    nxt,elites,bias=next_population(top4,g,s,s.get('phase','exploration'),policy)
    s['current_population']=nxt; s['breeding_elites']=elites; s['generation']=g
    s['selection_policy_version']=2; s['genome_memory_version']=memory.MEMORY_VERSION
    if g>=60: s['phase']='final'
    elif g>=20: s['phase']='exploitation'
    else: s['phase']='exploration'

    report={
      'generation':g,'phase':s['phase'],'mode':'turbo_nested_v2','genome_schema_version':s.get('genome_schema_version',2),
      'stage1':rows1,'stage1_x0':x0metrics,'stage2':rows2,'top4':[x['genome_id'] for x in top4],
      'dead_genome_count':len(dead),'mutation_bias':bias,'evolution_policy':policy,'coevolution':coevo_report,
      'promotion':evidence,'promoted_commit':promoted}
    p=b.RESULTS/f'g{g:02d}'/'report.json'; b.dump(p,report)
    s['mode']='turbo_nested_v2'
    s.setdefault('generation_history',[]).append({
      'generation':g,'top4':[x['genome_id'] for x in top4],
      'promotion_decision':evidence['decision'],'official_champion_genome_id':s['official_champion_genome_id'],
      'best_stage2':policy['best_stage2'],'median_stage2':policy['median_stage2'],
      'stage1_x0_best':x0metrics['best'],'stage1_x0_median':x0metrics['median'],'stage1_x0_mean':x0metrics['mean'],
      'stage1_x0_game_share':x0metrics['effective_game_share'],'stage1_x0_slots':x0metrics['x0_slots'],
      'structural_diversity':policy['structural_diversity'],'architecture_epoch':policy['architecture_epoch'],
      'duplicate_generation_rate':policy.get('duplicate_generation_rate',0.0),'dead_genome_count':int(s.get('dead_genome_count',0)),
      'coevolved_opponents':[x['genome_id'] for x in coevo_report.get('selected',[])]})

    extra=list(adv_paths)
    if g%5==0: extra.append(b.audit(s,opps,g))
    if g%5==0 or int(s.get('champion_promotions_since_checkpoint',0))>=3: extra.extend(b.checkpoint(s))
    s['retry_count']=0; s['last_error']=None; s['last_successful_transaction_id']=txid; s['last_successful_state_hash']=b.state_digest(s)
    b.dump(b.STATE,s); b.heartbeat_finish(s,txid,'success')
    b.persist([b.STATE,b.HEART,p,*extra,*[b.genome_path(x) for x in nxt]],f'evolution4 turbo nested: complete generation {g}')
    b.verify_remote(s['phase'],g,txid)
    if g!=pre+1: raise RuntimeError('false-green nested generation transition')


def main():
    os.chdir(b.ROOT); b.git('config','user.name','ChatGPT'); b.git('config','user.email','actions@users.noreply.github.com')
    s=b.load_state(); txid=str(uuid.uuid4()); b.heartbeat_start(s,txid)
    try:
        b.stop_check('at nested transaction start')
        if s['phase']=='bootstrap': b.bootstrap(s,txid)
        elif s['phase'] in ('exploration','exploitation'): generation(s,txid)
        elif s['phase']=='final': b.final_run(s,txid)
        elif s['phase']=='done': b.heartbeat_finish(s,txid,'done'); b.persist([b.HEART],f'evolution4: done heartbeat {txid[:8]}')
        elif s['phase']=='stopped': raise StopIteration('state stopped')
        else: raise RuntimeError(f'bad phase {s["phase"]}')
        return 0
    except StopIteration as e:
        print(e); return 0
    except Exception as e:
        print('EVOLUTION4 NESTED INFRASTRUCTURE FAILURE:',repr(e),file=__import__('sys').stderr); b.fail(s,txid,e); return 2


if __name__=='__main__': raise SystemExit(main())
