from __future__ import annotations
import copy, random
from tools.evolution4.schema import load_schema, chromosomes
from tools.evolution4.genome import canonical_values
from .genome import canonical_genome
from .graph import MODULES, CONDITIONS, ISLANDS, canonical_graph, repair_graph, specialize_graph

NORMAL_MIX={'micro':.25,'crossover':.25,'bundle':.20,'module':.15,'graph':.10,'immigrant':.05}
PLATEAU_MIX={'micro':.10,'crossover':.15,'bundle':.20,'module':.20,'graph':.25,'immigrant':.10}
BUNDLES=('rush','fortress','economy','hunter','muster','defense','finish','adaptive')


def _mutate_params(params:dict,rng:random.Random,temperature:float=1.0,count:int|None=None)->dict:
    data,_=load_schema(); genes=[g for g in data['genes'] if g['name']!='picker_neutrals_max']; out=dict(params)
    n=count if count is not None else rng.randint(1,max(2,round(3*temperature)))
    for g in rng.sample(genes,min(n,len(genes))):
        name,t,old=g['name'],g['type'],out.get(g['name'],g['default'])
        if t=='bool': out[name]=not bool(old)
        elif t=='enum':
            opts=[x for x in g['allowed'] if x!=old]; out[name]=rng.choice(opts) if opts else old
        elif t=='int': out[name]=int(old)+rng.choice([-2,-1,1,2])*max(1,round(g.get('mutation_step',1)*temperature))
        elif t=='float': out[name]=float(old)+rng.gauss(0,float(g.get('mutation_sigma',.05))*temperature)
    return canonical_values(out)


def micro_mutation(genome:dict,rng:random.Random,temperature:float=1.0)->dict:
    g=canonical_genome(genome); g['params']=_mutate_params(g['params'],rng,temperature); return canonical_genome(g)


def _one_module_edit(graph:dict,rng:random.Random)->dict:
    graph=copy.deepcopy(graph); graph['mode']='evolved'; names=list(graph['nodes']); name=rng.choice(names); q=graph['nodes'][name]
    action=rng.choice(('add','remove','reorder','instances','transition'))
    if action=='add':
        opts=[m for m in MODULES if m not in q['modules']]
        if opts:
            m=rng.choice(opts); q['modules'].append(m); q['priority'].insert(rng.randrange(len(q['priority'])+1),m); q['instances'][m]=rng.randint(1,2)
    elif action=='remove' and len(q['modules'])>2:
        m=rng.choice(q['modules']); q['modules'].remove(m); q['priority']=[x for x in q['priority'] if x!=m]; q['instances'].pop(m,None)
    elif action=='reorder' and len(q['priority'])>1:
        i,j=rng.sample(range(len(q['priority'])),2); q['priority'][i],q['priority'][j]=q['priority'][j],q['priority'][i]
    elif action=='instances':
        m=rng.choice(q['modules']); old=int(q['instances'].get(m,1)); opts=[x for x in (1,2,3) if x!=old]; q['instances'][m]=rng.choice(opts)
    elif len(names)>1:
        if q['transitions']:
            t=rng.choice(q['transitions']); old=(t['condition'],t['target']); choices=[(c,target) for c in CONDITIONS for target in names if (c,target)!=old]
            t['condition'],t['target']=rng.choice(choices)
        else: q['transitions'].append({'condition':rng.choice(CONDITIONS),'target':rng.choice(names)})
    return repair_graph(graph)


def module_mutation(genome:dict,rng:random.Random)->dict:
    g=canonical_genome(genome); original=g['graph']
    for _ in range(12):
        changed=_one_module_edit(original,rng)
        if changed!=original:
            g['graph']=changed; return canonical_genome(g)
    graph=copy.deepcopy(original); graph['mode']='evolved'; name=graph['entry']; q=graph['nodes'][name]; opts=[m for m in MODULES if m not in q['modules']]
    if opts:
        m=opts[0]; q['modules'].append(m); q['priority'].insert(0,m); q['instances'][m]=1
    else:
        m=q['modules'][0]; q['instances'][m]=2 if int(q['instances'].get(m,1))!=2 else 3
    g['graph']=repair_graph(graph); return canonical_genome(g)


def _random_node(rng:random.Random,names:list[str]):
    mods=rng.sample(list(MODULES),rng.randint(3,8)); pri=list(mods); rng.shuffle(pri); tr=[]
    if names: tr=[{'condition':rng.choice(CONDITIONS),'target':rng.choice(names)}]
    return {'modules':mods,'priority':pri,'instances':{m:rng.randint(1,3 if m in ('ATTACK','MUSTER') else 2) for m in mods},'transitions':tr}


def graph_rewrite(genome:dict,rng:random.Random,intensity:float=.30)->dict:
    g=canonical_genome(genome); graph=copy.deepcopy(g['graph']); graph['mode']='evolved'; nodes=graph['nodes']; names=list(nodes)
    k=max(1,min(len(names),round(len(names)*max(.2,min(.4,intensity)))))
    for name in rng.sample(names,k):
        q=nodes[name]; mods=rng.sample(list(MODULES),rng.randint(3,9)); q['modules']=mods; q['priority']=rng.sample(mods,len(mods)); q['instances']={m:rng.randint(1,3 if m in ('ATTACK','MUSTER') else 2) for m in mods}
        if len(names)>1: q['transitions']=[{'condition':rng.choice(CONDITIONS),'target':rng.choice(names)} for _ in range(rng.randint(0,2))]
    if rng.random()<.45 and len(nodes)<8:
        new=f'NOVEL_{rng.randrange(100000)}'; nodes[new]=_random_node(rng,list(nodes)); src=rng.choice(list(nodes))
        if src!=new: nodes[src]['transitions'].append({'condition':rng.choice(CONDITIONS),'target':new})
    if rng.random()<.30 and len(nodes)>3:
        victim=rng.choice([n for n in nodes if n!=graph['entry']]); nodes.pop(victim)
        for q in nodes.values():
            for t in q['transitions']:
                if t['target']==victim: t['target']=graph['entry']
    g['graph']=repair_graph(graph); g['params']=_mutate_params(g['params'],rng,1.5,rng.randint(4,9)); return canonical_genome(g)


def _force_finish_phase(graph:dict):
    if 'LATE' not in graph['nodes']: return
    q=graph['nodes']['LATE']
    if 'FINISH' not in q['modules']:
        q['modules'].append('FINISH'); q['instances']['FINISH']=2
    q['instances']['FINISH']=max(2,int(q['instances'].get('FINISH',1)))
    q['priority']=['FINISH']+[x for x in q['priority'] if x!='FINISH']


def strategy_bundle(genome:dict,rng:random.Random,bundle:str|None=None)->dict:
    g=canonical_genome(genome); bundle=bundle or rng.choice(BUNDLES)
    island={'rush':'Rush','fortress':'Fortress','economy':'Economy','hunter':'Hunter','muster':'Muster-Logistics','defense':'Fortress','finish':'Hunter','adaptive':'Adaptive'}[bundle]
    target=specialize_graph(island); graph=copy.deepcopy(g['graph']); graph['mode']='evolved'
    for name,q in target['nodes'].items():
        if name not in graph['nodes'] or rng.random()<.65: graph['nodes'][name]=copy.deepcopy(q)
    if bundle in ('rush','finish'): _force_finish_phase(graph)
    g['graph']=repair_graph(graph); p=dict(g['params'])
    if bundle=='rush': p.update({'war_share_contact':.58,'war_share_peace':.28,'castle1_target_turn':240,'castle2_target_turn':400,'muster_start_turn':190,'late_finish_turn':675,'general_reserve_base':3})
    elif bundle=='fortress': p.update({'doomguard_enabled':True,'general_reserve_base':12,'adjacent_reserve_base':6,'castle1_target_turn':120,'castle2_target_turn':210,'war_share_contact':.22})
    elif bundle=='economy': p.update({'expansion_share_healthy':.55,'expansion_share_soft':.64,'search_share_unseen':.34,'castle1_target_turn':145,'castle2_target_turn':245})
    elif bundle=='hunter': p.update({'search_share_unseen':.48,'search_share_seen':.25,'war_share_contact':.52,'late_finish_turn':700,'late_finish_base':50})
    elif bundle=='muster': p.update({'muster_start_turn':210,'muster_launch_base':60,'muster_topology':'triple','free_share_war':.32,'picker_enabled':True})
    elif bundle=='defense': p.update({'doomguard_enabled':True,'general_reserve_base':14,'general_reserve_opp_divisor':8,'adjacent_reserve_base':7,'war_share_contact':.30})
    elif bundle=='finish': p.update({'late_finish_turn':650,'late_finish_base':40,'late_finish_enemy_mult':1.2,'war_share_contact':.58})
    g['params']=canonical_values(p); return canonical_genome(g)


def crossover_genomes(a:dict,b:dict,rng:random.Random)->dict:
    a=canonical_genome(a); b=canonical_genome(b); groups=chromosomes(); params=dict(a['params'])
    for _,names in groups.items():
        src=a['params'] if rng.random()<.5 else b['params']
        for n in names: params[n]=src[n]
    ga,gb=a['graph'],b['graph']; nodes={}
    for name in sorted(set(ga['nodes'])|set(gb['nodes'])):
        src=ga if name in ga['nodes'] and (name not in gb['nodes'] or rng.random()<.5) else gb
        if name in src['nodes']: nodes[name]=copy.deepcopy(src['nodes'][name])
    entry=ga['entry'] if ga['entry'] in nodes and rng.random()<.5 else gb['entry'] if gb['entry'] in nodes else next(iter(nodes))
    child={'graph':repair_graph({'version':1,'mode':'evolved','entry':entry,'nodes':nodes}),'params':canonical_values(params)}
    return micro_mutation(child,rng,1.0)


def random_immigrant(base_params:dict,rng:random.Random,island:str|None=None)->dict:
    island=island or rng.choice(ISLANDS); g={'graph':specialize_graph(island),'params':canonical_values(base_params)}
    for _ in range(rng.randint(2,5)): g=graph_rewrite(g,rng,rng.uniform(.25,.40))
    g['params']=_mutate_params(g['params'],rng,2.2,rng.randint(8,16)); return canonical_genome(g)


def choose_kind(rng:random.Random,mix:dict[str,float])->str:
    keys=list(mix); return rng.choices(keys,weights=[mix[k] for k in keys],k=1)[0]
