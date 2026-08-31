import copy
import random

from tools.evolution4.schema import defaults
from tools.evolution5.graph import baseline_graph
from tools.evolution5.genome import canonical_genome
from tools.evolution5_lineage.policy import (
    HARD_GATES, DOMINANCE_TARGETS, dominance_pass, gate_pass,
    opponent_mix, phase, promotion_key, weighted_lineage_score,
)
from tools.evolution5_lineage.orchestrator_pool import _pair_distribution, _failure_bias
from tools.evolution5_lineage.orchestrator_breeding import _merge_entries, _directed_numeric_child, POOL_SIZE


def q(win, score=None, errors=0, illegal=0):
    return {
        'raw_win_rate': win,
        'score': win if score is None else score,
        'errors': errors,
        'illegal_actions': illegal,
    }


def test_phase_and_reference_decay_to_zero():
    assert phase(0) == 'early'
    assert opponent_mix(0) == {'reference': .50, 'lineage': .50}
    assert opponent_mix(3) == {'reference': .25, 'lineage': .75}
    assert opponent_mix(6) == {'reference': .10, 'lineage': .90}
    assert phase(9) == 'mature'
    assert opponent_mix(9) == {'reference': 0.0, 'lineage': 1.0}


def test_hard_gates_are_55_60_65_and_available_ancestry_only():
    assert HARD_GATES == {1: .55, 2: .60, 3: .65}
    assert gate_pass({1: q(.55)})
    assert gate_pass({1: q(.55), 2: q(.60)})
    assert gate_pass({1: q(.55), 2: q(.60), 3: q(.65)})
    assert not gate_pass({1: q(.54)})
    assert not gate_pass({1: q(.70), 2: q(.59)})
    assert not gate_pass({1: q(.70, errors=1)})
    assert not gate_pass({1: q(.70, illegal=1)})


def test_dominance_requires_full_60_70_80_ancestry():
    assert DOMINANCE_TARGETS == {1: .60, 2: .70, 3: .80}
    assert not dominance_pass({1: q(.90)})
    assert not dominance_pass({1: q(.90), 2: q(.90)})
    assert dominance_pass({1: q(.60), 2: q(.70), 3: q(.80)})
    assert not dominance_pass({1: q(.59), 2: q(.90), 3: q(.90)})
    assert not dominance_pass({1: q(.90), 2: q(.69), 3: q(.90)})
    assert not dominance_pass({1: q(.90), 2: q(.90), 3: q(.79)})


def test_lineage_weighting_is_parent_heaviest():
    m = {1: q(.80), 2: q(.60), 3: q(.40)}
    assert abs(weighted_lineage_score(m) - (.5 * .8 + .3 * .6 + .2 * .4)) < 1e-12


def test_promotion_gate_beats_pretty_reference_score():
    passed = {
        'matchups': {1: q(.56), 2: q(.61), 3: q(.66)},
        'reference_score': .10,
        'novelty': .10,
    }
    failed = {
        'matchups': {1: q(.90), 2: q(.90), 3: q(.64)},
        'reference_score': 1.0,
        'novelty': 1.0,
    }
    assert promotion_key(passed) > promotion_key(failed)


def test_previous_generation_main_champion_gets_half_the_deep_games():
    assert _pair_distribution(48, 4) == [24, 8, 8, 8]
    assert _pair_distribution(32, 3) == [16, 8, 8]
    assert _pair_distribution(24, 1) == [24]


def test_mutation_reacts_to_how_challenger_loses():
    assert _failure_bias({'finalists': [{'matchups': {1: q(.50)}}]}) == 'pressure'
    assert _failure_bias({'finalists': [{'matchups': {1: q(.60), 2: q(.55)}}]}) == 'anti_overfit'
    assert _failure_bias({'finalists': [{'matchups': {1: q(.60), 2: q(.65), 3: q(.70)}}]}) == 'normal'


def test_persistent_breeding_keeps_best_near_winners_across_attempts():
    incoming = [
        {
            'genome_id': f'g{i}',
            'generation': 1,
            'attempt': i,
            'rates': {'1': .48 + i / 1000.0},
            'weighted_lineage_score': .48 + i / 1000.0,
        }
        for i in range(24)
    ]
    pool = _merge_entries([], incoming, current='g23', generation=1)
    assert len(pool) == POOL_SIZE
    assert all(row['genome_id'] != 'g23' for row in pool)
    assert pool[0]['rates']['1'] > pool[-1]['rates']['1']
    assert 'g22' in {row['genome_id'] for row in pool}


def test_directed_numeric_probe_extrapolates_successful_direction():
    champion = canonical_genome({'graph': baseline_graph(), 'params': defaults()})
    elite = copy.deepcopy(champion)
    elite['params']['war_share_contact'] = champion['params']['war_share_contact'] + .10
    elite = canonical_genome(elite)
    child = _directed_numeric_child(champion, elite, random.Random(7), .50)
    assert child['params']['war_share_contact'] > elite['params']['war_share_contact']
    assert child['params']['war_share_contact'] <= .60
