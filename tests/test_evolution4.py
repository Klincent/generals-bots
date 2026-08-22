from __future__ import annotations
import random
from pathlib import Path
from tools.evolution4.genome import founder_x0, founder_y0, genome_id, canonical_json, validate_genome
from tools.evolution4.mutate import mutate
from tools.evolution4.crossover import crossover
from tools.evolution4.diversity import genome_distance
from tools.evolution4.selection import non_dominated_sort, select
from tools.evolution4.state import validate_transition
from tools.evolution4.freeze import freeze_header
from tools.evolution4.template_transform import HEADER

def test_canonical_hash_stable():
    x=founder_x0(); assert genome_id(x)==genome_id(dict(reversed(list(x.items())))); assert canonical_json(x)==canonical_json(dict(x))

def test_y0_exact_gene_delta():
    x=founder_x0(); y=founder_y0(); diff={k for k in x if x[k]!=y[k]}; assert diff=={'precontact_expansion_until','expansion_share_precontact'}; assert y['precontact_expansion_until']==250; assert y['expansion_share_precontact']==0.40

def test_mutation_bounds_and_validity():
    rng=random.Random(1); v=founder_x0()
    for _ in range(200): v=mutate(v,rng,exploratory=(_%7==0)); validate_genome(v)

def test_crossover_valid():
    rng=random.Random(2); c=crossover(founder_x0(),founder_y0(),rng); validate_genome(c); assert genome_distance(c,founder_x0())>=0

def test_duplicate_identity():
    assert genome_id(founder_x0())==genome_id(founder_x0()); assert genome_id(founder_x0())!=genome_id(founder_y0())

def test_pareto_selection():
    items=[
      {'genome_id':'a','fitness':{'aggregate':.80,'minimum':.10,'hof':.5,'color_imbalance':.02}},
      {'genome_id':'b','fitness':{'aggregate':.72,'minimum':.55,'hof':.5,'color_imbalance':.02}},
      {'genome_id':'c','fitness':{'aggregate':.60,'minimum':.30,'hof':.3,'color_imbalance':.10}},]
    fronts=non_dominated_sort(items); assert {'a','b'}=={x['genome_id'] for x in fronts[0]}; assert len(select(items,2))==2

def test_state_transition_validation():
    a={'phase':'bootstrap','generation':0}; b={'phase':'exploration','generation':0}; assert validate_transition(a,b)
    a={'phase':'exploration','generation':11}; b={'phase':'exploitation','generation':12}; assert validate_transition(a,b)
    a={'phase':'exploitation','generation':29}; b={'phase':'final','generation':30}; assert validate_transition(a,b)

def test_freeze_render_consistency(tmp_path:Path):
    src=tmp_path/'h.hpp'; out=tmp_path/'f.hpp'; src.write_text(HEADER); v=founder_y0(); freeze_header(src,v,out); text=out.read_text(); assert 'precontact_expansion_until=250' in text; assert 'expansion_share_precontact=.4' in text or 'expansion_share_precontact=0.4' in text
