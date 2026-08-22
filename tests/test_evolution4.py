from __future__ import annotations
import random
from pathlib import Path
from tools.evolution4.genome import founder_x0, founder_y0, genome_id, canonical_json, validate_genome
from tools.evolution4.mutate import mutate, structural_jump
from tools.evolution4.crossover import crossover
from tools.evolution4.diversity import genome_distance, structural_distance, cohort_novelty
from tools.evolution4.selection import non_dominated_sort, select
from tools.evolution4.state import validate_transition
from tools.evolution4.freeze import freeze_header
from tools.evolution4.schema import load_schema


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
