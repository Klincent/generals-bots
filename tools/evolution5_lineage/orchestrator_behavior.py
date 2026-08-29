from __future__ import annotations

import copy
import random

from . import orchestrator as b
from . import orchestrator_pool as p
from . import orchestrator_focus as f
from tools.evolution5.genome import canonical_genome, genome_id, save_genome
from tools.evolution5.graph import repair_graph
from tools.evolution5.mutate import crossover_genomes, graph_rewrite, strategy_bundle


FAMILIES = (
    'blitz_muster',
    'anti_rush',
    'edge_harvest',
    'castle_counter',
    'hunter_pressure',
    'adaptive_switch',
)

# Search-budget guard: after this many consecutive behavior-search misses, rotate
# the family recipe instead of repeating the same local neighborhood forever.
NO_PROGRESS_BUDGET = 4


def _prioritize(graph: dict, node: str, ordered: list[str], instances: dict[str, int] | None = None) -> None:
    if node not in graph['nodes']:
        return
    q = graph['nodes'][node]
    for module in reversed(ordered):
        if module not in q['modules']:
            q['modules'].insert(0, module)
            q['instances'][module] = 1
    q['priority'] = ordered + [m for m in q['modules'] if m not in ordered]
    if instances:
        for module, count in instances.items():
            if module in q['modules']:
                q['instances'][module] = max(1, min(3, int(count)))


def _set_transition(graph: dict, node: str, condition: str, target: str) -> None:
    if node not in graph['nodes'] or target not in graph['nodes']:
        return
    q = graph['nodes'][node]
    q['transitions'] = [t for t in q['transitions'] if t['condition'] != condition]
    q['transitions'].insert(0, {'condition': condition, 'target': target})


def behavior_variant(parent: dict, rng: random.Random, family: str, intensity: int) -> dict:
    """Create a materially different tactical policy, not just a few random gene nudges."""
    base = canonical_genome(parent)

    if family == 'blitz_muster':
        g = strategy_bundle(base, rng, 'muster')
        graph = copy.deepcopy(g['graph'])
        _prioritize(graph, 'CONTACT', ['MUSTER', 'ATTACK', 'LOGISTICS', 'INTERCEPT'], {'MUSTER': 3, 'ATTACK': 2})
        _prioritize(graph, 'LATE', ['MUSTER', 'ATTACK', 'FINISH', 'HUNT_GENERAL'], {'MUSTER': 3, 'ATTACK': 2})
        pms = dict(g['params'])
        pms.update({
            'muster_start_turn': 165 + 10 * intensity,
            'muster_launch_base': 48 + 4 * intensity,
            'muster_topology': 'triple',
            'war_share_contact': 0.50 + 0.02 * intensity,
            'free_share_war': 0.34,
            'picker_enabled': True,
        })

    elif family == 'anti_rush':
        g = strategy_bundle(base, rng, 'defense')
        graph = copy.deepcopy(g['graph'])
        _prioritize(graph, 'CONTACT', ['DEFEND_GENERAL', 'INTERCEPT', 'MUSTER', 'ATTACK', 'LOGISTICS'], {'INTERCEPT': 2, 'MUSTER': 2})
        _prioritize(graph, 'BEHIND', ['DEFEND_GENERAL', 'INTERCEPT', 'RECOVER', 'MUSTER', 'LOGISTICS'], {'INTERCEPT': 2})
        _set_transition(graph, 'OPENING', 'threat', 'CONTACT')
        pms = dict(g['params'])
        pms.update({
            'doomguard_enabled': True,
            'general_reserve_base': 10 + intensity,
            'adjacent_reserve_base': 5 + intensity // 2,
            'war_share_contact': 0.36 + 0.02 * intensity,
            'muster_start_turn': 185 + 10 * intensity,
            'muster_launch_base': 58 + 4 * intensity,
        })

    elif family == 'edge_harvest':
        g = strategy_bundle(base, rng, 'muster')
        graph = copy.deepcopy(g['graph'])
        _prioritize(graph, 'OPENING', ['EXPAND', 'LOGISTICS', 'PICK', 'SCOUT', 'DEFEND_GENERAL'])
        _prioritize(graph, 'CONTACT', ['LOGISTICS', 'PICK', 'MUSTER', 'ATTACK', 'INTERCEPT'], {'MUSTER': 3})
        _prioritize(graph, 'LATE', ['MUSTER', 'LOGISTICS', 'ATTACK', 'FINISH'], {'MUSTER': 3, 'ATTACK': 2})
        pms = dict(g['params'])
        pms.update({
            'picker_enabled': True,
            'edge_picker_threshold': 10 + 2 * intensity,
            'picker_min_efficiency': 1.0 + 0.25 * intensity,
            'picker_mature_turn': 210 + 15 * intensity,
            'picker_mature_land_pct': 45 + 3 * intensity,
            'muster_start_turn': 205 + 10 * intensity,
            'muster_launch_base': 55 + 5 * intensity,
            'free_share_war': 0.35,
        })

    elif family == 'castle_counter':
        g = strategy_bundle(base, rng, 'fortress')
        graph = copy.deepcopy(g['graph'])
        _prioritize(graph, 'OPENING', ['BUILD_CASTLE', 'EXPAND', 'DEFEND_GENERAL', 'LOGISTICS'])
        _prioritize(graph, 'CONTACT', ['INTERCEPT', 'DEFEND_GENERAL', 'MUSTER', 'ATTACK', 'CONSOLIDATE'], {'MUSTER': 2, 'ATTACK': 2})
        pms = dict(g['params'])
        pms.update({
            'castle1_target_turn': 130 + 10 * intensity,
            'castle2_target_turn': 220 + 10 * intensity,
            'general_reserve_base': 8 + intensity,
            'adjacent_reserve_base': 4 + intensity // 2,
            'muster_start_turn': 220 + 10 * intensity,
            'war_share_contact': 0.40 + 0.02 * intensity,
        })

    elif family == 'hunter_pressure':
        g = strategy_bundle(base, rng, 'hunter')
        graph = copy.deepcopy(g['graph'])
        _prioritize(graph, 'CONTACT', ['HUNT_GENERAL', 'ATTACK', 'MUSTER', 'SCOUT', 'INTERCEPT'], {'HUNT_GENERAL': 2, 'ATTACK': 2, 'MUSTER': 2})
        _prioritize(graph, 'LATE', ['HUNT_GENERAL', 'FINISH', 'ATTACK', 'MUSTER'], {'ATTACK': 2})
        pms = dict(g['params'])
        pms.update({
            'search_share_unseen': 0.42 + 0.02 * intensity,
            'search_share_seen': 0.20 + 0.01 * intensity,
            'war_share_contact': 0.52 + 0.01 * intensity,
            'muster_start_turn': 205 + 10 * intensity,
            'late_finish_turn': 670 + 10 * intensity,
        })

    elif family == 'adaptive_switch':
        g = strategy_bundle(base, rng, 'adaptive')
        graph = copy.deepcopy(g['graph'])
        _prioritize(graph, 'OPENING', ['EXPAND', 'SCOUT', 'LOGISTICS', 'DEFEND_GENERAL'])
        _prioritize(graph, 'CONTACT', ['INTERCEPT', 'MUSTER', 'ATTACK', 'LOGISTICS', 'DEFEND_GENERAL'], {'MUSTER': 2, 'ATTACK': 2})
        _prioritize(graph, 'BEHIND', ['DEFEND_GENERAL', 'INTERCEPT', 'RECOVER', 'LOGISTICS', 'MUSTER'])
        _prioritize(graph, 'LATE', ['MUSTER', 'ATTACK', 'HUNT_GENERAL', 'FINISH'], {'MUSTER': 3, 'ATTACK': 2})
        _set_transition(graph, 'OPENING', 'threat', 'CONTACT')
        _set_transition(graph, 'CONTACT', 'behind', 'BEHIND')
        _set_transition(graph, 'BEHIND', 'ahead', 'CONTACT')
        pms = dict(g['params'])
        pms.update({
            'doomguard_enabled': True,
            'general_reserve_base': 7 + intensity,
            'adjacent_reserve_base': 4,
            'muster_start_turn': 200 + 10 * intensity,
            'muster_launch_base': 58 + 4 * intensity,
            'war_share_contact': 0.44 + 0.02 * intensity,
            'picker_enabled': True,
        })
    else:
        raise ValueError(family)

    g['graph'] = repair_graph(graph)
    g['params'] = pms
    return canonical_genome(g)


def _recent_behavior_failures(state: dict) -> int:
    streak = 0
    for row in reversed(state.get('attempt_history', [])):
        if row.get('promoted') or row.get('promotion_gate_passed'):
            break
        streak += 1
    return streak


def create_challengers_behavior(state: dict):
    generation = int(state['lineage_generation'])
    attempt = int(state['promotion_attempt']) + 1
    current = state['current_champion']
    parent = b.genome(current)
    rng = random.Random(9917000 + generation * 1009 + attempt * 131)

    # Every NO_PROGRESS_BUDGET misses rotate intensity/order so the same behavior
    # family does not get replayed forever.
    failures = _recent_behavior_failures(state)
    epoch = failures // NO_PROGRESS_BUDGET
    families = list(FAMILIES)
    rng.shuffle(families)
    families = families[epoch % len(families):] + families[:epoch % len(families)]

    known = {path.name[:-5] for path in b.GENOMES.glob('*.json')}
    ids, created = [], []
    counts = {family: 0 for family in FAMILIES}
    counts['crossover'] = 0
    counts['explore'] = 0
    archetypes: list[tuple[str, dict]] = []

    # 48 explicit strategic policies: eight variants per family.
    for slot in range(48):
        family = families[slot % len(families)]
        intensity = (slot // len(families) + epoch) % 5
        child = behavior_variant(parent, rng, family, intensity)
        for retry in range(20):
            gid = genome_id(child)
            if gid not in known:
                break
            child = graph_rewrite(child, rng, 0.22 + 0.02 * (retry % 4))
        else:
            raise RuntimeError('unable to create unique behavior challenger')
        known.add(gid)
        path = b.GENOMES / f'{gid}.json'
        save_genome(path, child, {
            'lineage_generation_target': generation + 1,
            'promotion_attempt': attempt,
            'lineage_parent': current,
            'kind': 'behavior',
            'behavior_family': family,
            'behavior_epoch': epoch,
            'behavior_intensity': intensity,
        })
        ids.append(gid); created.append(path); counts[family] += 1
        archetypes.append((family, child))

    # 8 cross-family hybrids combine genuinely different tactical policies.
    for slot in range(8):
        a_name, a_genome = archetypes[(slot * 5) % len(archetypes)]
        b_name, b_genome = archetypes[(slot * 7 + 3) % len(archetypes)]
        child = crossover_genomes(a_genome, b_genome, rng)
        for retry in range(20):
            gid = genome_id(child)
            if gid not in known:
                break
            child = graph_rewrite(child, rng, 0.25)
        else:
            raise RuntimeError('unable to create unique behavior crossover')
        known.add(gid)
        path = b.GENOMES / f'{gid}.json'
        save_genome(path, child, {
            'lineage_generation_target': generation + 1,
            'promotion_attempt': attempt,
            'lineage_parent': current,
            'kind': 'behavior_crossover',
            'behavior_family': f'{a_name}+{b_name}',
            'behavior_epoch': epoch,
        })
        ids.append(gid); created.append(path); counts['crossover'] += 1

    # 8 broader graph explorations retain escape routes from our hand-built ideas.
    for slot in range(8):
        family, seed = archetypes[(slot * 11 + 1) % len(archetypes)]
        child = graph_rewrite(seed, rng, 0.32 + 0.02 * (slot % 3))
        for retry in range(20):
            gid = genome_id(child)
            if gid not in known:
                break
            child = graph_rewrite(child, rng, 0.35)
        else:
            raise RuntimeError('unable to create unique behavior explorer')
        known.add(gid)
        path = b.GENOMES / f'{gid}.json'
        save_genome(path, child, {
            'lineage_generation_target': generation + 1,
            'promotion_attempt': attempt,
            'lineage_parent': current,
            'kind': 'behavior_explore',
            'behavior_family': family,
            'behavior_epoch': epoch,
        })
        ids.append(gid); created.append(path); counts['explore'] += 1

    f.phase_heartbeat(
        state,
        'behavior_population_created',
        challengers=len(ids),
        behavior_epoch=epoch,
        no_progress_budget=NO_PROGRESS_BUDGET,
        behavior_counts=counts,
    )
    return ids, created, counts


def main() -> None:
    # Preserve the durable persistence and cheap staged G1/G2/G3 funnel from focus,
    # but replace local mutation with explicit tactical behavior search.
    b.persist = f.persist_resilient
    b.opponent_mix = f.focus_opponent_mix
    p._phase_heartbeat = f.phase_heartbeat
    b.screen = p.screen_parallel
    b.create_challengers = create_challengers_behavior
    b.deep_lineage = f.deep_lineage_focus
    b.transaction = p.transaction_hardened
    b.main()


if __name__ == '__main__':
    main()
