from __future__ import annotations
import copy, hashlib, json, random
from tools.evolution4.genome import canonical_values

MODULES=(
    'EXPAND','SCOUT','PICK','BUILD_CASTLE','CONSOLIDATE','DEFEND_GENERAL',
    'INTERCEPT','MUSTER','ATTACK','HUNT_GENERAL','FINISH','RECOVER','LOGISTICS'
)
CONDITIONS=('always','contact','no_contact','ahead','behind','late','threat','enemy_seen')
ISLANDS=('Expansion','Rush','Fortress','Hunter','Economy','Muster-Logistics','Adaptive','Wildcard')


def _node(modules, priority=None, transitions=None, instances=None):
    mods=list(dict.fromkeys(modules))
    return {
        'modules':mods,
        'priority':list(priority or mods),
        'instances':dict(instances or {m:1 for m in mods}),
        'transitions':list(transitions or []),
    }


def baseline_graph():
    return {
        'version':1,'mode':'baseline','entry':'OPENING',
        'nodes':{
            'OPENING':_node(['DEFEND_GENERAL','EXPAND','SCOUT','BUILD_CASTLE','LOGISTICS'],
                            transitions=[{'condition':'contact','target':'CONTACT'},{'condition':'late','target':'LATE'}]),
            'CONTACT':_node(['DEFEND_GENERAL','INTERCEPT','ATTACK','EXPAND','LOGISTICS','MUSTER','PICK'],
                            transitions=[{'condition':'behind','target':'BEHIND'},{'condition':'late','target':'LATE'}]),
            'BEHIND':_node(['DEFEND_GENERAL','INTERCEPT','RECOVER','EXPAND','LOGISTICS','ATTACK'],
                           transitions=[{'condition':'ahead','target':'CONTACT'},{'condition':'late','target':'LATE'}]),
            'LATE':_node(['DEFEND_GENERAL','MUSTER','ATTACK','HUNT_GENERAL','FINISH','LOGISTICS'])
        }
    }


def _clean_graph(g:dict)->dict:
    mode='baseline' if g.get('mode')=='baseline' else 'evolved'
    raw=g.get('nodes') or {}
    nodes={}
    for name in sorted(raw):
        q=raw[name] if isinstance(raw[name],dict) else {}
        mods=[]
        for m in q.get('modules',[]):
            if m in MODULES and m not in mods: mods.append(m)
        if not mods: mods=['EXPAND']
        pri=[m for m in q.get('priority',[]) if m in mods]
        pri+= [m for m in mods if m not in pri]
        inst={m:max(1,min(3,int((q.get('instances') or {}).get(m,1)))) for m in mods}
        tr=[]
        for t in q.get('transitions',[]):
            if not isinstance(t,dict): continue
            c=t.get('condition'); target=t.get('target')
            if c in CONDITIONS and isinstance(target,str): tr.append({'condition':c,'target':target})
        nodes[str(name)]={'modules':mods,'priority':pri,'instances':inst,'transitions':tr}
    if not nodes:
        return baseline_graph()
    entry=g.get('entry') if g.get('entry') in nodes else next(iter(nodes))
    return {'version':1,'mode':mode,'entry':entry,'nodes':nodes}


def repair_graph(g:dict)->dict:
    x=_clean_graph(copy.deepcopy(g))
    nodes=x['nodes']
    while len(nodes)>8:
        victim=next((n for n in reversed(sorted(nodes)) if n!=x['entry']),None)
        if victim is None: break
        nodes.pop(victim)
        for q in nodes.values():
            for t in q['transitions']:
                if t['target']==victim: t['target']=x['entry']
    for q in nodes.values():
        q['transitions']=[t for t in q['transitions'] if t['target'] in nodes]
    reachable={x['entry']}; changed=True
    while changed:
        changed=False
        for n in list(reachable):
            for t in nodes[n]['transitions']:
                if t['target'] not in reachable:
                    reachable.add(t['target']); changed=True
    for n in sorted(set(nodes)-reachable):
        nodes[x['entry']]['transitions'].append({'condition':'always','target':n})
        reachable.add(n)
    return _clean_graph(x)


def validate_graph(g:dict)->None:
    if not isinstance(g,dict) or g.get('version')!=1: raise ValueError('graph version')
    if g.get('mode') not in ('baseline','evolved'): raise ValueError('graph mode')
    nodes=g.get('nodes')
    if not isinstance(nodes,dict) or not 2<=len(nodes)<=8: raise ValueError('graph node count')
    if g.get('entry') not in nodes: raise ValueError('graph entry')
    for name,q in nodes.items():
        mods=q.get('modules'); pri=q.get('priority'); inst=q.get('instances'); tr=q.get('transitions')
        if not mods or any(m not in MODULES for m in mods) or len(mods)!=len(set(mods)): raise ValueError(f'modules {name}')
        if set(pri)!=set(mods) or len(pri)!=len(mods): raise ValueError(f'priority {name}')
        if set(inst)!=set(mods) or any(not 1<=int(v)<=3 for v in inst.values()): raise ValueError(f'instances {name}')
        for t in tr:
            if t.get('condition') not in CONDITIONS or t.get('target') not in nodes: raise ValueError(f'transition {name}')
    reachable={g['entry']}; frontier=[g['entry']]
    while frontier:
        n=frontier.pop()
        for t in nodes[n]['transitions']:
            if t['target'] not in reachable:
                reachable.add(t['target']); frontier.append(t['target'])
    if reachable!=set(nodes): raise ValueError('unreachable graph node')


def canonical_graph(g:dict)->dict:
    x=repair_graph(g); validate_graph(x)
    return x


def graph_json(g:dict)->str:
    return json.dumps(canonical_graph(g),sort_keys=True,separators=(',',':'))


def graph_hash(g:dict)->str:
    return hashlib.sha256(graph_json(g).encode()).hexdigest()


def specialize_graph(island:str)->dict:
    g=baseline_graph(); g['mode']='evolved'; n=g['nodes']
    if island=='Expansion':
        n['OPENING']=_node(['EXPAND','SCOUT','LOGISTICS','BUILD_CASTLE','DEFEND_GENERAL'],['EXPAND','SCOUT','LOGISTICS','BUILD_CASTLE','DEFEND_GENERAL'],n['OPENING']['transitions'])
        n['CONTACT']=_node(['EXPAND','ATTACK','DEFEND_GENERAL','LOGISTICS','PICK'],['EXPAND','ATTACK','LOGISTICS','DEFEND_GENERAL','PICK'],n['CONTACT']['transitions'])
    elif island=='Rush':
        n['OPENING']=_node(['EXPAND','SCOUT','ATTACK','LOGISTICS','DEFEND_GENERAL'],['EXPAND','ATTACK','SCOUT','LOGISTICS','DEFEND_GENERAL'],n['OPENING']['transitions'])
        n['CONTACT']=_node(['ATTACK','HUNT_GENERAL','MUSTER','INTERCEPT','DEFEND_GENERAL','LOGISTICS'],['ATTACK','HUNT_GENERAL','MUSTER','INTERCEPT','DEFEND_GENERAL','LOGISTICS'],n['CONTACT']['transitions'],{'ATTACK':2,'MUSTER':2})
        n['LATE']=_node(['ATTACK','HUNT_GENERAL','FINISH','MUSTER','DEFEND_GENERAL'],instances={'ATTACK':2,'MUSTER':2,'HUNT_GENERAL':1,'FINISH':1,'DEFEND_GENERAL':1})
    elif island=='Fortress':
        n['OPENING']=_node(['BUILD_CASTLE','DEFEND_GENERAL','EXPAND','LOGISTICS','SCOUT'],['BUILD_CASTLE','DEFEND_GENERAL','EXPAND','LOGISTICS','SCOUT'],n['OPENING']['transitions'])
        n['CONTACT']=_node(['DEFEND_GENERAL','INTERCEPT','BUILD_CASTLE','CONSOLIDATE','LOGISTICS','ATTACK'],['DEFEND_GENERAL','INTERCEPT','CONSOLIDATE','LOGISTICS','ATTACK','BUILD_CASTLE'],n['CONTACT']['transitions'])
        n['BEHIND']=_node(['DEFEND_GENERAL','INTERCEPT','RECOVER','CONSOLIDATE','LOGISTICS','EXPAND'],transitions=n['BEHIND']['transitions'])
    elif island=='Hunter':
        n['OPENING']=_node(['SCOUT','EXPAND','HUNT_GENERAL','LOGISTICS','DEFEND_GENERAL'],['SCOUT','EXPAND','HUNT_GENERAL','LOGISTICS','DEFEND_GENERAL'],n['OPENING']['transitions'])
        n['CONTACT']=_node(['HUNT_GENERAL','ATTACK','INTERCEPT','MUSTER','LOGISTICS','DEFEND_GENERAL'],['HUNT_GENERAL','ATTACK','MUSTER','INTERCEPT','LOGISTICS','DEFEND_GENERAL'],n['CONTACT']['transitions'],{'HUNT_GENERAL':2,'ATTACK':2})
    elif island=='Economy':
        n['OPENING']=_node(['EXPAND','BUILD_CASTLE','SCOUT','LOGISTICS','PICK','DEFEND_GENERAL'],['EXPAND','BUILD_CASTLE','SCOUT','LOGISTICS','PICK','DEFEND_GENERAL'],n['OPENING']['transitions'])
        n['CONTACT']=_node(['EXPAND','DEFEND_GENERAL','LOGISTICS','ATTACK','MUSTER','PICK'],['EXPAND','DEFEND_GENERAL','LOGISTICS','MUSTER','ATTACK','PICK'],n['CONTACT']['transitions'])
    elif island=='Muster-Logistics':
        n['OPENING']=_node(['EXPAND','LOGISTICS','PICK','SCOUT','DEFEND_GENERAL'],['EXPAND','LOGISTICS','PICK','SCOUT','DEFEND_GENERAL'],n['OPENING']['transitions'])
        n['CONTACT']=_node(['MUSTER','LOGISTICS','PICK','ATTACK','DEFEND_GENERAL','INTERCEPT'],['MUSTER','LOGISTICS','ATTACK','PICK','INTERCEPT','DEFEND_GENERAL'],n['CONTACT']['transitions'],{'MUSTER':3,'ATTACK':2})
        n['LATE']=_node(['MUSTER','ATTACK','FINISH','HUNT_GENERAL','LOGISTICS','DEFEND_GENERAL'],instances={'MUSTER':3,'ATTACK':2,'FINISH':1,'HUNT_GENERAL':1,'LOGISTICS':1,'DEFEND_GENERAL':1})
    elif island=='Wildcard':
        rng=random.Random(505001)
        for q in n.values():
            mods=rng.sample(list(MODULES),rng.randint(4,8)); q.update(_node(mods,rng.sample(mods,len(mods)),q['transitions'],{m:rng.randint(1,2) for m in mods}))
    return canonical_graph(g)


def _module_strength(g:dict,module:str)->float:
    vals=[]
    for q in g['nodes'].values():
        if module not in q['modules']: continue
        rank=q['priority'].index(module); size=max(1,len(q['priority'])-1)
        base=1.0-rank/(size+1)
        vals.append(base*q['instances'].get(module,1))
    return sum(vals)/max(1,len(g['nodes']))


def compile_params(g:dict,base:dict)->dict:
    g=canonical_graph(g); p=canonical_values(base)
    if g['mode']=='baseline': return p
    active={m for q in g['nodes'].values() for m in q['modules']}
    attack=min(1.0,_module_strength(g,'ATTACK')+.35*_module_strength(g,'HUNT_GENERAL'))
    expand=min(1.0,_module_strength(g,'EXPAND'))
    search=min(1.0,_module_strength(g,'SCOUT')+.3*_module_strength(g,'HUNT_GENERAL'))
    logistics=min(1.0,_module_strength(g,'LOGISTICS')+.25*_module_strength(g,'CONSOLIDATE'))
    defense=min(1.0,_module_strength(g,'DEFEND_GENERAL')+.4*_module_strength(g,'INTERCEPT'))
    finish=min(1.0,_module_strength(g,'FINISH')+.3*_module_strength(g,'HUNT_GENERAL'))
    muster=max((q['instances'].get('MUSTER',0) for q in g['nodes'].values()),default=0)
    p['doomguard_enabled']='DEFEND_GENERAL' in active or 'INTERCEPT' in active
    p['war_share_contact']=.10+.48*attack; p['war_share_peace']=.02+.25*attack
    p['expansion_share_healthy']=.15+.42*expand; p['expansion_share_soft']=.25+.38*expand; p['expansion_share_severe']=.35+.42*expand
    p['expansion_share_precontact']=.15+.47*expand; p['precontact_expansion_until']=300 if expand>.55 else 150 if expand>.3 else -1
    p['search_share_unseen']=.05+.40*search; p['search_share_seen']=.01+.22*search
    p['free_share_peace']=.03+.30*logistics; p['free_share_war']=.05+.30*logistics
    p['general_reserve_base']=max(2,min(20,round(2+12*defense))); p['adjacent_reserve_base']=max(1,min(10,round(1+6*defense)))
    p['general_reserve_opp_divisor']=max(4,min(30,round(22-13*defense)))
    if 'BUILD_CASTLE' in active:
        p['castle1_target_turn']=max(100,min(220,round(190-55*_module_strength(g,'BUILD_CASTLE')))); p['castle2_target_turn']=max(p['castle1_target_turn']+50,min(360,round(330-70*_module_strength(g,'BUILD_CASTLE')))); p['late_castle_army_margin']=30
    else:
        p['castle1_target_turn']=260; p['castle2_target_turn']=420; p['late_castle_army_margin']=90
    if 'PICK' not in active and 'MUSTER' not in active:
        p['picker_enabled']=False
    else:
        p['picker_enabled']=True
        if 'PICK' not in active:
            p['edge_picker_threshold']=58; p['picker_min_efficiency']=7.5; p['picker_mature_turn']=350; p['picker_mature_land_pct']=60
        else:
            pick=_module_strength(g,'PICK'); p['edge_picker_threshold']=max(6,min(40,round(26-14*pick))); p['picker_min_efficiency']=max(.7,min(5.0,3.2-1.6*pick))
    if muster:
        p['muster_topology']='triple' if muster>=3 else 'dual' if muster==2 else 'single'; p['muster_start_turn']=max(180,min(520,round(420-150*_module_strength(g,'MUSTER')))); p['muster_launch_base']=max(45,min(150,round(120-45*_module_strength(g,'MUSTER'))))
    else:
        p['muster_topology']='single'; p['muster_start_turn']=650; p['muster_launch_base']=180
    p['muster_anchor_policy']='forward' if attack>.65 else 'central' if logistics>.6 else 'largest'
    p['chunk_transfer_policy']='split' if logistics>.65 and attack<.7 else 'full'
    p['logistics_route_policy']='interior' if logistics>=.4 else 'shortest'
    p['defense_policy']='reinforce_first' if defense>.72 else 'block_first'
    p['fallback_policy']='consolidate' if 'CONSOLIDATE' in active else 'aggressive' if attack>.65 else 'balanced'
    p['picker_start_policy']='efficiency' if logistics>.65 else 'mass' if attack>.65 else 'margin'
    p['late_finish_turn']=max(650,min(1050,round(1000-300*finish))); p['late_finish_base']=max(35,min(130,round(110-55*finish)))
    if 'RECOVER' in active:
        p['production_recover_gap']=max(4,min(18,round(14-6*_module_strength(g,'RECOVER')))); p['production_soft_gap']=min(p['production_soft_gap'],8)
    return canonical_values(p)


def graph_distance(a:dict,b:dict)->float:
    a=canonical_graph(a); b=canonical_graph(b)
    na,nb=set(a['nodes']),set(b['nodes']); node_d=1-len(na&nb)/max(1,len(na|nb))
    mods_a={(n,m) for n,q in a['nodes'].items() for m in q['modules']}; mods_b={(n,m) for n,q in b['nodes'].items() for m in q['modules']}
    mod_d=1-len(mods_a&mods_b)/max(1,len(mods_a|mods_b))
    ea={(n,t['condition'],t['target']) for n,q in a['nodes'].items() for t in q['transitions']}; eb={(n,t['condition'],t['target']) for n,q in b['nodes'].items() for t in q['transitions']}
    edge_d=1-len(ea&eb)/max(1,len(ea|eb))
    inst=sum(abs(q['instances'].get(m,1)-b['nodes'].get(n,{}).get('instances',{}).get(m,1)) for n,q in a['nodes'].items() for m in q['modules'])/max(1,2*len(mods_a))
    return min(1.0,.2*node_d+.45*mod_d+.25*edge_d+.10*inst)


def descriptor(genome:dict)->dict:
    g=canonical_graph(genome['graph']); p=compile_params(g,genome['params']); active={m for q in g['nodes'].values() for m in q['modules']}
    return {
        'nodes':min(4,len(g['nodes'])//2),
        'aggression':min(4,int(p['war_share_contact']*8)),
        'expansion':min(4,int(p['expansion_share_healthy']*8)),
        'search':min(4,int(p['search_share_unseen']*8)),
        'castle':1 if 'BUILD_CASTLE' in active else 0,
        'muster':{'single':1,'dual':2,'triple':3}.get(p['muster_topology'],1),
        'picker':1 if 'PICK' in active else 0,
        'defense':min(4,p['general_reserve_base']//4),
    }


def descriptor_key(genome:dict)->str:
    d=descriptor(genome)
    return '|'.join(f'{k}:{d[k]}' for k in sorted(d))
