from __future__ import annotations
import copy, random
from pathlib import Path
from tools.evolution4.genome import founder_x0, founder_y0, genome_id, canonical_json, validate_genome
from tools.evolution4.mutate import mutate, structural_jump
from tools.evolution4.crossover import crossover
from tools.evolution4.diversity import genome_distance, structural_distance, cohort_novelty
from tools.evolution4.selection import non_dominated_sort, select
from tools.evolution4.state import validate_transition
from tools.evolution4.freeze import freeze_header
from tools.evolution4.schema import load_schema
from tools.evolution4.selection_memory import x0_stage1_slots, x0_game_share
from tools.evolution4.genome_memory import candidate_allowed, may_retest_existing, reserved_newborn_ids, mark_infra_unresolved, migrate_state


def test_canonical_hash_stable():
    x=founder_x0(); assert genome_id(x)==genome_id(dict(reversed(list(x.items())))); assert canonical_json(x)==canonical_json(dict(x))


def test_y0_exact_gene_delta():
    x=founder_x0(); y=founder_y0(); diff={k for k in x if x[k]!=y[k]}; assert diff=={'precontact_expansion_until','expansion_share_precontact'}; assert y['precontact_expansion_until']==250; assert y['expansion_share_precontact']==0.40


def test_mutation_bounds_and_validity():
    rng=random.Random(1); v=founder_x0(); structural=0
    data,_=load_schema(); enum_names=[g['name'] for g in data['genes'] if g['type']=='enum']
    for i in range(200):
        before=dict(v); v=mutate(v,rng,exploratory=(i%7==0)); validate_genome(v)
        structural+=any(v[n]!=before[n] for n in enum_names)
    assert structural>0


def test_macro_jump_guarantees_multiple_structural_changes():
    rng=random.Random(77); x=founder_x0(); y=structural_jump(x,rng,2,4); validate_genome(y)
    assert structural_distance(x,y)>=2/7


def test_crossover_valid():
    rng=random.Random(2); c=crossover(founder_x0(),founder_y0(),rng); validate_genome(c); assert genome_distance(c,founder_x0())>=0


def test_duplicate_identity():
    assert genome_id(founder_x0())==genome_id(founder_x0()); assert genome_id(founder_x0())!=genome_id(founder_y0())


def test_pareto_selection_and_novelty():
    items=[
      {'genome_id':'a','fitness':{'aggregate':.80,'minimum':.10,'novelty':.0,'hof':.5,'color_imbalance':.02}},
      {'genome_id':'b','fitness':{'aggregate':.72,'minimum':.55,'novelty':.1,'hof':.5,'color_imbalance':.02}},
      {'genome_id':'c','fitness':{'aggregate':.60,'minimum':.30,'novelty':.9,'hof':.3,'color_imbalance':.10}},]
    fronts=non_dominated_sort(items); assert len(fronts)>=1; assert len(select(items,2))==2
    n=cohort_novelty([founder_x0(),founder_y0()]); assert len(n)==2


def test_x0_slot_weight_is_dynamic_and_near_30_percent():
    assert x0_stage1_slots(7)==3
    for specialized in range(4,11):
        slots=x0_stage1_slots(specialized); share=x0_game_share(specialized,slots)
        assert abs(share-.30)<=.04


def test_x0_matchup_result_affects_stage1_selection():
    items=[
      {'genome_id':'weak-x0','fitness':{'aggregate':.70,'minimum':.50,'x0_score':.40,'novelty':.2,'hof':0.0,'color_imbalance':.05}},
      {'genome_id':'strong-x0','fitness':{'aggregate':.70,'minimum':.50,'x0_score':.75,'novelty':.2,'hof':0.0,'color_imbalance':.05}},]
    assert select(items,1)[0]['genome_id']=='strong-x0'


def test_catastrophic_x0_cannot_be_rescued_by_novelty_when_safe_choice_exists():
    items=[
      {'genome_id':'novel-but-crushed','fitness':{'aggregate':.90,'minimum':.10,'x0_score':.125,'novelty':1.0,'hof':0.0,'color_imbalance':.01}},
      {'genome_id':'safe','fitness':{'aggregate':.68,'minimum':.45,'x0_score':.50,'novelty':.0,'hof':0.0,'color_imbalance':.08}},]
    assert select(items,1)[0]['genome_id']=='safe'


def test_exact_dead_hash_is_permanent_breeding_tombstone_but_elite_may_retest():
    s={'tested_genomes':{'dead-hash':{'status':'dead'},'elite-hash':{'status':'elite'}},'current_population':[],'breeding_elites':['elite-hash'],'hall_of_fame':[],'official_champion_genome_id':None}
    assert not may_retest_existing(s,'dead-hash')
    assert may_retest_existing(s,'elite-hash')
    assert not candidate_allowed(s,'dead-hash',set())
    assert 'dead-hash' in reserved_newborn_ids(s)
    assert 'elite-hash' in reserved_newborn_ids(s)


def test_infra_unresolved_is_not_evolutionary_death():
    s={'tested_genomes':{},'current_population':[],'breeding_elites':[],'hall_of_fame':[],'official_champion_genome_id':None}
    mark_infra_unresolved(s,'infra-hash',5,'driver crash')
    assert s['tested_genomes']['infra-hash']['status']=='infra_unresolved'
    assert may_retest_existing(s,'infra-hash')
    assert 'infra-hash' not in reserved_newborn_ids(s)


def test_memory_migration_is_idempotent():
    s={'tested_genomes':{'elite-hash':{'status':'survivor'},'dead-hash':{'status':'dead','last_tested_generation':3},'champ-hash':{'status':'survivor'}},'current_population':['elite-hash'],'breeding_elites':['elite-hash'],'hall_of_fame':[{'genome_id':'champ-hash'}],'official_champion_genome_id':'champ-hash'}
    migrate_state(s); once=copy.deepcopy(s); migrate_state(s)
    assert s==once
    assert s['tested_genomes']['elite-hash']['status']=='elite'
    assert s['tested_genomes']['dead-hash']['status']=='dead'
    assert s['tested_genomes']['champ-hash']['status']=='champion'


def test_state_transition_validation():
    a={'phase':'bootstrap','generation':0}; b={'phase':'exploration','generation':0}; assert validate_transition(a,b)
    a={'phase':'exploration','generation':19}; b={'phase':'exploitation','generation':20}; assert validate_transition(a,b)
    a={'phase':'exploitation','generation':59}; b={'phase':'final','generation':60}; assert validate_transition(a,b)


def test_structural_catalog_is_real_and_wide():
    data,_=load_schema(); enums={g['name']:g for g in data['genes'] if g['type']=='enum'}
    assert len(enums)==7
    assert {'single','dual','triple'} <= set(enums['muster_topology']['allowed'])
    assert {'largest','forward','central'} <= set(enums['muster_anchor_policy']['allowed'])
    assert {'full','split'} <= set(enums['chunk_transfer_policy']['allowed'])
    assert {'interior','shortest'} <= set(enums['logistics_route_policy']['allowed'])
    assert {'block_first','reinforce_first'} <= set(enums['defense_policy']['allowed'])
    assert {'balanced','aggressive','consolidate'} <= set(enums['fallback_policy']['allowed'])
    assert {'margin','mass','efficiency','speed'} <= set(enums['picker_start_policy']['allowed'])


def test_freeze_render_consistency(tmp_path:Path):
    data,_=load_schema(); src=tmp_path/'h.hpp'; out=tmp_path/'f.hpp'; lines=['struct GenomeConfig {']
    for g in data['genes']:
        v=g['default']; t=g['type']
        if t=='bool': ctype='bool'; lit='true' if v else 'false'
        elif t=='int': ctype='int'; lit=str(v)
        elif t=='float': ctype='double'; lit=str(v)
        else: ctype='std::string'; lit='"'+str(v)+'"'
        lines.append(f' {ctype} {g["name"]}={lit};')
    lines.append('};'); src.write_text('\n'.join(lines)+'\n')
    v=founder_y0(); freeze_header(src,v,out); text=out.read_text(); assert 'precontact_expansion_until=250' in text; assert 'expansion_share_precontact=.4' in text or 'expansion_share_precontact=0.4' in text; assert 'muster_topology="single"' in text
