from __future__ import annotations
import hashlib, itertools, json, os, random, shutil, subprocess, sys, tempfile, time, uuid, zipfile
from datetime import datetime, timezone
from pathlib import Path
from .genome import founder_x0, founder_y0, save_genome, load_genome, genome_id, env_for, canonical_values
from .mutate import mutate
from .crossover import crossover
from .selection import select
from .diversity import genome_distance
from .telemetry import aggregate as telemetry_aggregate, suggested_chromosome
from .evaluator import ROOT, AGENT, worktree, build, wrapper, plain_wrapper, resolve_opponents, paired, combine, color_imbalance, run
from .freeze import freeze_header, inline_for_submission

CONTROL='evolution4/control'; TEMPLATE='evolution4/template'; CHAMPION='evolution4/champion'
XBR='evolution4/founder-x0'; YBR='evolution4/founder-y0'
X0='2260b6f19d51a14d7c68770677f22d04dfd88022'; Y0='687165839cea8ae5e84da26c99af1c0e5aed4543'
E4=ROOT/'evolution4'; STATE=E4/'state.json'; HEART=E4/'heartbeat.json'; STOP=E4/'STOP'; GENOMES=E4/'genomes'; RESULTS=E4/'results'; CHECKPOINTS=E4/'checkpoints'; FINAL=E4/'final'
RUNTIME=('main.cpp','core.hpp','build.sh','run.sh')

def now(): return datetime.now(timezone.utc).isoformat()
def load_state(): return json.loads(STATE.read_text())
def dump(path:Path,obj): path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n')
def state_digest(s): return hashlib.sha256(json.dumps(s,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def sha256_file(p:Path): return hashlib.sha256(p.read_bytes()).hexdigest()
def runtime_hashes(tree:Path): return {f:sha256_file(tree/AGENT/f) for f in RUNTIME}
def git(*args,check=True,capture=False,cwd=ROOT): return run(['git',*args],cwd=cwd,check=check,capture=capture)
def remote_sha(branch):
    git('fetch','--no-tags','origin',branch)
    return git('rev-parse',f'origin/{branch}',capture=True).stdout.strip()
def stop_check(where=''):
    git('fetch','--no-tags','origin',CONTROL)
    p=git('cat-file','-e',f'origin/{CONTROL}:evolution4/STOP',check=False,capture=True)
    if p.returncode==0: raise StopIteration(f'evolution4/STOP present {where}')
def persist(paths:list[Path],message:str):
    git('add',*[str(p) for p in paths])
    if git('diff','--cached','--quiet',check=False).returncode==0: return
    git('commit','-m',message); git('push','origin',f'HEAD:{CONTROL}')
def verify_remote(expected_phase:str,expected_generation:int,txid:str|None):
    git('fetch','--no-tags','origin',CONTROL)
    raw=git('show',f'origin/{CONTROL}:evolution4/state.json',capture=True).stdout
    r=json.loads(raw)
    if r.get('phase')!=expected_phase or int(r.get('generation',-1))!=expected_generation: raise RuntimeError(f'remote durable state mismatch phase/gen: {r.get("phase")}/{r.get("generation")}')
    if txid and r.get('last_successful_transaction_id')!=txid: raise RuntimeError('remote durable transaction id mismatch')
    return r

def heartbeat_start(s,txid):
    h={'transaction_id':txid,'workflow_run_id':os.getenv('GITHUB_RUN_ID'),'start_time':now(),'expected_phase':s['phase'],'expected_generation':s['generation'],'completion_time':None,'resulting_state_hash':None,'result':'in_progress'}
    dump(HEART,h); persist([HEART],f'evolution4: heartbeat start {txid[:8]}')
def heartbeat_finish(s,txid,result):
    h=json.loads(HEART.read_text()); h.update({'completion_time':now(),'resulting_state_hash':state_digest(s),'result':result}); dump(HEART,h)

def allocate(s,count,label):
    start=int(s['seed_ledger']['next_seed']); s['seed_ledger']['next_seed']=start+count+17
    s['seed_ledger'].setdefault('ranges',[]).append({'label':label,'start':start,'maps':count})
    return start

def genome_path(gid): return GENOMES/f'{gid}.json'
def genome_values(gid): return load_genome(genome_path(gid))['values']
def save_unique(values,meta,known:set[str]):
    for _ in range(30):
        gid=genome_id(values)
        if gid not in known:
            save_genome(genome_path(gid),values,meta); known.add(gid); return gid
        values=mutate(values,random.Random(int(gid[:12],16)^len(known)),False)
    raise RuntimeError('could not generate unique genome')

def ensure_template():
    git('fetch','--no-tags','origin',TEMPLATE)
    t=worktree(f'origin/{TEMPLATE}',Path('/tmp/e4-template'))
    main=t/AGENT/'main.cpp'; hdr=t/AGENT/'evolution4_genome.hpp'
    if not hdr.exists() or '#include "evolution4_genome.hpp"' not in main.read_text():
        run(['python','-m','tools.evolution4.template_transform',str(main)])
        build(t)
        test=t/AGENT/'test.sh'
        if test.exists(): run(['bash',str(test)],cwd=t)
        git('add',str(AGENT/'main.cpp'),str(AGENT/'evolution4_genome.hpp'),cwd=t)
        if git('diff','--cached','--quiet',cwd=t,check=False).returncode:
            git('commit','-m','evolution4: refactor X0 into genome-capable template',cwd=t)
            git('push','origin',f'HEAD:{TEMPLATE}',cwd=t)
    build(t); return t

def y_env_json(): return json.dumps(env_for(founder_y0()),sort_keys=True)

def equivalence(founder:Path,template:Path,env_json='{}',seeds=12):
    run(['python','-m','tools.evolution4.equivalence_check','--original',str(founder/AGENT/'run.sh'),'--template',str(template/AGENT/'run.sh'),'--env-json',env_json,'--seeds',str(seeds)])

def founder_worktrees():
    git('fetch','--no-tags','origin',XBR,YBR)
    x=worktree(f'origin/{XBR}',Path('/tmp/e4-x0')); y=worktree(f'origin/{YBR}',Path('/tmp/e4-y0'))
    if git('rev-parse','HEAD',cwd=x,capture=True).stdout.strip()!=X0: raise RuntimeError('X0 founder branch moved')
    if git('rev-parse','HEAD',cwd=y,capture=True).stdout.strip()!=Y0: raise RuntimeError('Y0 founder branch moved')
    build(x); build(y); return x,y

def initial_population(xgid,ygid):
    rng=random.Random(404004); known={xgid,ygid}; ids=[xgid,ygid]; x=founder_x0(); y=founder_y0()
    for i in range(6): ids.append(save_unique(mutate(x,rng,False),{'origin':'x0-local','index':i},known))
    for i in range(4): ids.append(save_unique(mutate(y,rng,False),{'origin':'y0-local','index':i},known))
    for i in range(4):
        child=crossover(x,y,rng); child=mutate(child,rng,False)
        ids.append(save_unique(child,{'origin':'x0-y0-crossover','index':i},known))
    if len(ids)!=16 or len(set(ids))!=16: raise RuntimeError('initial population size/diversity failure')
    return ids

def eval_genome(values,template_run:Path,opps:list[dict],starts:dict[str,int],seeds:int,out:Path):
    wr=wrapper(template_run,values,out/'candidate.sh'); summaries={}
    for o in opps:
        summaries[o['archetype']]=paired(wr,Path(o['run']),starts[o['archetype']],seeds,out/o['archetype'])
    agg=combine(list(summaries.values())); arch={k:float(v['score']) for k,v in summaries.items()}
    fit={'aggregate':agg['score'],'minimum':min(arch.values()) if arch else 0.0,'hof':0.0,'color_imbalance':sum(color_imbalance(v) for v in summaries.values())/max(1,len(summaries))}
    return {'summaries':summaries,'archetypes':arch,'aggregate':agg,'fitness':fit}

def baseline_bootstrap(s,x,y,t,opps):
    out=E4/'baseline'; shutil.rmtree(out,ignore_errors=True); out.mkdir(parents=True,exist_ok=True)
    xw=plain_wrapper(x/AGENT/'run.sh',out/'x0.sh'); yw=plain_wrapper(y/AGENT/'run.sh',out/'y0.sh')
    hstart=allocate(s,5,'bootstrap-x0-y0'); hv=paired(xw,yw,hstart,5,out/'x0-v-y0')
    reps=[]
    reps_opps=[]
    wanted=[]
    for key in ('aggressive-expansion','defense-turtle','doomer-rusher','recent-reference'):
        q=next((o for o in opps if o['archetype']==key),None)
        if q: wanted.append(q)
    for o in wanted:
        st=allocate(s,3,f'bootstrap-{o["archetype"]}')
        xs=paired(xw,Path(o['run']),st,3,out/'x0'/o['archetype']); ys=paired(yw,Path(o['run']),st,3,out/'y0'/o['archetype'])
        reps.append({'archetype':o['archetype'],'x0':xs,'y0':ys}); reps_opps.append({'archetype':o['archetype'],'ref':o['ref'],'sha':o['sha']})
    report={'x0_v_y0':hv,'representative_suite':reps,'opponents':reps_opps}; dump(out/'report.json',report); return report

def bootstrap(s,txid):
    # Verify old system is definitely dead.
    if git('cat-file','-e','origin/evolution3/control:evolution3/STOP',check=False).returncode: raise RuntimeError('evolution3 STOP missing')
    if git('cat-file','-e','origin/master:.github/workflows/evolution3-elitist.yml',check=False).returncode==0: raise RuntimeError('evolution3 workflow still present')
    x,y=founder_worktrees(); t=ensure_template(); equivalence(x,t,'{}',12); equivalence(y,t,y_env_json(),12)
    # Fresh game-level smoke with actual engine.
    run(['python','competition/matchup.py',str(t/AGENT/'run.sh'),str(x/AGENT/'run.sh'),'--mode','competition','--seed','399901'])
    yw=wrapper(t/AGENT/'run.sh',founder_y0(),Path('/tmp/e4-y-smoke.sh')); run(['python','competition/matchup.py',str(yw),str(y/AGENT/'run.sh'),'--mode','competition','--seed','399902'])
    opps=resolve_opponents(); manifest=[{k:o[k] for k in ('archetype','ref','sha')} for o in opps]; dump(E4/'opponent_suite.json',manifest)
    xgid=save_genome(GENOMES/'founder-x0.json',founder_x0(),{'founder':'X0','gameplay_sha':X0}); ygid=save_genome(GENOMES/'founder-y0.json',founder_y0(),{'founder':'Y0','gameplay_sha':Y0})
    # Canonical id-named copies are the durable population objects.
    save_genome(genome_path(xgid),founder_x0(),{'founder':'X0','gameplay_sha':X0}); save_genome(genome_path(ygid),founder_y0(),{'founder':'Y0','gameplay_sha':Y0})
    pop=initial_population(xgid,ygid); base=baseline_bootstrap(s,x,y,t,opps)
    xh=runtime_hashes(x); yh=runtime_hashes(y)
    s.update({'phase':'exploration','generation':0,'current_population':pop,'breeding_elites':[xgid,ygid],
      'official_champion_genome_id':xgid,'official_champion_commit_sha':X0,'official_champion_runtime_hashes':xh,
      'founder_x0':{'gameplay_sha':X0,'branch':XBR,'runtime_hashes':xh,'genome_id':xgid},'founder_y0':{'gameplay_sha':Y0,'branch':YBR,'runtime_hashes':yh,'genome_id':ygid},
      'hall_of_fame':[{'label':'X0','genome_id':xgid,'commit_sha':X0,'runtime_hashes':xh},{'label':'Y0','genome_id':ygid,'commit_sha':Y0,'runtime_hashes':yh}],
      'baseline':base,'opponent_suite':manifest,'retry_count':0,'last_error':None,'last_successful_transaction_id':txid})
    s['last_successful_state_hash']=state_digest(s); dump(STATE,s); heartbeat_finish(s,txid,'success')
    persist([STATE,HEART,E4/'opponent_suite.json',E4/'baseline'/'report.json',*GENOMES.glob('*.json')],'evolution4: complete verified bootstrap')
    verify_remote('exploration',0,txid)

def stage_population(s,t,opps,ids,generation):
    template_run=t/AGENT/'run.sh'; rep_names=['aggressive-expansion','defense-turtle','doomer-rusher','recent-reference']; rep=[o for o in opps if o['archetype'] in rep_names]
    starts1={o['archetype']:allocate(s,3,f'g{generation:02d}-stage1-{o["archetype"]}') for o in rep}
    rows=[]
    for gid in ids:
        out=RESULTS/f'g{generation:02d}'/'stage1'/gid[:12]; ev=eval_genome(genome_values(gid),template_run,rep,starts1,3,out); rows.append({'genome_id':gid,'fitness':ev['fitness'],'stage1':ev})
    top8=select(rows,8)
    starts2={o['archetype']:allocate(s,5,f'g{generation:02d}-stage2-{o["archetype"]}') for o in opps}
    rows2=[]
    for r in top8:
        gid=r['genome_id']; out=RESULTS/f'g{generation:02d}'/'stage2'/gid[:12]; ev=eval_genome(genome_values(gid),template_run,opps,starts2,5,out); rows2.append({'genome_id':gid,'fitness':ev['fitness'],'stage1':r['stage1'],'stage2':ev})
    top4=select(rows2,4); return rows,rows2,top4

def gate_a(s,candidate:Path,champion:Path,g,label):
    st=allocate(s,10,f'{label}-gateA-r1'); q1=paired(candidate,champion,st,10,RESULTS/f'g{g:02d}'/'promotion'/'gateA-r1'); rounds=[q1]; cum=combine(rounds)
    if cum['score']<=.525: return {'rounds':rounds,'cumulative':cum,'decision':'reject'}
    if cum['score']>=.575 and cum['W']>cum['L']: return {'rounds':rounds,'cumulative':cum,'decision':'pass'}
    st2=allocate(s,10,f'{label}-gateA-r2'); q2=paired(candidate,champion,st2,10,RESULTS/f'g{g:02d}'/'promotion'/'gateA-r2'); rounds.append(q2); cum=combine(rounds)
    return {'rounds':rounds,'cumulative':cum,'decision':'pass' if cum['score']>=.55 and cum['W']>cum['L'] else 'reject'}

def gate_b(s,candidate,champion,opps,g,label):
    details=[]; parent=[]; cand=[]; bad=[]
    for o in opps:
        st=allocate(s,5,f'{label}-gateB-{o["archetype"]}'); ps=paired(champion,Path(o['run']),st,5,RESULTS/f'g{g:02d}'/'promotion'/'gateB'/o['archetype']/'parent'); cs=paired(candidate,Path(o['run']),st,5,RESULTS/f'g{g:02d}'/'promotion'/'gateB'/o['archetype']/'candidate')
        d=float(cs['score'])-float(ps['score']); rec={'archetype':o['archetype'],'parent':ps,'candidate':cs,'delta':d}; details.append(rec); parent.append(ps); cand.append(cs)
        if d < -.10: bad.append(rec)
    confirmed=[]
    for rec in bad:
        o=next(x for x in opps if x['archetype']==rec['archetype']); st=allocate(s,5,f'{label}-gateB-confirm-{o["archetype"]}'); ps=paired(champion,Path(o['run']),st,5,RESULTS/f'g{g:02d}'/'promotion'/'gateB-confirm'/o['archetype']/'parent'); cs=paired(candidate,Path(o['run']),st,5,RESULTS/f'g{g:02d}'/'promotion'/'gateB-confirm'/o['archetype']/'candidate'); delta=float(cs['score'])-float(ps['score']);
        if delta < -.10: confirmed.append({'archetype':o['archetype'],'delta':delta,'parent':ps,'candidate':cs})
    pa=combine(parent); ca=combine(cand); decision='pass' if ca['score']>=pa['score'] and not confirmed else 'reject'
    return {'details':details,'parent_aggregate':pa,'candidate_aggregate':ca,'confirmed_regressions':confirmed,'decision':decision}

def gate_anchor(s,candidate,anchor_run,g,label,name):
    rounds=[]; st=allocate(s,5,f'{label}-{name}-r1'); rounds.append(paired(candidate,anchor_run,st,5,RESULTS/f'g{g:02d}'/'promotion'/name/'r1')); cum=combine(rounds)
    if cum['score']<.45:
        st=allocate(s,5,f'{label}-{name}-r2'); rounds.append(paired(candidate,anchor_run,st,5,RESULTS/f'g{g:02d}'/'promotion'/name/'r2')); cum=combine(rounds)
    return {'rounds':rounds,'cumulative':cum,'decision':'pass' if cum['score']>=.45 else 'reject'}

def promotion_screen(s,proposal,t,opps,g):
    gid=proposal['genome_id']; label=f'g{g:02d}-{gid[:8]}'; cand=wrapper(t/AGENT/'run.sh',genome_values(gid),RESULTS/f'g{g:02d}'/'promotion'/'candidate.sh')
    ctree=worktree(f'origin/{CHAMPION}',Path('/tmp/e4-champion')); build(ctree); champ=plain_wrapper(ctree/AGENT/'run.sh',RESULTS/f'g{g:02d}'/'promotion'/'champion.sh')
    A=gate_a(s,cand,champ,g,label)
    if A['decision']!='pass': return False,{'genome_id':gid,'gateA':A,'decision':'REJECTED','reason':'Gate A'}
    B=gate_b(s,cand,champ,opps,g,label)
    if B['decision']!='pass': return False,{'genome_id':gid,'gateA':A,'gateB':B,'decision':'REJECTED','reason':'Gate B'}
    x,y=founder_worktrees(); Cx=gate_anchor(s,cand,plain_wrapper(x/AGENT/'run.sh',RESULTS/f'g{g:02d}'/'promotion'/'x0.sh'),g,label,'gateC-X0'); Cy=gate_anchor(s,cand,plain_wrapper(y/AGENT/'run.sh',RESULTS/f'g{g:02d}'/'promotion'/'y0.sh'),g,label,'gateC-Y0')
    if Cx['decision']!='pass' or Cy['decision']!='pass': return False,{'genome_id':gid,'gateA':A,'gateB':B,'gateC':{'X0':Cx,'Y0':Cy},'decision':'REJECTED','reason':'Gate C'}
    checks=[]
    historical=[]
    for h in reversed(s.get('hall_of_fame',[])):
        q=h.get('commit_sha')
        if q and q not in (s['official_champion_commit_sha'],X0,Y0) and q not in historical: historical.append(q)
        if len(historical)>=2: break
    for i,q in enumerate(historical):
        hp=worktree(q,Path(f'/tmp/e4-hof-{i}')); build(hp); qres=gate_anchor(s,cand,plain_wrapper(hp/AGENT/'run.sh',RESULTS/f'g{g:02d}'/'promotion'/f'hof{i}.sh'),g,label,f'gateD-{i}'); checks.append({'sha':q,'result':qres})
        if qres['decision']!='pass': return False,{'genome_id':gid,'gateA':A,'gateB':B,'gateC':{'X0':Cx,'Y0':Cy},'gateD':checks,'decision':'REJECTED','reason':'Gate D'}
    return True,{'genome_id':gid,'gateA':A,'gateB':B,'gateC':{'X0':Cx,'Y0':Cy},'gateD':checks,'decision':'ACCEPTED_PENDING'}

def promote(s,gid,t,evidence,g,txid):
    stop_check('before pending promotion'); old=s['official_champion_commit_sha']; s['pending_promotion']={'genome_id':gid,'parent_commit_sha':old,'generation':g,'evidence':evidence}; dump(STATE,s); p=RESULTS/f'g{g:02d}'/'promotion'/'evidence.json'; dump(p,evidence); persist([STATE,p],f'evolution4: pending promotion g{g:02d} {gid[:8]}')
    stop_check('before champion freeze')
    ctree=worktree(f'origin/{CHAMPION}',Path('/tmp/e4-promote')); vals=genome_values(gid)
    for f in RUNTIME: shutil.copy2(t/AGENT/f,ctree/AGENT/f)
    shutil.copy2(t/AGENT/'evolution4_genome.hpp',ctree/AGENT/'evolution4_genome.hpp'); freeze_header(t/AGENT/'evolution4_genome.hpp',vals,ctree/AGENT/'evolution4_genome.hpp')
    build(ctree); equivalence(ctree,t,json.dumps(env_for(vals)),8)
    stop_check('immediately before champion ref move')
    git('add',str(AGENT/'main.cpp'),str(AGENT/'core.hpp'),str(AGENT/'build.sh'),str(AGENT/'run.sh'),str(AGENT/'evolution4_genome.hpp'),cwd=ctree)
    git('commit','-m',f'evolution4: promote genome {gid[:12]} at generation {g}',cwd=ctree)
    git('push','origin',f'HEAD:{CHAMPION}',cwd=ctree); newsha=remote_sha(CHAMPION); h=runtime_hashes(ctree)
    s['official_champion_genome_id']=gid; s['official_champion_commit_sha']=newsha; s['official_champion_runtime_hashes']=h; s['pending_promotion']=None; s['champion_promotions_since_checkpoint']=int(s.get('champion_promotions_since_checkpoint',0))+1
    s.setdefault('champion_promotion_history',[]).append({'generation':g,'genome_id':gid,'parent_commit_sha':old,'commit_sha':newsha,'runtime_hashes':h,'evidence':evidence}); s.setdefault('hall_of_fame',[]).append({'label':f'g{g:02d}','genome_id':gid,'commit_sha':newsha,'runtime_hashes':h})
    return newsha

def next_population(top4,g):
    rng=random.Random(880000+g); elites=[x['genome_id'] for x in top4]; known=set(elites); out=list(elites); vals=[genome_values(x) for x in elites]
    worst=top4[0]['stage2']['archetypes']; bias=suggested_chromosome({},worst)
    def add(v,meta):
        gid=save_unique(v,meta,known); out.append(gid)
    for i in range(6):
        a,b=rng.sample(vals,2); child=crossover(a,b,rng); child=mutate(child,rng,False,bias if rng.random()<.7 else None); add(child,{'generation':g+1,'kind':'crossover','bias':bias})
    for i in range(4): add(mutate(rng.choice(vals),rng,False,bias),{'generation':g+1,'kind':'local','bias':bias})
    for i in range(2): add(mutate(rng.choice(vals),rng,True,None),{'generation':g+1,'kind':'exploratory'})
    if len(out)!=16: raise RuntimeError('next population size failure')
    return out,elites,bias

def package_tree(tree:Path,zip_path:Path):
    tmp=Path(tempfile.mkdtemp(prefix='e4-pkg-')); pkg=tmp/'juraj_v35'; pkg.mkdir();
    hdr=tree/AGENT/'evolution4_genome.hpp'; main=tree/AGENT/'main.cpp'
    if hdr.exists() and '#include "evolution4_genome.hpp"' in main.read_text(): inline_for_submission(main,hdr,pkg/'main.cpp')
    else: shutil.copy2(main,pkg/'main.cpp')
    for f in ('core.hpp','build.sh','run.sh'): shutil.copy2(tree/AGENT/f,pkg/f)
    zip_path.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED) as z:
        for f in RUNTIME: z.write(pkg/f,arcname=f'juraj_v35/{f}')
    clean=Path(tempfile.mkdtemp(prefix='e4-clean-'))
    with zipfile.ZipFile(zip_path) as z: z.extractall(clean)
    run(['bash',str(clean/'juraj_v35'/'build.sh')]); (clean/'juraj_v35'/'agent').unlink(missing_ok=True)
    return sha256_file(zip_path)

def checkpoint(s):
    g=int(s['generation']); gid=s['official_champion_genome_id']; ctree=worktree(f'origin/{CHAMPION}',Path('/tmp/e4-checkpoint')); build(ctree)
    z=CHECKPOINTS/f'evolution4_g{g:02d}_{gid[:12]}_submission.zip'; h=package_tree(ctree,z); (z.with_suffix('.sha256')).write_text(h+'  '+z.name+'\n')
    branch=f'submission/evolution4-g{g:02d}-{gid[:12]}'; git('push','origin',f'{s["official_champion_commit_sha"]}:refs/heads/{branch}',check=False)
    s['last_checkpoint_generation']=g; s['champion_promotions_since_checkpoint']=0; return [z,z.with_suffix('.sha256')]

def audit(s,opps,g):
    # Fresh robustness audit of current, previous champion and founders on common seeds.
    candidates=[]
    for h in [*reversed(s.get('hall_of_fame',[]))]:
        q=h.get('commit_sha')
        if q and q not in [x['commit_sha'] for x in candidates]: candidates.append(h)
        if len(candidates)>=4: break
    if not any(x.get('commit_sha')==X0 for x in candidates): candidates.append(next(x for x in s['hall_of_fame'] if x.get('commit_sha')==X0))
    if not any(x.get('commit_sha')==Y0 for x in candidates): candidates.append(next(x for x in s['hall_of_fame'] if x.get('commit_sha')==Y0))
    starts={o['archetype']:allocate(s,5,f'g{g:02d}-audit-{o["archetype"]}') for o in opps}; rows=[]
    for i,h in enumerate(candidates):
        tr=worktree(h['commit_sha'],Path(f'/tmp/e4-audit-{i}')); build(tr); wr=plain_wrapper(tr/AGENT/'run.sh',RESULTS/f'g{g:02d}'/'audit'/f'{i}.sh'); ss={}
        for o in opps: ss[o['archetype']]=paired(wr,Path(o['run']),starts[o['archetype']],5,RESULTS/f'g{g:02d}'/'audit'/f'{i}-{o["archetype"]}')
        ag=combine(list(ss.values())); rows.append({'entry':h,'aggregate':ag,'minimum':min(float(x['score']) for x in ss.values()),'scores':ss})
    rows.sort(key=lambda x:(x['aggregate']['score'],x['minimum'],x['aggregate']['W']),reverse=True); best=rows[0]; cur=next(x for x in rows if x['entry'].get('commit_sha')==s['official_champion_commit_sha'])
    rollback=None
    if best['entry']['commit_sha']!=cur['entry']['commit_sha'] and (cur['aggregate']['score']<best['aggregate']['score']-.04 or cur['minimum']<best['minimum']-.10):
        old=s['official_champion_commit_sha']; target=best['entry']; git('push','--force','origin',f'{target["commit_sha"]}:refs/heads/{CHAMPION}'); s['official_champion_commit_sha']=target['commit_sha']; s['official_champion_genome_id']=target['genome_id']; tr=worktree(target['commit_sha'],Path('/tmp/e4-rollback')); s['official_champion_runtime_hashes']=runtime_hashes(tr); rollback={'generation':g,'revoked':old,'restored':target['commit_sha'],'evidence':{'current':cur,'best':best}}; s.setdefault('rollback_history',[]).append(rollback)
    s['audit_count']=int(s.get('audit_count',0))+1; rep={'generation':g,'rows':rows,'rollback':rollback}; p=RESULTS/f'g{g:02d}'/'audit.json'; dump(p,rep); return p

def generation(s,txid):
    pre=int(s['generation']); g=pre+1; stop_check(f'generation {g}')
    t=ensure_template(); opps=resolve_opponents(); ids=list(s['current_population']); rows1,rows2,top4=stage_population(s,t,opps,ids,g)
    proposal=top4[0]; accepted,evidence=promotion_screen(s,proposal,t,opps,g); prom=None
    if accepted: prom=promote(s,proposal['genome_id'],t,evidence,g,txid)
    else: s.setdefault('rejected_promotions',[]).append({'generation':g,**evidence})
    nxt,elites,bias=next_population(top4,g); s['current_population']=nxt; s['breeding_elites']=elites; s['generation']=g
    if g>=30: s['phase']='final'
    elif g>=12: s['phase']='exploitation'
    else: s['phase']='exploration'
    report={'generation':g,'phase':s['phase'],'stage1':rows1,'stage2':rows2,'top4':[x['genome_id'] for x in top4],'mutation_bias':bias,'promotion':evidence,'promoted_commit':prom}; p=RESULTS/f'g{g:02d}'/'report.json'; dump(p,report); s.setdefault('generation_history',[]).append({'generation':g,'top4':[x['genome_id'] for x in top4],'promotion_decision':evidence['decision'],'official_champion_genome_id':s['official_champion_genome_id']})
    extra=[]
    if g%5==0: extra.append(audit(s,opps,g))
    if g==0 or g%5==0 or int(s.get('champion_promotions_since_checkpoint',0))>=3: extra.extend(checkpoint(s))
    s['retry_count']=0; s['last_error']=None; s['last_successful_transaction_id']=txid; s['last_successful_state_hash']=state_digest(s); dump(STATE,s); heartbeat_finish(s,txid,'success')
    persist([STATE,HEART,p,*extra,*[genome_path(x) for x in nxt]],f'evolution4: complete generation {g}')
    verify_remote(s['phase'],g,txid)
    if g!=pre+1: raise RuntimeError('false-green generation transition')

def final_run(s,txid):
    stop_check('final'); t=ensure_template(); opps=resolve_opponents(); entries=[]; seen=set()
    for h in s.get('hall_of_fame',[]):
        gid=h.get('genome_id');
        if gid and gid not in seen: entries.append({'genome_id':gid,'commit_sha':h.get('commit_sha'),'label':h.get('label','hof')}); seen.add(gid)
    for gid in s.get('breeding_elites',[]):
        if gid not in seen: entries.append({'genome_id':gid,'commit_sha':None,'label':'breeding'}); seen.add(gid)
    starts={o['archetype']:allocate(s,10,f'final-{o["archetype"]}') for o in opps}; rows=[]
    for i,e in enumerate(entries):
        if e['commit_sha']:
            tr=worktree(e['commit_sha'],Path(f'/tmp/e4-final-ref-{i}')); build(tr); wr=plain_wrapper(tr/AGENT/'run.sh',FINAL/f'ref-{i}.sh')
        else: wr=wrapper(t/AGENT/'run.sh',genome_values(e['genome_id']),FINAL/f'genome-{i}.sh')
        ss={}
        for o in opps: ss[o['archetype']]=paired(wr,Path(o['run']),starts[o['archetype']],10,FINAL/'suite'/f'{i}-{o["archetype"]}')
        ag=combine(list(ss.values())); rows.append({'entry':e,'aggregate':ag,'minimum':min(float(x['score']) for x in ss.values()),'scores':ss,'run':str(wr)})
    rows.sort(key=lambda x:(x['aggregate']['score'],x['minimum'],x['aggregate']['W']),reverse=True); top=rows[:4]; mutual=[]
    for a,b in itertools.combinations(top,2):
        st=allocate(s,10,f'final-mutual-{a["entry"]["genome_id"][:6]}-{b["entry"]["genome_id"][:6]}'); q=paired(Path(a['run']),Path(b['run']),st,10,FINAL/'mutual'/f'{a["entry"]["genome_id"][:8]}-{b["entry"]["genome_id"][:8]}'); mutual.append({'a':a['entry'],'b':b['entry'],'summary':q})
    winner=rows[0]['entry'];
    if winner['commit_sha']:
        wtree=worktree(winner['commit_sha'],Path('/tmp/e4-final-winner'))
    else:
        wtree=Path('/tmp/e4-final-genome'); shutil.rmtree(wtree,ignore_errors=True); shutil.copytree(t,wtree,symlinks=True,ignore=shutil.ignore_patterns('.git')); freeze_header(t/AGENT/'evolution4_genome.hpp',genome_values(winner['genome_id']),wtree/AGENT/'evolution4_genome.hpp'); build(wtree); equivalence(wtree,t,json.dumps(env_for(genome_values(winner['genome_id']))),8)
    z=FINAL/'generals_evolution4_submission.zip'; h=package_tree(wtree,z); (FINAL/'generals_evolution4_submission.sha256').write_text(h+'  '+z.name+'\n'); report={'winner':winner,'suite':rows,'mutual':mutual,'sha256':h}; dump(FINAL/'VALIDATION.json',report)
    s['phase']='done'; s['final_winner']=winner; s['retry_count']=0; s['last_error']=None; s['last_successful_transaction_id']=txid; s['last_successful_state_hash']=state_digest(s); dump(STATE,s); heartbeat_finish(s,txid,'success'); persist([STATE,HEART,FINAL/'VALIDATION.json',z,FINAL/'generals_evolution4_submission.sha256'],'evolution4: final unseen tournament and submission'); verify_remote('done',s['generation'],txid)

def fail(s,txid,exc):
    try:
        s=load_state()
    except Exception: pass
    s['retry_count']=int(s.get('retry_count',0))+1; s['last_error']=repr(exc)
    if s['retry_count']>=3:
        STOP.write_text(f'STOPPED {now()}\nThree consecutive infrastructure failures.\nLast error: {exc!r}\n'); s['phase']='stopped'
    dump(STATE,s); heartbeat_finish(s,txid,'failure'); paths=[STATE,HEART]+([STOP] if STOP.exists() else []); persist(paths,f'evolution4: infrastructure failure {s["retry_count"]}')

def main():
    os.chdir(ROOT); git('config','user.name','ChatGPT'); git('config','user.email','actions@users.noreply.github.com')
    s=load_state(); txid=str(uuid.uuid4()); heartbeat_start(s,txid)
    try:
        stop_check('at transaction start')
        if s['phase']=='bootstrap': bootstrap(s,txid)
        elif s['phase'] in ('exploration','exploitation'): generation(s,txid)
        elif s['phase']=='final': final_run(s,txid)
        elif s['phase']=='done': heartbeat_finish(s,txid,'done'); persist([HEART],f'evolution4: done heartbeat {txid[:8]}')
        elif s['phase']=='stopped': raise StopIteration('state stopped')
        else: raise RuntimeError(f'bad phase {s["phase"]}')
        return 0
    except StopIteration as e:
        print(e); return 0
    except Exception as e:
        print('EVOLUTION4 INFRASTRUCTURE FAILURE:',repr(e),file=sys.stderr); fail(s,txid,e); return 2
if __name__=='__main__': raise SystemExit(main())
