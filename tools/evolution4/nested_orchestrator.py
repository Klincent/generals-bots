from __future__ import annotations
import os, uuid
from . import orchestrator as b
from .nested import build_adversaries, stage_population, evolution_policy, next_population


def generation(s:dict,txid:str):
    pre=int(s['generation']); g=pre+1; b.stop_check(f'nested generation {g}')
    t=b.ensure_template(); fixed=b.resolve_opponents()
    coevo,coevo_report,adv_paths=build_adversaries(s,t,g); opps=fixed+coevo
    ids=list(s['current_population']); rows1,rows2,top4=stage_population(s,t,opps,ids,g)

    proposal=top4[0]; accepted,evidence=b.promotion_screen(s,proposal,t,opps,g); promoted=None
    if accepted:
        promoted=b.promote(s,proposal['genome_id'],t,evidence,g,txid)
    else:
        s.setdefault('rejected_promotions',[]).append({'generation':g,**evidence})

    dead=b.archive_generation_results(s,g,rows1,rows2,top4)
    policy=evolution_policy(s,g,rows2,top4)
    nxt,elites,bias=next_population(top4,g,dead,s.get('phase','exploration'),policy)
    s['current_population']=nxt; s['breeding_elites']=elites; s['generation']=g
    if g>=60: s['phase']='final'
    elif g>=20: s['phase']='exploitation'
    else: s['phase']='exploration'

    report={
      'generation':g,'phase':s['phase'],'mode':'turbo_nested_v2','genome_schema_version':s.get('genome_schema_version',2),
      'stage1':rows1,'stage2':rows2,'top4':[x['genome_id'] for x in top4],
      'mutation_bias':bias,'evolution_policy':policy,'coevolution':coevo_report,
      'promotion':evidence,'promoted_commit':promoted}
    p=b.RESULTS/f'g{g:02d}'/'report.json'; b.dump(p,report)
    s['mode']='turbo_nested_v2'
    s.setdefault('generation_history',[]).append({
      'generation':g,'top4':[x['genome_id'] for x in top4],
      'promotion_decision':evidence['decision'],'official_champion_genome_id':s['official_champion_genome_id'],
      'best_stage2':policy['best_stage2'],'median_stage2':policy['median_stage2'],
      'structural_diversity':policy['structural_diversity'],'architecture_epoch':policy['architecture_epoch'],
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
