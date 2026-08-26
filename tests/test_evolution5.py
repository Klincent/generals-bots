from __future__ import annotations
import json, random, tempfile
from pathlib import Path
import pytest
from tools.evolution4.genome import founder_x0, founder_y0
from tools.evolution5.graph import baseline_graph, validate_graph, graph_hash, graph_distance, specialize_graph, descriptor_key, ISLANDS
from tools.evolution5.genome import canonical_genome, genome_id, effective_params, save_genome, load_genome, runtime_graph_spec
from tools.evolution5.mutate import module_mutation, graph_rewrite, strategy_bundle, crossover_genomes, random_immigrant
from tools.evolution5.archive import update_archive
from tools.evolution5.league import consider


def base(): return {'graph':baseline_graph(),'params':founder_x0()}

def test_serialization_and_baseline_passthrough():
    g=canonical_genome(base()); assert genome_id(g)==genome_id(json.loads(json.dumps(g))); assert effective_params(g)==founder_x0(); assert graph_hash(g['graph'])==graph_hash(json.loads(json.dumps(g['graph']))); assert 'OPENING~' in runtime_graph_spec(g['graph'])

def test_graph_validation_rejects_invalid_target():
    g=baseline_graph(); g['nodes']['OPENING']['transitions'][0]['target']='NOPE'
    with pytest.raises(ValueError): validate_graph(g)

def test_module_and_graph_mutation_change_architecture():
    rng=random.Random(1); g=base(); m=module_mutation(g,rng); r=graph_rewrite(g,rng,.4); assert graph_distance(g['graph'],m['graph'])>0; assert graph_distance(g['graph'],r['graph'])>=.10

def test_strategy_bundle_is_coordinated():
    g=strategy_bundle(base(),random.Random(2),'rush'); p=effective_params(g); assert g['graph']['mode']=='evolved'; assert p['war_share_contact']>=.35; assert p['late_finish_turn']<=900

def test_random_immigrants_independent():
    ids={genome_id(random_immigrant(founder_x0(),random.Random(i),None)) for i in range(12)}; assert len(ids)>=11

def test_crossover_combines_graphs():
    a={'graph':specialize_graph('Rush'),'params':founder_x0()}; b={'graph':specialize_graph('Fortress'),'params':founder_y0()}; c=crossover_genomes(a,b,random.Random(3)); validate_graph(c['graph']); assert c['graph']['mode']=='evolved'

def test_islands_have_distinct_descriptors():
    keys={descriptor_key({'graph':specialize_graph(i),'params':founder_x0()}) for i in ISLANDS}; assert len(keys)>=6

def test_archive_preserves_distinct_niches():
    genomes={}; rows=[]
    for i,name in enumerate(('Rush','Fortress','Hunter')):
        g={'graph':specialize_graph(name),'params':founder_x0()}; gid=genome_id(g); genomes[gid]=g; rows.append({'genome_id':gid,'fitness':{'aggregate':.5+i*.01,'raw_win_rate':.4,'minimum':.3}})
    state={}; changed=update_archive(state,rows,lambda gid:genomes[gid],0); assert changed>=2; assert len(state['map_elites'])>=2

def test_league_preserves_protected_and_admits_coverage():
    x=base(); xid=genome_id(x); r={'graph':specialize_graph('Rush'),'params':founder_x0()}; rid=genome_id(r); genomes={xid:x,rid:r}; state={'league':[{'genome_id':xid,'protected':True,'label':'X0','fresh_score':.5,'minimum':.3,'archetypes':{'a':.4}}]}; cand={'genome_id':rid,'fresh':{'fitness':{'aggregate':.62,'minimum':.35},'aggregate':{'raw_win_rate':.58,'errors':0,'illegal_actions':0},'archetypes':{'a':.7}},'head_to_head':{xid:{'score':.65}}}; changes=consider(state,[cand],lambda gid:genomes[gid],1); assert changes; assert any(x['genome_id']==xid for x in state['league']); assert any(x['genome_id']==rid for x in state['league'])

def test_genome_file_roundtrip():
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/'g.json'; gid=save_genome(p,base(),{'x':1}); q=load_genome(p); assert q['genome_id']==gid; assert q['genome']==canonical_genome(base())
