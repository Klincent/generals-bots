#!/usr/bin/env python3
import json, os, random, re, shlex, shutil, statistics, subprocess, sys, zipfile, hashlib
from pathlib import Path

ROOT=Path.cwd(); STATE=ROOT/'evolution2/state.json'; RESULTS=ROOT/'evolution2/results'; BASE=ROOT/'evolution2/baseline'; FINAL=ROOT/'evolution2/final'; STOP=ROOT/'evolution2/STOP'
AGENT=Path('competition/agents/juraj_v35_cpp'); BENCH=ROOT/AGENT/'paired_benchmark.py'
X0='2260b6f19d51a14d7c68770677f22d04dfd88022'; Y0='687165839cea8ae5e84da26c99af1c0e5aed4543'
XBR='evolution2/version-x'; YBR='evolution2/version-y'; CONTROL='evolution2/control'
OPPS=[
 ('defense-turtle',['v35-defense-fresh','v35-logistics-conservative']),
 ('economy-consolidator',['v35-iterative-1to6','v35-heuristic-rebuild']),
 ('logistics-recenter',['v35-logistics-recenter','v35-logistics-conservative']),
 ('attack-pass',['juraj-v3.6-iter1-attack-pass']),
 ('search-hunter',['juraj-v3.6-search-refactor','juraj-v35-e50123-selective']),
 ('expander',['juraj-v3.6-expansion-cycle-hardening']),
 ('doomer-rusher',['chatgpt/picker9-doomguard-rusher']),
 ('picker-muster',['chatgpt/picker-v9-muster-castle']),
 ('heuristic-reference',['v35-heuristic-rebuild','v35-castle-recapture'])]
CORE={x[0] for x in OPPS[:8]}

def run(cmd,cwd=ROOT,check=True,capture=False):
    p=subprocess.run(cmd if not isinstance(cmd,str) else cmd,cwd=cwd,shell=isinstance(cmd,str),text=True,capture_output=capture)
    if check and p.returncode:
        if capture: print(p.stdout,file=sys.stderr); print(p.stderr,file=sys.stderr)
        raise RuntimeError(f'command failed ({p.returncode}): {cmd}')
    return p

def git(*a,cwd=ROOT,check=True,capture=False): return run(['git',*a],cwd,check,capture)
def load(p=STATE): return json.loads(Path(p).read_text())
def dump(p,o): p=Path(p); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(o,indent=2,sort_keys=True)+'\n')
def fetch_all(): run("git fetch --no-tags origin '+refs/heads/*:refs/remotes/origin/*'")
def wsha(p): return git('rev-parse','HEAD',cwd=p,capture=True).stdout.strip()
def remote(branch): fetch_all(); return git('rev-parse',f'origin/{branch}',capture=True).stdout.strip()
def wt(ref,path):
    path=Path(path); run(['git','worktree','remove','--force',str(path)],check=False); shutil.rmtree(path,ignore_errors=True); git('worktree','add','--detach',str(path),ref); return path

def build(p): run(['bash',str(p/AGENT/'test.sh')],cwd=p); run(['bash',str(p/AGENT/'build.sh')],cwd=p)
def wrapper(runsh,label,dest):
    dest=Path(dest); dest.parent.mkdir(parents=True,exist_ok=True); dest.write_text('#!/usr/bin/env bash\nset -euo pipefail\n'+f"bash {shlex.quote(str(Path(runsh).resolve()))} 2> >(sed -u 's/^/[{label}] /' >&2)\n"); dest.chmod(0o755); return dest

def live(where):
    fetch_all()
    if STOP.exists() or git('cat-file','-e',f'origin/{CONTROL}:evolution2/STOP',check=False).returncode==0: raise StopIteration(f'STOP at {where}')

def fresh(s,maps,purpose):
    used=[(int(x['start']),int(x['maps'])) for x in s.get('used_seed_ranges',[])]
    rr=random.SystemRandom()
    for _ in range(5000):
        a=rr.randrange(100000,1999990000); b=a+maps-1
        if all(b<u-100 or a>u+m+100 for u,m in used):
            s.setdefault('used_seed_ranges',[]).append({'start':a,'maps':maps,'purpose':purpose}); return a
    raise RuntimeError('no fresh seed range')

def bench(cand,base,start,maps,out):
    out=Path(out); shutil.rmtree(out,ignore_errors=True); out.mkdir(parents=True,exist_ok=True)
    p=run([sys.executable,str(BENCH),'--candidate',str(cand),'--baseline',str(base),'--start',str(start),'--seeds',str(maps),'--output',str(out)],check=False,capture=True)
    sp=out/'summary.json'
    if not sp.exists(): raise RuntimeError('benchmark produced no summary: '+p.stderr[-3000:])
    z=load(sp); z['returncode']=p.returncode
    if p.returncode or z.get('errors',0) or z.get('illegal_actions',0): raise RuntimeError(f'invalid benchmark {z}')
    return z

def combine(rows):
    W=sum(x['W'] for x in rows); D=sum(x['D'] for x in rows); L=sum(x['L'] for x in rows); g=W+D+L
    return {'W':W,'D':D,'L':L,'games':g,'score':(W+.5*D)/max(1,g),'raw_win_rate':W/max(1,g),'errors':sum(x.get('errors',0) for x in rows),'illegal_actions':sum(x.get('illegal_actions',0) for x in rows)}

def parse_metrics(games,label,loss_pred):
    p=Path(games); ss=[]; pref=f'[{label}] '
    if not p.exists(): return {'loss_samples':0}
    for line in p.read_text().splitlines():
        if not line.strip(): continue
        g=json.loads(line)
        if not loss_pred(g): continue
        q={'turns':g.get('turns',0)}
        for l in g.get('stderr','').splitlines():
            if not l.startswith(pref): continue
            z=l[len(pref):]
            if z.startswith('[v35_land]'): q['land']={int(a):int(b) for a,b in re.findall(r'(\d+):(-?\d+)',z)}
            elif z.startswith('[v35_actions]'): q['actions']={a:float(b) for a,b in re.findall(r'(\w+)=(-?\d+(?:\.\d+)?)',z)}
            elif z.startswith('[v35_pass]'): q['pass']={a:float(b) for a,b in re.findall(r'(\w+)=(-?\d+(?:\.\d+)?)',z)}
            elif z.startswith('[v36_picker]'): q['picker']={a:float(b) for a,b in re.findall(r'(\w+)=(-?\d+(?:\.\d+)?)',z)}
            elif z.startswith('[v36_muster]'): q['muster']={a:float(b) for a,b in re.findall(r'(\w+)=(-?\d+(?:\.\d+)?)',z)}
            elif z.startswith('[v35_doomguard]'): q['doom']={a:float(b) for a,b in re.findall(r'(\w+)=(-?\d+(?:\.\d+)?)',z)}
            elif z.startswith('[v35_threat]'): q['threat']={a:float(b) for a,b in re.findall(r'(\w+)=(-?\d+(?:\.\d+)?)',z)}
            elif z.startswith('[v35_front]'): q['front']={a:float(b) for a,b in re.findall(r'(\w+)=(-?\d+(?:\.\d+)?)',z)}
        ss.append(q)
    def av(sec,key,d=0):
        v=[x.get(sec,{}).get(key) for x in ss if key in x.get(sec,{})]; return statistics.mean(v) if v else d
    def land(t):
        v=[x.get('land',{}).get(t) for x in ss if t in x.get('land',{})]; return statistics.mean(v) if v else 0
    return {'loss_samples':len(ss),'turns':statistics.mean([x['turns'] for x in ss]) if ss else 0,'land200':land(200),'land250':land(250),'land400':land(400),'passes':av('actions','pass'),'no_strategic':av('pass','pass_no_strategic_candidate'),'picker_starts':av('picker','starts'),'picker_completions':av('picker','completions'),'picker_mass_rejects':av('picker','mass_rejects'),'picker_eff_rejects':av('picker','efficiency_rejects'),'muster_windows':av('muster','windows'),'muster_attack':av('muster','attack_moves'),'doom_starts':av('doom','starts'),'threats':av('threat','threats_seen_incoming'),'contact_turn':av('front','meaningful_contact',-1)}

def diagnose(m):
    r=[]
    if m.get('land200',0) and m['land200']<55:r.append('weak early expansion')
    if m.get('picker_starts',0)<.5:r.append('picker rarely starts')
    if m.get('muster_windows',0)>1 and m.get('muster_attack',0)<.5:r.append('muster harvest fails to launch')
    if m.get('passes',0)>8 or m.get('no_strategic',0)>3:r.append('too many pass/no-strategic actions')
    if m.get('doom_starts',0)<.25 and m.get('threats',0)>1:r.append('doom defense too insensitive')
    return r or ['general robustness loss']

def mutation_order(m):
    k=[]
    if m.get('land200',0) and m['land200']<55:k+=['early_expansion']
    if m.get('picker_starts',0)<.5 and m.get('picker_mass_rejects',0)>=m.get('picker_eff_rejects',0):k+=['picker_mass_lower']
    if m.get('picker_starts',0)<.5 and m.get('picker_eff_rejects',0)>0:k+=['picker_eff_lower']
    if m.get('muster_windows',0)>1 and m.get('muster_attack',0)<.5:k+=['launch_lower','finish_earlier']
    if m.get('passes',0)>8:k+=['muster_threshold_lower','picker_eff_lower']
    if m.get('doom_starts',0)<.25 and m.get('threats',0)>1:k+=['doom_more_sensitive']
    k+=['early_expansion','picker_mass_lower','picker_eff_lower','muster_threshold_lower','launch_lower','finish_earlier','concentration_more']
    out=[]
    for x in k:
        if x not in out: out.append(x)
    return out

def mutate_text(s,key):
    if key=='picker_mass_lower':
        m=re.search(r'edge_picker_threshold_=(\d+)',s); 
        if m: return s[:m.start(1)]+str(max(8,int(m.group(1))-2))+s[m.end(1):]
    if key=='picker_eff_lower':
        m=re.search(r'edge_picker_min_efficiency_=([0-9.]+)',s)
        if m: return s[:m.start(1)]+str(round(max(.9,float(m.group(1))-.10),2))+s[m.end(1):]
    if key=='muster_threshold_lower':
        m=re.search(r'muster_threshold_=(\d+)',s)
        if m: return s[:m.start(1)]+str(max(4,int(m.group(1))-1))+s[m.end(1):]
    if key=='early_expansion':
        m=re.search(r'\(\(!enemy_seen&&o\.turn<=250\)\?\.([0-9]+):\.35\)',s)
        if m:
            v=min(.50,float('.'+m.group(1))+.02); return s[:m.start()]+f'((!enemy_seen&&o.turn<=250)?{v:.2f}:.35)'+s[m.end():]
        old='production_==ProductionState::SOFT_DEFICIT?.45:.35'
        if old in s:return s.replace(old,'production_==ProductionState::SOFT_DEFICIT?.45:((!enemy_seen&&o.turn<=250)?.37:.35)',1)
    if key=='launch_lower':
        m=re.search(r'launch_need=std::max\(\{(\d+),eg_army\*3\+(\d+)',s)
        if m:
            rep=f'launch_need=std::max({{{max(65,int(m.group(1))-5)},eg_army*3+{max(5,int(m.group(2))-5)}'; return s[:m.start()]+rep+s[m.end():]
    if key=='finish_earlier':
        m=re.search(r'late_finish=o\.turn>=(\d+)',s)
        if m:return s[:m.start(1)]+str(max(650,int(m.group(1))-25))+s[m.end(1):]
    if key=='concentration_more':
        m=re.search(r'own_peak\*100<std::max\(1,o\.my_army\)\*(\d+)',s)
        if m:return s[:m.start(1)]+str(min(65,int(m.group(1))+5))+s[m.end(1):]
    if key=='doom_more_sensitive':
        m=re.search(r'doom_eta_now<=([0-9]+)&&largest_army>=doom_floor',s)
        if m:return s[:m.start(1)]+str(min(16,int(m.group(1))+1))+s[m.end(1):]
    return None

def choose_mutation(s,line,parent_sha,m):
    hist=[x for x in s['mutation_history'].get(line,[]) if x.get('parent_sha')==parent_sha]
    tried={x.get('mutation') for x in hist}
    for k in mutation_order(m):
        if k not in tried:return k
    return None

def make_candidate(parent_sha,line,cycle,it,key):
    p=wt(parent_sha,f'/tmp/e2-cand-{line}'); main=p/AGENT/'main.cpp'; old=main.read_text(); new=mutate_text(old,key)
    if not new or new==old: raise RuntimeError(f'mutation {key} not applicable')
    main.write_text(new); build(p); branch=f'evolution2/candidates/{line.lower()}-c{cycle}-i{it}-{key}'; git('checkout','-B',branch,cwd=p); git('add',str(AGENT/'main.cpp'),cwd=p); git('config','user.name','github-actions[bot]',cwd=p); git('config','user.email','41898282+github-actions[bot]@users.noreply.github.com',cwd=p); git('commit','-m',f'evolution2 candidate {line} c{cycle} i{it}: {key}',cwd=p); sha=wsha(p); git('push','--force','origin',f'HEAD:{branch}',cwd=p); return p,sha,branch

def prepare_opps(s):
    fetch_all(); ready=[]; fail=[]; used=set(); resolved=set(); subs=[]
    for i,(cat,refs) in enumerate(OPPS):
        chosen=None
        for ref in refs:
            if git('rev-parse','--verify',f'origin/{ref}',capture=True,check=False).returncode: fail.append({'category':cat,'ref':ref,'reason':'missing'}); continue
            p=wt(f'origin/{ref}',f'/tmp/e2-opp-{i}')
            try: build(p); chosen=(cat,ref,p); break
            except Exception as e: fail.append({'category':cat,'ref':ref,'reason':str(e)})
        if chosen and chosen[1] not in used:
            ready.append(chosen); used.add(chosen[1]); resolved.add(cat)
            if chosen[1]!=refs[0]:subs.append({'category':cat,'preferred':refs[0],'substitute':chosen[1]})
    if CORE-resolved: raise RuntimeError(f'missing core archetypes {sorted(CORE-resolved)}')
    if len(ready)<7: raise RuntimeError('fewer than 7 diverse opponents')
    s['opponent_substitutions']=subs; return ready,fail,subs

def suite(path,opps,s,label,purpose,maps=3,starts=None):
    wr=Path(f'/tmp/e2-suite-{label}'); shutil.rmtree(wr,ignore_errors=True); wr.mkdir(parents=True); cw=wrapper(path/AGENT/'run.sh',label,wr/'cand.sh'); rows=[]
    for i,(cat,ref,opp) in enumerate(opps):
        st=(starts or {}).get(cat) if starts else None
        if st is None: st=fresh(s,maps,f'{purpose}-{cat}')
        ow=wrapper(opp/AGENT/'run.sh','OPP',wr/f'o{i}.sh'); z=bench(cw,ow,st,maps,RESULTS/purpose/label/cat); rows.append({'category':cat,'ref':ref,'start':st,'summary':z})
    return rows,combine([r['summary'] for r in rows])

def gate_a(s,cand,parent,line,cycle,it):
    wr=Path('/tmp/e2-ga'); shutil.rmtree(wr,ignore_errors=True); wr.mkdir(); cw=wrapper(cand/AGENT/'run.sh','CAND',wr/'c.sh'); pw=wrapper(parent/AGENT/'run.sh','PARENT',wr/'p.sh'); rounds=[]
    st=fresh(s,10,f'c{cycle}i{it}-{line}-gateA-r1'); a=bench(cw,pw,st,10,RESULTS/f'c{cycle}/iter-{it:02d}/{line}/gateA/r1'); rounds.append({'start':st,'summary':a}); cum=combine([a])
    if a['score']>=.575 and a['W']>a['L']:return {'rounds':rounds,'cumulative':cum,'decision':'pass'}
    if a['score']<=.525:return {'rounds':rounds,'cumulative':cum,'decision':'reject'}
    st=fresh(s,10,f'c{cycle}i{it}-{line}-gateA-r2'); b=bench(cw,pw,st,10,RESULTS/f'c{cycle}/iter-{it:02d}/{line}/gateA/r2'); rounds.append({'start':st,'summary':b}); cum=combine([a,b]); return {'rounds':rounds,'cumulative':cum,'decision':'pass' if cum['score']>=.55 and cum['W']>cum['L'] else 'reject'}

def gate_b(s,parent,cand,opps,line,cycle,it):
    wr=Path('/tmp/e2-gb'); shutil.rmtree(wr,ignore_errors=True); wr.mkdir(); pw=wrapper(parent/AGENT/'run.sh','PARENT',wr/'p.sh'); cw=wrapper(cand/AGENT/'run.sh','CAND',wr/'c.sh'); rows=[]; ps=[]; cs=[]
    for i,(cat,ref,opp) in enumerate(opps):
        st=fresh(s,3,f'c{cycle}i{it}-{line}-gateB-{cat}'); ow=wrapper(opp/AGENT/'run.sh','OPP',wr/f'o{i}.sh'); p=bench(pw,ow,st,3,RESULTS/f'c{cycle}/iter-{it:02d}/{line}/gateB/{cat}/parent'); c=bench(cw,ow,st,3,RESULTS/f'c{cycle}/iter-{it:02d}/{line}/gateB/{cat}/candidate'); pc=p; cc=c; row={'category':cat,'ref':ref,'start':st,'parent':p,'candidate':c,'delta':c['score']-p['score']}
        if row['delta']<-.10:
            st2=fresh(s,5,f'c{cycle}i{it}-{line}-gateB-confirm-{cat}'); pe=bench(pw,ow,st2,5,RESULTS/f'c{cycle}/iter-{it:02d}/{line}/gateB/{cat}/parent-confirm'); ce=bench(cw,ow,st2,5,RESULTS/f'c{cycle}/iter-{it:02d}/{line}/gateB/{cat}/candidate-confirm'); pc=combine([p,pe]); cc=combine([c,ce]); row['confirmation']={'start':st2,'parent':pe,'candidate':ce}; row['delta_combined']=cc['score']-pc['score']
        ps.append(pc); cs.append(cc); rows.append(row)
    pa=combine(ps); ca=combine(cs); bad=[r['category'] for r in rows if r.get('delta_combined',r['delta'])<-.10]; return {'opponents':rows,'parent_aggregate':pa,'candidate_aggregate':ca,'catastrophic_regressions':bad,'decision':'pass' if ca['score']>=pa['score'] and not bad else 'reject'}

def gate_c(s,cand,line,cycle,it):
    anchors=[s['original_x_sha'] if line=='X' else s['original_y_sha']]; best=s['best_x_sha'] if line=='X' else s['best_y_sha'];
    if best not in anchors: anchors.append(best)
    rows=[]
    for j,a in enumerate(anchors):
        ap=wt(a,f'/tmp/e2-anchor-{j}'); build(ap); wr=Path('/tmp/e2-gc'); shutil.rmtree(wr,ignore_errors=True); wr.mkdir(); cw=wrapper(cand/AGENT/'run.sh','CAND',wr/'c.sh'); aw=wrapper(ap/AGENT/'run.sh','ANCHOR',wr/'a.sh'); st=fresh(s,5,f'c{cycle}i{it}-{line}-gateC-{j}'); q=bench(cw,aw,st,5,RESULTS/f'c{cycle}/iter-{it:02d}/{line}/gateC/{j}/r1'); allq=[q];
        if q['score']<.45:
            st2=fresh(s,5,f'c{cycle}i{it}-{line}-gateC-{j}-confirm'); q2=bench(cw,aw,st2,5,RESULTS/f'c{cycle}/iter-{it:02d}/{line}/gateC/{j}/r2'); allq.append(q2)
        cum=combine(allq); rows.append({'anchor_sha':a,'cumulative':cum});
        if cum['score']<.45:return {'anchors':rows,'decision':'reject'}
    return {'anchors':rows,'decision':'pass'}

def persist(msg,paths):
    git('config','user.name','github-actions[bot]'); git('config','user.email','41898282+github-actions[bot]@users.noreply.github.com')
    for p in paths:
        if Path(p).exists(): git('add',str(p))
    if git('diff','--cached','--quiet',check=False).returncode:return
    git('commit','-m',msg); git('push','origin',f'HEAD:{CONTROL}')

def attempt(s,line,parent_path,metrics,opps,cycle,it,context):
    parent_sha=s['current_x_champion_sha'] if line=='X' else s['current_y_champion_sha']; key=choose_mutation(s,line,parent_sha,metrics); rp=RESULTS/f'c{cycle}/iter-{it:02d}/{line}/report.json'; r={'cycle':cycle,'iteration':it,'target_lineage':line,'parent_sha':parent_sha,'causal_hypothesis':diagnose(metrics),'loss_metrics':metrics,'context':context,'mutation':key}
    if key is None:
        r.update({'decision':'REJECTED','rejection_reason':'no untried coherent mutation','champion_sha_after':parent_sha}); s['rejected_mutations'].append(r.copy()); s['mutation_history'][line].append({'parent_sha':parent_sha,'mutation':None,'accepted':False}); dump(rp,r); return False
    try: cand,csha,cbranch=make_candidate(parent_sha,line,cycle,it,key)
    except Exception as e:
        r.update({'decision':'REJECTED','rejection_reason':f'candidate build/test failed: {e}','champion_sha_after':parent_sha}); s['mutation_history'][line].append({'parent_sha':parent_sha,'mutation':key,'accepted':False,'reason':str(e)}); dump(rp,r); return False
    r.update({'candidate_sha':csha,'candidate_branch':cbranch}); ga=gate_a(s,cand,parent_path,line,cycle,it); r['gateA']=ga
    if ga['decision']!='pass':
        r.update({'decision':'REJECTED','rejection_reason':'Gate A','champion_sha_after':parent_sha}); s['mutation_history'][line].append({'parent_sha':parent_sha,'candidate_sha':csha,'mutation':key,'accepted':False,'reason':'Gate A'}); dump(rp,r); return False
    gb=gate_b(s,parent_path,cand,opps,line,cycle,it); r['gateB']=gb
    if gb['decision']!='pass':
        r.update({'decision':'REJECTED','rejection_reason':'Gate B','champion_sha_after':parent_sha}); s['mutation_history'][line].append({'parent_sha':parent_sha,'candidate_sha':csha,'mutation':key,'accepted':False,'reason':'Gate B'}); dump(rp,r); return False
    gc=gate_c(s,cand,line,cycle,it); r['gateC']=gc
    if gc['decision']!='pass':
        r.update({'decision':'REJECTED','rejection_reason':'Gate C','champion_sha_after':parent_sha}); s['mutation_history'][line].append({'parent_sha':parent_sha,'candidate_sha':csha,'mutation':key,'accepted':False,'reason':'Gate C'}); dump(rp,r); return False
    live('before promotion'); s['pending_promotion']={'lineage':line,'parent_sha':parent_sha,'candidate_sha':csha,'candidate_branch':cbranch}; r['decision']='ACCEPTED_PENDING'; dump(rp,r); dump(STATE,s); persist(f'evolution2: pending {line} c{cycle} i{it}',[STATE,rp]); live('immediately before ref move'); br=XBR if line=='X' else YBR
    if remote(br)!=parent_sha: raise RuntimeError(f'champion branch changed unexpectedly {br}')
    git('push','origin',f'{csha}:refs/heads/{br}')
    if remote(br)!=csha: raise RuntimeError('promotion ref move failed')
    if line=='X': s['current_x_champion_sha']=csha; s['best_x_sha']=csha
    else: s['current_y_champion_sha']=csha; s['best_y_sha']=csha
    s['hall_of_fame'].append({'lineage':line,'sha':csha,'reason':'accepted-promotion'}); s['accepted_since_audit']+=1; s['mutation_history'][line].append({'parent_sha':parent_sha,'candidate_sha':csha,'mutation':key,'accepted':True}); s['pending_promotion']=None; r.update({'decision':'ACCEPTED','champion_sha_after':csha}); dump(rp,r); dump(STATE,s); persist(f'evolution2: promote {line} {csha[:8]}',[STATE,rp]); return True

def champions(s):
    if remote(XBR)!=s['current_x_champion_sha'] or remote(YBR)!=s['current_y_champion_sha']:raise RuntimeError('state/ref mismatch')
    x=wt(s['current_x_champion_sha'],'/tmp/e2-x'); y=wt(s['current_y_champion_sha'],'/tmp/e2-y'); build(x); build(y); return x,y

def h2h(s,x,y,maps,purpose,out):
    wr=Path('/tmp/e2-h2h'); shutil.rmtree(wr,ignore_errors=True); wr.mkdir(); xw=wrapper(x/AGENT/'run.sh','X',wr/'x.sh'); yw=wrapper(y/AGENT/'run.sh','Y',wr/'y.sh'); st=fresh(s,maps,purpose); z=bench(xw,yw,st,maps,out); mx=parse_metrics(Path(out)/'games.jsonl','X',lambda g:g.get('result')=='loss'); my=parse_metrics(Path(out)/'games.jsonl','Y',lambda g:g.get('result')=='win'); return z,mx,my,st

def preflight(s):
    live('preflight'); x,y=champions(s); opps,fail,subs=prepare_opps(s); hv,mx,my,st=h2h(s,x,y,10,'preflight-X-v-Y',BASE/'x-v-y'); starts={c:fresh(s,3,f'preflight-suite-{c}') for c,_,_ in opps}; xr,xa=suite(x,opps,s,'X','preflight-X',3,starts); yr,ya=suite(y,opps,s,'Y','preflight-Y',3,starts); rep={'x_sha':X0,'y_sha':Y0,'x_v_y':hv,'x_v_y_start':st,'x_suite':xr,'y_suite':yr,'x_aggregate':xa,'y_aggregate':ya,'opponent_failures':fail,'substitutions':subs}; dump(BASE/'report.json',rep); s['baseline_summary']={'x_v_y':hv,'x_suite':xa,'y_suite':ya}; s['phase']='cycle1'; s['retry_count']=0;s['last_error']=None;dump(STATE,s);persist('evolution2: complete preflight',[STATE,BASE/'report.json'])

def cycle1(s):
    it=s['cycle1_attempted']+1; live(f'cycle1 {it}'); x,y=champions(s); opps,fail,subs=prepare_opps(s); hv,mx,my,st=h2h(s,x,y,10,f'c1i{it}-h2h',RESULTS/f'c1/iter-{it:02d}/h2h');
    if hv['score']<.475: weak='X'
    elif hv['score']>.525: weak='Y'
    else:
        tb,tx,ty,tst=h2h(s,x,y,5,f'c1i{it}-tiebreak',RESULTS/f'c1/iter-{it:02d}/tiebreak'); weak='X' if tb['score']<.5 else ('Y' if tb['score']>.5 else ('X' if it%2 else 'Y'))
    ok=attempt(s,weak,x if weak=='X' else y,mx if weak=='X' else my,opps,1,it,{'x_v_y':hv,'start':st}); s['cycle1_attempted']=it; s['cycle1_promoted']+=int(ok); s['cycle1_rejected']+=int(not ok); 
    if it>=23:s['phase']='cycle2'
    dump(STATE,s);persist(f'evolution2: finalize cycle1 attempt {it}',[STATE])

def cycle2(s):
    it=s['cycle2_attempted']+1; live(f'cycle2 {it}'); x,y=champions(s); opps,fail,subs=prepare_opps(s); hv,mx,my,st=h2h(s,x,y,5,f'c2i{it}-h2h',RESULTS/f'c2/iter-{it:02d}/h2h'); starts={c:fresh(s,3,f'c2i{it}-diag-{c}') for c,_,_ in opps}; xr,xa=suite(x,opps,s,'X',f'c2/iter-{it:02d}/diagX',3,starts); yr,ya=suite(y,opps,s,'Y',f'c2/iter-{it:02d}/diagY',3,starts)
    # only mutate when there is meaningful weakness: aggregate < .72 or any archetype < .50
    def weak(rows,agg): return agg['score']<.72 or any(r['summary']['score']<.50 for r in rows)
    xok=None; yok=None
    if weak(xr,xa):
        worst=min(xr,key=lambda r:r['summary']['score']); xm=parse_metrics(RESULTS/f'c2/iter-{it:02d}/diagX'/'X'/worst['category']/'games.jsonl','X',lambda g:g.get('result')=='loss'); xok=attempt(s,'X',x,xm,opps,2,it,{'h2h':hv,'suite_aggregate':xa,'worst':worst['category']})
    if weak(yr,ya):
        # refresh Y parent path in case X promotion occurred; Y is independent
        y=wt(s['current_y_champion_sha'],'/tmp/e2-y2'); build(y); worst=min(yr,key=lambda r:r['summary']['score']); ym=parse_metrics(RESULTS/f'c2/iter-{it:02d}/diagY'/'Y'/worst['category']/'games.jsonl','Y',lambda g:g.get('result')=='loss'); yok=attempt(s,'Y',y,ym,opps,2,it,{'h2h':hv,'suite_aggregate':ya,'worst':worst['category']})
    s['cycle2_attempted']=it
    if xok is None:s['cycle2_x_skipped']+=1
    elif xok:s['cycle2_x_promoted']+=1
    else:s['cycle2_x_rejected']+=1
    if yok is None:s['cycle2_y_skipped']+=1
    elif yok:s['cycle2_y_promoted']+=1
    else:s['cycle2_y_rejected']+=1
    if it>=32:s['phase']='final'
    dump(STATE,s);persist(f'evolution2: finalize cycle2 attempt {it}',[STATE])

def final_tournament(s):
    live('final'); opps,fail,subs=prepare_opps(s); shas=[]
    for q in [s['current_x_champion_sha'],s['current_y_champion_sha'],s['original_x_sha'],s['original_y_sha'],s['best_x_sha'],s['best_y_sha']]:
        if q not in shas: shas.append(q)
    cands=[]
    for i,q in enumerate(shas): p=wt(q,f'/tmp/e2-final-{i}'); build(p); cands.append((q,p))
    suite_scores={}
    starts={c:fresh(s,5,f'final-suite-{c}') for c,_,_ in opps}
    for i,(q,p) in enumerate(cands): rows,agg=suite(p,opps,s,f'C{i}',f'final/{i}',5,starts); suite_scores[q]={'rows':rows,'aggregate':agg,'min':min(r['summary']['score'] for r in rows)}
    mutual=[]
    for i in range(len(cands)):
        for j in range(i+1,len(cands)):
            a,ap=cands[i]; b,bp=cands[j]; wr=Path('/tmp/e2-final-h2h'); shutil.rmtree(wr,ignore_errors=True); wr.mkdir(); aw=wrapper(ap/AGENT/'run.sh','A',wr/'a.sh'); bw=wrapper(bp/AGENT/'run.sh','B',wr/'b.sh'); st=fresh(s,10,f'final-h2h-{i}-{j}'); z=bench(aw,bw,st,10,RESULTS/f'final/h2h-{i}-{j}'); mutual.append({'a':a,'b':b,'start':st,'summary':z})
    champ=max(shas,key=lambda q:(suite_scores[q]['aggregate']['score'],suite_scores[q]['min'],suite_scores[q]['aggregate']['W']))
    cp=dict(cands)[champ]; shutil.rmtree(FINAL,ignore_errors=True); (FINAL/'juraj_v35').mkdir(parents=True)
    for f in ['main.cpp','core.hpp','build.sh','run.sh']: shutil.copy2(cp/AGENT/f,FINAL/'juraj_v35'/f)
    val={'champion_sha':champ,'final_x_sha':s['current_x_champion_sha'],'final_y_sha':s['current_y_champion_sha'],'suite':suite_scores,'mutual':mutual,'cycle1_attempted':s['cycle1_attempted'],'cycle1_promoted':s['cycle1_promoted'],'cycle1_rejected':s['cycle1_rejected'],'cycle2_attempted':s['cycle2_attempted'],'cycle2_x_promoted':s['cycle2_x_promoted'],'cycle2_y_promoted':s['cycle2_y_promoted'],'rollback_history':s['rollback_history']}; dump(FINAL/'VALIDATION.json',val)
    run(['bash','build.sh'],cwd=FINAL/'juraj_v35'); a=FINAL/'juraj_v35'/'agent'; a.unlink(missing_ok=True)
    zp=FINAL/'generals_final_submission.zip';
    with zipfile.ZipFile(zp,'w',zipfile.ZIP_DEFLATED) as z:
        for f in ['main.cpp','core.hpp','build.sh','run.sh']: z.write(FINAL/'juraj_v35'/f,arcname='juraj_v35/'+f)
    chk=hashlib.sha256(zp.read_bytes()).hexdigest(); (FINAL/'generals_final_submission.sha256').write_text(chk+'  generals_final_submission.zip\n'); s['final_champion_sha']=champ; s['phase']='done'; dump(STATE,s); persist('evolution2: final champion and submission',[STATE,FINAL/'VALIDATION.json',FINAL/'generals_final_submission.sha256'])

def failure(s,e):
    s['retry_count']=int(s.get('retry_count',0))+1; s['last_error']=str(e); dump(STATE,s); Path('evolution2/last-error.txt').write_text(str(e)+'\n'); persist('evolution2: record infrastructure failure',[STATE,'evolution2/last-error.txt'])

def main():
    s=load();
    try:
        if STOP.exists(): print('STOP present'); return 0
        fetch_all()
        ph=s['phase']
        if ph=='preflight':preflight(s)
        elif ph=='cycle1':cycle1(s)
        elif ph=='cycle2':cycle2(s)
        elif ph=='final':final_tournament(s)
        elif ph=='done':print('done')
        else:raise RuntimeError(f'bad phase {ph}')
        s=load(); s['retry_count']=0; s['last_error']=None; dump(STATE,s); persist('evolution2: clear recovery state',[STATE]); return 0
    except StopIteration as e: print(e); return 0
    except Exception as e: print('EVOLUTION2 FAILURE:',e,file=sys.stderr); failure(s,e); return 2

if __name__=='__main__': raise SystemExit(main())
