from __future__ import annotations
import copy, hashlib, json, random, subprocess
from pathlib import Path
from tools.evolution4.evaluator import ROOT
from tools.evolution4.genome import founder_x0, founder_y0, canonical_values
from .graph import ISLANDS, baseline_graph, specialize_graph
from .genome import genome_id, save_genome
from .mutate import strategy_bundle, module_mutation, graph_rewrite, crossover_genomes, random_immigrant

E5=ROOT/'evolution5'; STATE=E5/'state.json'; GENOMES=E5/'genomes'
CONTROL='evolution4/turbo-structural'


def _run(*args): return subprocess.run(args,cwd=ROOT,text=True,capture_output=True,check=True).stdout

def _remote_json(path:str):
    subprocess.run(['git','fetch','--no-tags','origin',CONTROL],cwd=ROOT,check=True,timeout=120)
    return json.loads(_run('git','show',f'origin/{CONTROL}:{path}'))


def _remote_e4_values(gid:str):
    try: return _remote_json(f'evolution4/genomes/{gid}.json')['values']
    except Exception: return None


def _unique_save(genome:dict,meta:dict,known:set[str])->str:
    rng=random.Random(int(hashlib.sha256(json.dumps(meta,sort_keys=True).encode()).hexdigest()[:12],16))
    for _ in range(40):
        gid=genome_id(genome)
        if gid not in known:
            save_genome(GENOMES/f'{gid}.json',genome,meta); known.add(gid); return gid
        genome=graph_rewrite(genome,rng,.35)
    raise RuntimeError('unable to produce unique Evolution5 genome')


def build_bootstrap_state()->tuple[dict,list[Path]]:
    e4=_remote_json('evolution4/state.json'); x=founder_x0(); y=founder_y0()
    source_ids=[]
    for gid in [e4.get('official_champion_genome_id'),*(e4.get('breeding_elites') or []),*(e4.get('current_population') or [])]:
        if gid and gid not in source_ids: source_ids.append(gid)
    source_values=[x,y]
    for gid in source_ids[:12]:
        v=_remote_e4_values(gid)
        if v is not None: source_values.append(canonical_values(v))
    rng=random.Random(5050001); known=set(); islands={}; all_ids=[]; origin_paths=[]
    adaptive_baselines=[]
    for ii,island in enumerate(ISLANDS):
        pop=[]
        for j in range(8):
            base=copy.deepcopy(source_values[(ii*3+j)%len(source_values)])
            graph=specialize_graph(island)
            if island=='Adaptive' and j<2:
                graph=baseline_graph(); base=x if j==0 else y
            g={'graph':graph,'params':base}; kind='specialized-seed'
            if j==1: g=strategy_bundle(g,rng); kind='strategy-bundle'
            elif j==2: g=module_mutation(g,rng); kind='module-mutation'
            elif j==3: g=graph_rewrite(g,rng,.30); kind='graph-rewrite'
            elif j==4:
                other={'graph':specialize_graph(ISLANDS[(ii+3)%len(ISLANDS)]),'params':source_values[(j+ii+1)%len(source_values)]}; g=crossover_genomes(g,other,rng); kind='cross-island-seed'
            elif j==5: g=random_immigrant(base,rng,island); kind='random-immigrant'
            elif j==6: g=graph_rewrite(graph_rewrite(g,rng,.35),rng,.35); kind='double-graph-rewrite'
            elif j==7: g=random_immigrant(base,rng,None); kind='wild-random-immigrant'
            gid=_unique_save(g,{'bootstrap':True,'island':island,'index':j,'kind':kind,'e4_source_generation':e4.get('generation')},known)
            pop.append(gid); all_ids.append(gid); origin_paths.append(GENOMES/f'{gid}.json')
            if island=='Adaptive' and j<2: adaptive_baselines.append(gid)
        islands[island]={'population':pop,'elite':pop[0],'best_score':None,'lineages':len(pop)}
    league=[]
    labels=['X0','Y0','Rush-seed','Fortress-seed','Hunter-seed','Muster-seed']
    seed_ids=[*adaptive_baselines,islands['Rush']['population'][0],islands['Fortress']['population'][0],islands['Hunter']['population'][0],islands['Muster-Logistics']['population'][0]]
    for label,gid in zip(labels,seed_ids): league.append({'genome_id':gid,'generation':-1,'fresh_score':0.0,'fresh_win_rate':0.0,'minimum':0.0,'archetypes':{},'coverage_gain':0.0,'novelty':0.0,'counter_score':.5,'protected':label in ('X0','Y0'),'label':label,'bootstrap':True})
    frozen={'generation':e4.get('generation'),'phase':e4.get('phase'),'official_champion_genome_id':e4.get('official_champion_genome_id'),'official_champion_commit_sha':e4.get('official_champion_commit_sha'),'architecture_epoch':e4.get('architecture_epoch'),'tested_genome_count':e4.get('tested_genome_count'),'dead_genome_count':e4.get('dead_genome_count')}
    state={
      'version':1,'mode':'cambrian_league_v1','phase':'evolving','generation':-1,'islands':islands,'population_size':64,'current_population':all_ids,
      'league':league,'map_elites':{},'tested_genomes':{},'dead_genomes':{},'adversary_hof':e4.get('adversary_hof',[]),'frozen_evolution4':frozen,
      'seed_ledger':{'training':{'next_seed':510000,'ranges':[]},'evaluation':{'next_seed':610000,'ranges':[]},'holdout':{'next_seed':710000,'ranges':[]},'promotion':{'next_seed':810000,'ranges':[]},'final':{'next_seed':910000,'ranges':[]}},
      'mutation_policy':{'normal':{'micro':.25,'crossover':.25,'bundle':.20,'module':.15,'graph':.10,'immigrant':.05},'plateau':{'micro':.10,'crossover':.15,'bundle':.20,'module':.20,'graph':.25,'immigrant':.10}},
      'mutation_temperature':1.0,'plateau_counter':0,'best_fresh_score':0.0,'best_fresh_win_rate':0.0,'best_fresh_genome_id':None,'extinction_history':[],
      'generation_history':[],'retry_count':0,'last_error':None,'last_successful_transaction_id':None,'bootstrap_seed':5050001,
    }
    STATE.parent.mkdir(parents=True,exist_ok=True); STATE.write_text(json.dumps(state,indent=2,sort_keys=True)+'\n')
    return state,[STATE,*origin_paths]


def ensure_bootstrap()->tuple[dict,list[Path]]:
    if STATE.exists():
        try:
            s=json.loads(STATE.read_text())
            if s.get('mode')=='cambrian_league_v1' and len(s.get('current_population',[]))==64: return s,[]
        except Exception: pass
    return build_bootstrap_state()
