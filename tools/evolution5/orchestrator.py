from __future__ import annotations
import hashlib, json, os, random, shutil, subprocess, uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from tools.evolution4 import evaluator as ev
from tools.evolution4.evaluator import ROOT, AGENT
from .archive import update_archive, archive_ids
from .bootstrap import ensure_bootstrap
from .freeze import freeze_submission
from .genome import env_for, genome_id, load_genome as load_genome_file, save_genome
from .graph import ISLANDS, graph_distance
from .league import consider as consider_league
from .mutate import NORMAL_MIX, PLATEAU_MIX, choose_kind, micro_mutation, module_mutation, graph_rewrite, strategy_bundle, crossover_genomes, random_immigrant

CONTROL='evolution5/cambrian-league'; E5=ROOT/'evolution5'; STATE=E5/'state.json'; HEART=E5/'heartbeat.json'; STOP=E5/'STOP'; GENOMES=E5/'genomes'; RESULTS=E5/'results'; CHECKPOINTS=E5/'checkpoints'; TMP=Path('/tmp/e5-eval')


def now(): return datetime.now(timezone.utc).isoformat()
def dump(path:Path,obj): path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n')
def load_state(): return json.loads(STATE.read_text())
def state_hash(s): return hashlib.sha256(json.dumps(s,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def git(*args,check=True,capture=False): return ev.run(['git',*args],cwd=ROOT,check=check,capture=capture,timeout=120)

def persist(paths:list[Path],message:str):
    uniq=[]
    for p in paths:
        if p.exists() and p not in uniq: uniq.append(p)
    if not uniq: return
    git('add',*[str(p) for p in uniq])
    if git('diff','--cached','--quiet',check=False).returncode==0: return
    git('commit','-m',message); git('push','origin',f'HEAD:{CONTROL}')

def stop_check():
    git('fetch','--no-tags','origin',CONTROL)
    if git('cat-file','-e',f'origin/{CONTROL}:evolution5/STOP',check=False,capture=True).returncode==0: raise StopIteration('evolution5/STOP present')

def load_genome(gid:str)->dict:
    return load_genome_file(GENOMES/f'{gid}.json')['genome']

def allocate(state:dict,stream:str,count:int,label:str)->int:
    led=state['seed_ledger'][stream]; start=int(led['next_seed']); led['next_seed']=start+count+37; led['ranges'].append({'label':label,'start':start,'maps':count}); return start

def wrapper(run_sh:Path,genome:dict,out:Path)->Path:
    out.parent.mkdir(parents=True,exist_ok=True); lines=['#!/usr/bin/env bash','set -euo pipefail']
    for k,v in env_for(genome).items(): lines.append(f'export {k}={json.dumps(v)}')
    lines.append(f'exec {json.dumps(str(run_sh))}'); out.write_text('\n'.join(lines)+'\n'); out.chmod(0o755); return out

def rotate(opps:list[dict],generation:int,count:int,offset:int=0)->list[dict]:
    if len(opps)<=count: return list(opps)
    start=(generation*3+offset)%len(opps); return [opps[(start+i)%len(opps)] for i in range(count)]

def evaluate(genome:dict,run_sh:Path,opps:list[dict],starts:dict[str,int],seeds:int,out:Path)->dict:
    cand=wrapper(run_sh,genome,out/'candidate.sh'); summaries={}
    for o in opps: summaries[o['archetype']]=ev.paired(cand,Path(o['run']),starts[o['archetype']],seeds,out/o['archetype'])
    agg=ev.combine(list(summaries.values())); arch={k:float(v.get('score',0.0)) for k,v in summaries.items()}
    fit={'aggregate':float(agg['score']),'raw_win_rate':float(agg['raw_win_rate']),'minimum':min(arch.values()) if arch else 0.0,'color_imbalance':sum(ev.color_imbalance(v) for v in summaries.values())/max(1,len(summaries))}
    return {'aggregate':agg,'archetypes':arch,'summaries':summaries,'fitness':fit}

def parallel_stage(state:dict,g:int,ids:list[str],opps:list[dict],stream:str,seeds:int,label:str,max_workers:int=4)->list[dict]:
    run_sh=ROOT/AGENT/'run.sh'; starts={o['archetype']:allocate(state,stream,seeds,f'g{g:03d}-{label}-{o["archetype"]}') for o in opps}; outbase=TMP/f'g{g:03d}'/label
    def one(gid):
        q=evaluate(load_genome(gid),run_sh,opps,starts,seeds,outbase/gid[:12]); return {'genome_id':gid,'fitness':q['fitness'],label:q}
    got={}
    with ThreadPoolExecutor(max_workers=min(max_workers,len(ids))) as pool:
        futs={pool.submit(one,gid):gid for gid in ids}
        for f in as_completed(futs): got[futs[f]]=f.result()
    return [got[x] for x in ids]

def island_of(state:dict,gid:str)->str:
    for name,q in state['islands'].items():
        if gid in q.get('population',[]): return name
    return 'Unknown'

def rank_key(row:dict):
    f=row['fitness']; return (float(f.get('aggregate',0)),float(f.get('minimum',0)),float(f.get('raw_win_rate',0)),-float(f.get('color_imbalance',1)))

def stage1_survivors(state:dict,rows:list[dict])->list[str]:
    out=[]
    for island in ISLANDS:
        q=[r for r in rows if island_of(state,r['genome_id'])==island]; q.sort(key=rank_key,reverse=True); out.extend(r['genome_id'] for r in q[:3])
    if len(out)!=24: raise RuntimeError(f'Stage1 diversity funnel expected 24, got {len(out)}')
    return out

def stage2_elites(state:dict,rows:list[dict])->tuple[list[dict],dict[str,list[dict]]]:
    by={name:[] for name in ISLANDS}
    for r in rows: by[island_of(state,r['genome_id'])].append(r)
    elites=[]
    for name in ISLANDS:
        by[name].sort(key=rank_key,reverse=True)
        if not by[name]: raise RuntimeError(f'island vanished in stage2: {name}')
        elites.append(by[name][0])
    return elites,by

def fresh_stage(state:dict,g:int,candidates:list[dict],opps:list[dict])->list[dict]:
    run_sh=ROOT/AGENT/'run.sh'; fresh_opps=rotate(opps,g,6,5); starts={o['archetype']:allocate(state,'holdout',4,f'g{g:03d}-fresh-{o["archetype"]}') for o in fresh_opps}; rows=[]
    for base in candidates:
        gid=base['genome_id']; fresh=evaluate(load_genome(gid),run_sh,fresh_opps,starts,4,TMP/f'g{g:03d}'/'fresh'/gid[:12]); row=dict(base); row['fresh']=fresh; row['head_to_head']={}; rows.append(row)
    return rows

def league_head_to_head(state:dict,g:int,rows:list[dict]):
    run_sh=ROOT/AGENT/'run.sh'
    for row in rows:
        gid=row['genome_id']; cw=wrapper(run_sh,load_genome(gid),TMP/f'g{g:03d}'/'league'/f'{gid[:12]}-candidate.sh')
        for member in list(state.get('league',[])):
            mid=member.get('genome_id')
            if not mid or mid==gid or not (GENOMES/f'{mid}.json').exists(): continue
            mw=wrapper(run_sh,load_genome(mid),TMP/f'g{g:03d}'/'league'/f'{mid[:12]}-member.sh'); st=allocate(state,'promotion',1,f'g{g:03d}-league-{gid[:8]}-{mid[:8]}')
            row['head_to_head'][mid]=ev.paired(cw,mw,st,1,TMP/f'g{g:03d}'/'league'/f'{gid[:8]}-v-{mid[:8]}')

def save_unique(child:dict,meta:dict,known:set[str],rng:random.Random)->str:
    for _ in range(60):
        gid=genome_id(child)
        if gid not in known:
            save_genome(GENOMES/f'{gid}.json',child,meta); known.add(gid); return gid
        child=graph_rewrite(child,rng,.35)
    raise RuntimeError('unable to save unique Cambrian child')

def breed_next(state:dict,g:int,by_island:dict[str,list[dict]],island_elites:list[dict],reset_islands:set[str],extinction:bool,temperature:float)->tuple[list[str],dict[str,int],list[Path]]:
    rng=random.Random(5500000+g); elite_map={island_of(state,r['genome_id']):r['genome_id'] for r in island_elites}; known=set(state.get('tested_genomes',{}))|set(state.get('current_population',[]))|set(x.get('genome_id') for x in state.get('league',[]))|archive_ids(state)
    mix=PLATEAU_MIX if state.get('plateau_counter',0)>=3 else NORMAL_MIX; counts={k:0 for k in (*mix,'migration')}; created=[]; all_next=[]
    for island in ISLANDS:
        elite=elite_map[island]; pool=[r['genome_id'] for r in by_island[island][:3]] or [elite]; nxt=[elite]
        for slot in range(1,8):
            if island in reset_islands:
                kind='immigrant' if slot<=4 else 'graph' if slot<=6 else 'bundle'
            elif extinction:
                kind='immigrant' if slot<=5 else ('graph' if slot==6 else 'bundle')
            elif g%3==0 and slot==1 and island in ('Adaptive','Wildcard'):
                kind='migration'
            else: kind=choose_kind(rng,mix)
            parent_id=rng.choice(pool); parent=load_genome(parent_id); child=None; meta={'generation':g+1,'island':island,'kind':kind,'parent':parent_id,'temperature':temperature}
            if kind=='micro': child=micro_mutation(parent,rng,temperature)
            elif kind=='module': child=module_mutation(parent,rng)
            elif kind=='graph': child=graph_rewrite(parent,rng,min(.40,.25+.05*temperature))
            elif kind=='bundle': child=strategy_bundle(parent,rng)
            elif kind=='immigrant': child=random_immigrant(parent['params'],rng,island); meta['parent']=None
            elif kind in ('crossover','migration'):
                if kind=='migration':
                    others=[x for k,x in elite_map.items() if k!=island]; other=rng.choice(others)
                else: other=rng.choice(pool)
                if other==parent_id:
                    others=[x for x in elite_map.values() if x!=parent_id]; other=rng.choice(others) if others else parent_id
                child=crossover_genomes(parent,load_genome(other),rng); meta['parents']=[parent_id,other]
            else: raise RuntimeError(kind)
            gid=save_unique(child,meta,known,rng); counts[kind]+=1; created.append(GENOMES/f'{gid}.json'); nxt.append(gid)
        state['islands'][island]['population']=nxt; state['islands'][island]['elite']=elite; state['islands'][island]['lineages']=len(set(load_genome_file(GENOMES/f'{x}.json')['meta'].get('parent',x) or x for x in nxt)); all_next.extend(nxt)
    if len(all_next)!=64 or len(set(all_next))!=64: raise RuntimeError('Cambrian next population size/diversity failure')
    state['current_population']=all_next; return all_next,counts,created

def update_tested(state:dict,g:int,rows1:list[dict],rows2:list[dict],next_ids:set[str]):
    s2={r['genome_id']:r for r in rows2}; league={x.get('genome_id') for x in state.get('league',[])}; archived=archive_ids(state); tested=state.setdefault('tested_genomes',{}); dead=state.setdefault('dead_genomes',{})
    for r in rows1:
        gid=r['genome_id']; rec=tested.setdefault(gid,{'first_generation':g,'tests':0}); rec['last_generation']=g; rec['tests']=int(rec.get('tests',0))+1; rec['stage1_score']=float(r['fitness']['aggregate'])
        if gid in s2: rec['stage2_score']=float(s2[gid]['fitness']['aggregate'])
        rec['status']='active' if gid in next_ids or gid in league or gid in archived else 'dead'
        if rec['status']=='dead': dead[gid]={'generation':g,'last_score':float((s2.get(gid) or r)['fitness']['aggregate'])}

def checkpoint(state:dict,g:int,best:dict,league_changes:list[dict])->list[Path]:
    if g%5!=0 and not league_changes: return []
    gid=best['genome_id']; z=CHECKPOINTS/f'evolution5_g{g:03d}_{gid[:12]}_submission.zip'; info=freeze_submission(load_genome(gid),ROOT,z)
    manifest=CHECKPOINTS/f'evolution5_g{g:03d}_{gid[:12]}.json'; dump(manifest,{'generation':g,'genome_id':gid,'fresh':best.get('fresh'),'league_changes':league_changes,'archive_occupancy':len(state.get('map_elites',{})),'league':state.get('league',[]),'submission':info,'state_hash':state_hash(state)})
    return [z,manifest]

def transaction(state:dict,txid:str):
    stop_check(); g=int(state['generation'])+1; shutil.rmtree(TMP/f'g{g:03d}',ignore_errors=True); ev.build(ROOT); opps=ev.resolve_opponents()
    # Stage 1: 64 organisms x 4 opponents x 1 paired seed = 8 games/organism.
    s1op=rotate(opps,g,4,0); rows1=parallel_stage(state,g,list(state['current_population']),s1op,'training',1,'stage1'); survivors=stage1_survivors(state,rows1)
    # Stage 2: 24 survivors x 5 opponents x 3 paired seeds = 30 games/organism.
    s2op=rotate(opps,g,5,2); rows2=parallel_stage(state,g,survivors,s2op,'evaluation',3,'stage2'); elites,by_island=stage2_elites(state,rows2)
    stage3_base=sorted(elites,key=rank_key,reverse=True)[:4]; rows3=fresh_stage(state,g,stage3_base,opps); league_head_to_head(state,g,rows3)
    archive_changes=update_archive(state,rows2,load_genome,g); league_changes=consider_league(state,rows3,load_genome,g)
    fresh_best=max(rows3,key=lambda r:(float(r['fresh']['fitness']['aggregate']),float(r['fresh']['fitness']['minimum']))); fresh_score=float(fresh_best['fresh']['fitness']['aggregate']); fresh_win=float(fresh_best['fresh']['aggregate']['raw_win_rate'])
    previous=float(state.get('best_fresh_score',0)); improved=fresh_score>previous+.01
    if improved:
        state['best_fresh_score']=fresh_score; state['best_fresh_win_rate']=fresh_win; state['best_fresh_genome_id']=fresh_best['genome_id']; state['plateau_counter']=0
    else: state['plateau_counter']=int(state.get('plateau_counter',0))+1
    state['generations_since_league_change']=0 if league_changes else int(state.get('generations_since_league_change',0))+1
    plateau=int(state['plateau_counter']); temperature=min(2.5,1.0+.15*plateau); state['mutation_temperature']=temperature
    island_scores={name:float(by_island[name][0]['fitness']['aggregate']) for name in ISLANDS}; reset=set()
    if plateau>=8: reset=set(sorted(ISLANDS,key=lambda n:island_scores[n])[:2])
    extinction=plateau>=10 or int(state['generations_since_league_change'])>=10
    next_ids,mutation_counts,created=breed_next(state,g,by_island,elites,reset,extinction,temperature)
    if extinction:
        state.setdefault('extinction_history',[]).append({'generation':g,'reason':'plateau' if plateau>=10 else 'league_stagnation','replaced_non_elite_fraction':7/8,'preserved_league':len(state.get('league',[])),'preserved_archive':len(state.get('map_elites',{}))}); state['plateau_counter']=0; state['generations_since_league_change']=0
    update_tested(state,g,rows1,rows2,set(next_ids))
    evidence=state.setdefault('target_evidence',[])
    if fresh_win>=.75 and float(fresh_best['fresh']['fitness']['minimum'])>=.50 and int(fresh_best['fresh']['aggregate'].get('games',0))>=40:
        evidence.append({'generation':g,'genome_id':fresh_best['genome_id'],'fresh_win_rate':fresh_win,'fresh_score':fresh_score,'minimum':fresh_best['fresh']['fitness']['minimum'],'games':fresh_best['fresh']['aggregate']['games']})
    report={
      'generation':g,'stage1_games_per_genome':8,'stage2_games_per_genome':30,'fresh_games_per_candidate':int(fresh_best['fresh']['aggregate']['games']),
      'stage1_best':max(float(r['fitness']['aggregate']) for r in rows1),'stage1_median':sorted(float(r['fitness']['aggregate']) for r in rows1)[len(rows1)//2],
      'stage2_best':max(float(r['fitness']['aggregate']) for r in rows2),'stage2_median':sorted(float(r['fitness']['aggregate']) for r in rows2)[len(rows2)//2],
      'fresh_best_genome_id':fresh_best['genome_id'],'fresh_best_score':fresh_score,'fresh_best_win_rate':fresh_win,'fresh_best_minimum':fresh_best['fresh']['fitness']['minimum'],
      'island_best_scores':island_scores,'league_size':len(state.get('league',[])),'league_changes':league_changes,'archive_occupancy':len(state.get('map_elites',{})),'archive_changes':archive_changes,
      'plateau_counter_before_extinction_reset':plateau,'mutation_temperature':temperature,'mutation_counts':mutation_counts,'reset_islands':sorted(reset),'extinction':extinction,'independent_lineages':sum(int(state['islands'][n].get('lineages',0)) for n in ISLANDS),
      'errors':sum(int(r['stage1']['aggregate'].get('errors',0)) for r in rows1),'illegal_actions':sum(int(r['stage1']['aggregate'].get('illegal_actions',0)) for r in rows1),
    }
    state['generation']=g; state['phase']='evolving'; state['retry_count']=0; state['last_error']=None; state['last_successful_transaction_id']=txid; state.setdefault('generation_history',[]).append(report)
    for name in ISLANDS: state['islands'][name]['best_score']=island_scores[name]
    report_path=RESULTS/f'g{g:03d}'/'report.json'; dump(report_path,report); checkpoint_paths=checkpoint(state,g,fresh_best,league_changes)
    state['last_successful_state_hash']=state_hash(state); dump(STATE,state); h=json.loads(HEART.read_text()); h.update({'completion_time':now(),'result':'success','resulting_state_hash':state_hash(state)}); dump(HEART,h)
    persist([STATE,HEART,report_path,*created,*checkpoint_paths],f'evolution5: complete Cambrian generation {g}')
    return report

def main():
    bootstrap,paths=ensure_bootstrap()
    if paths: persist(paths,'evolution5: bootstrap 8-island Cambrian population')
    state=load_state(); stop_check(); txid=str(uuid.uuid4()); expected=int(state['generation'])+1
    dump(HEART,{'transaction_id':txid,'workflow_run_id':os.getenv('GITHUB_RUN_ID'),'start_time':now(),'expected_generation':expected,'completion_time':None,'result':'in_progress','resulting_state_hash':None}); persist([HEART],f'evolution5: heartbeat start {txid[:8]}')
    try:
        report=transaction(state,txid); print('[evolution5] COMPLETE '+json.dumps(report,sort_keys=True),flush=True)
    except StopIteration:
        raise
    except Exception as exc:
        s=load_state(); s['retry_count']=int(s.get('retry_count',0))+1; s['last_error']=repr(exc); dump(STATE,s)
        h=json.loads(HEART.read_text()); h.update({'completion_time':now(),'result':'failed','resulting_state_hash':state_hash(s),'error':repr(exc)}); dump(HEART,h); persist([STATE,HEART],f'evolution5: transaction failed retry {s["retry_count"]}')
        raise

if __name__=='__main__': main()
