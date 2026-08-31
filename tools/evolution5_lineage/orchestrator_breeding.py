from __future__ import annotations

import copy
import json
import random
from collections import Counter

from . import orchestrator as b
from . import orchestrator_pool as p
from . import orchestrator_behavior as behavior
from . import orchestrator_cmaes as cma
from .policy import HARD_GATES
from tools.evolution4.schema import load_schema
from tools.evolution5.genome import canonical_genome, genome_id, save_genome
from tools.evolution5.mutate import crossover_genomes, graph_rewrite


POOL_SIZE = 16
MIN_POOL_G1 = 0.48
_ORIGINAL_TRANSACTION_HARDENED = p.transaction_hardened


def _entry_key(entry: dict) -> tuple:
    rates = entry.get('rates', {})
    g1 = float(rates.get('1', 0.0))
    g2 = rates.get('2')
    g3 = rates.get('3')
    gate_depth = 0
    for distance in (1, 2, 3):
        value = rates.get(str(distance))
        if value is not None and float(value) >= HARD_GATES[distance]:
            gate_depth += 1
        else:
            break
    return (
        gate_depth,
        1 if g3 is not None else 0,
        float(g3 or 0.0),
        1 if g2 is not None else 0,
        float(g2 or 0.0),
        g1,
        float(entry.get('weighted_lineage_score', 0.0)),
        float(entry.get('selection_score', 0.0)),
        float(entry.get('novelty', 0.0)),
        int(entry.get('attempt', 0)),
    )


def _merge_entries(existing: list[dict], incoming: list[dict], current: str | None, generation: int) -> list[dict]:
    by_gid: dict[str, dict] = {}
    for entry in [*existing, *incoming]:
        gid = entry.get('genome_id')
        if not gid or gid == current or int(entry.get('generation', generation)) != generation:
            continue
        old = by_gid.get(gid)
        if old is None or _entry_key(entry) > _entry_key(old):
            by_gid[gid] = dict(entry)
    rows = sorted(by_gid.values(), key=_entry_key, reverse=True)
    return rows[:POOL_SIZE]


def _history_entries(state: dict) -> list[dict]:
    generation = int(state.get('lineage_generation', 0))
    current = state.get('current_champion')
    rows = []
    for row in state.get('attempt_history', []):
        if int(row.get('generation_before', -1)) != generation:
            continue
        gid = row.get('best_challenger')
        g1 = float(row.get('best_vs_parent_win_rate', 0.0))
        if not gid or gid == current or g1 < MIN_POOL_G1:
            continue
        if not (b.GENOMES / f'{gid}.json').exists():
            continue
        rows.append({
            'genome_id': gid,
            'generation': generation,
            'attempt': int(row.get('attempt', 0)),
            'source': 'attempt_history',
            'rates': {'1': g1},
            'weighted_lineage_score': g1,
            'selection_score': 0.0,
            'novelty': 0.0,
        })
    return rows


def _finalist_entry(row: dict, generation: int, attempt: int) -> dict | None:
    matchups = row.get('matchups') or {}
    if 1 not in matchups:
        return None
    rates = {
        str(distance): float(summary.get('raw_win_rate', 0.0))
        for distance, summary in matchups.items()
        if distance in (1, 2, 3)
    }
    if float(rates.get('1', 0.0)) < MIN_POOL_G1:
        return None
    return {
        'genome_id': row['genome_id'],
        'generation': generation,
        'attempt': attempt,
        'source': 'deep_finalist',
        'rates': rates,
        'weighted_lineage_score': float(row.get('weighted_lineage_score', 0.0)),
        'selection_score': float(row.get('selection_score', 0.0)),
        'novelty': float(row.get('novelty', 0.0)),
        'evaluation_complete': bool(row.get('evaluation_complete', False)),
    }


def ensure_breeding_pool(state: dict) -> list[dict]:
    generation = int(state.get('lineage_generation', 0))
    current = state.get('current_champion')
    existing = state.get('breeding_pool', []) if int(state.get('breeding_pool_generation', generation)) == generation else []
    valid_existing = [
        row for row in existing
        if row.get('genome_id') and (b.GENOMES / f"{row['genome_id']}.json").exists()
    ]
    pool = _merge_entries(valid_existing, _history_entries(state), current, generation)
    state['breeding_pool_generation'] = generation
    state['breeding_pool'] = pool
    return pool


def _parent_weight(entry: dict) -> float:
    rates = entry.get('rates', {})
    g1 = float(rates.get('1', 0.0))
    weight = 1.0 + max(0.0, g1 - MIN_POOL_G1) * 14.0
    if rates.get('2') is not None:
        weight += 1.0 + max(0.0, float(rates['2']) - 0.50) * 8.0
    if rates.get('3') is not None:
        weight += 1.0 + max(0.0, float(rates['3']) - 0.55) * 6.0
    return max(0.25, weight)


def _choose_parent_id(state: dict, rng: random.Random, pool: list[dict]) -> str:
    current = state['current_champion']
    r = rng.random()
    if r < 0.25 or not pool:
        return current
    if r < 0.90:
        return rng.choices(
            [row['genome_id'] for row in pool],
            weights=[_parent_weight(row) for row in pool],
            k=1,
        )[0]
    legacy = [
        gid for gid in state.get('champion_pool', [])
        if gid != current and (b.GENOMES / f'{gid}.json').exists()
    ]
    return rng.choice(legacy) if legacy else current


def _directed_numeric_child(champion: dict, elite: dict, rng: random.Random, factor: float) -> dict:
    """Extrapolate a successful elite farther along one numeric chromosome."""
    champ = canonical_genome(champion)
    child = canonical_genome(elite)
    data, _ = load_schema()
    by_chromosome: dict[str, list[dict]] = {}
    for gene in data['genes']:
        if gene['type'] not in ('int', 'float'):
            continue
        name = gene['name']
        if float(child['params'][name]) == float(champ['params'][name]):
            continue
        by_chromosome.setdefault(gene['chromosome'], []).append(gene)
    if not by_chromosome:
        return graph_rewrite(child, rng, 0.20)

    chromosome = rng.choice(sorted(by_chromosome))
    genes = by_chromosome[chromosome]
    genes.sort(
        key=lambda gene: abs(float(child['params'][gene['name']]) - float(champ['params'][gene['name']])) /
        max(1e-12, float(gene['maximum']) - float(gene['minimum'])),
        reverse=True,
    )
    params = dict(child['params'])
    for gene in genes[:6]:
        name = gene['name']
        elite_value = float(child['params'][name])
        champ_value = float(champ['params'][name])
        value = elite_value + factor * (elite_value - champ_value)
        params[name] = int(round(value)) if gene['type'] == 'int' else value
    child['params'] = params
    return canonical_genome(child)


def _save_unique(child: dict, known: set[str], rng: random.Random, meta: dict) -> tuple[str, object]:
    for retry in range(24):
        gid = genome_id(child)
        if gid not in known:
            break
        child = graph_rewrite(child, rng, 0.22 + 0.02 * (retry % 5))
    else:
        raise RuntimeError('unable to create unique persistent-breeding challenger')
    known.add(gid)
    path = b.GENOMES / f'{gid}.json'
    save_genome(path, child, meta)
    return gid, path


def create_challengers_breeding(state: dict):
    generation = int(state['lineage_generation'])
    attempt = int(state['promotion_attempt']) + 1
    current = state['current_champion']
    champion = b.genome(current)
    pool = ensure_breeding_pool(state)
    rng = random.Random(11917000 + generation * 1009 + attempt * 131)

    failures = behavior._recent_behavior_failures(state)
    epoch = failures // behavior.NO_PROGRESS_BUDGET
    families = list(behavior.FAMILIES)
    rng.shuffle(families)
    families = families[epoch % len(families):] + families[:epoch % len(families)]

    known = {path.name[:-5] for path in b.GENOMES.glob('*.json')}
    ids, created = [], []
    counts = {family: 0 for family in behavior.FAMILIES}
    counts.update({'crossover': 0, 'cma_es': 0, 'directed': 0, 'explore': 0})
    parent_counts: Counter[str] = Counter()

    # 36 structural/tactical offspring remain the majority of the search budget.
    # CMA-ES gets a separate 16-member island rather than replacing graph evolution.
    for slot in range(36):
        family = families[slot % len(families)]
        intensity = (slot // len(families) + epoch) % 5
        parent_id = _choose_parent_id(state, rng, pool)
        parent = b.genome(parent_id)
        child = behavior.behavior_variant(parent, rng, family, intensity)
        gid, path = _save_unique(child, known, rng, {
            'lineage_generation_target': generation + 1,
            'promotion_attempt': attempt,
            'lineage_parent': parent_id,
            'current_champion_at_birth': current,
            'kind': 'persistent_behavior',
            'behavior_family': family,
            'behavior_epoch': epoch,
            'behavior_intensity': intensity,
        })
        ids.append(gid); created.append(path); counts[family] += 1; parent_counts[parent_id] += 1

    # Eight cross-generation recombinations exploit complementary near-winners.
    parent_source = [current] + [row['genome_id'] for row in pool]
    for slot in range(8):
        left_id = _choose_parent_id(state, rng, pool)
        right_choices = [gid for gid in parent_source if gid != left_id]
        right_id = rng.choice(right_choices) if right_choices else current
        child = crossover_genomes(b.genome(left_id), b.genome(right_id), rng)
        gid, path = _save_unique(child, known, rng, {
            'lineage_generation_target': generation + 1,
            'promotion_attempt': attempt,
            'lineage_parent': left_id,
            'crossover_parent': right_id,
            'current_champion_at_birth': current,
            'kind': 'persistent_crossover',
            'behavior_epoch': epoch,
        })
        ids.append(gid); created.append(path); counts['crossover'] += 1
        parent_counts[left_id] += 1; parent_counts[right_id] += 1

    # A full CMA-ES lambda=16 island learns the 46-dimensional INT/FLOAT landscape
    # on one fixed graph.  Its covariance persists across attempts.
    cma_ids, cma_created, cma_info = cma.sample_candidates(
        state, pool, known, attempt, count=cma.CMA_LAMBDA
    )
    ids.extend(cma_ids); created.extend(cma_created); counts['cma_es'] += len(cma_ids)
    parent_counts[cma_info['anchor_gid']] += len(cma_ids)

    # Keep two simple directional probes as an independent sanity check on CMA's
    # learned direction and two broad graph rewrites as explicit escape routes.
    for slot, factor in enumerate((0.50, 1.00)):
        if pool:
            elite_id = pool[slot % min(2, len(pool))]['genome_id']
            child = _directed_numeric_child(champion, b.genome(elite_id), rng, factor)
            parent_id = elite_id
        else:
            parent_id = current
            child = graph_rewrite(champion, rng, 0.24)
        gid, path = _save_unique(child, known, rng, {
            'lineage_generation_target': generation + 1,
            'promotion_attempt': attempt,
            'lineage_parent': parent_id,
            'current_champion_at_birth': current,
            'kind': 'directed_numeric_probe',
            'direction_factor': factor,
            'behavior_epoch': epoch,
        })
        ids.append(gid); created.append(path); counts['directed'] += 1; parent_counts[parent_id] += 1

    for slot in range(2):
        parent_id = _choose_parent_id(state, rng, pool)
        seed = b.genome(parent_id)
        child = graph_rewrite(seed, rng, 0.36 + 0.02 * slot)
        gid, path = _save_unique(child, known, rng, {
            'lineage_generation_target': generation + 1,
            'promotion_attempt': attempt,
            'lineage_parent': parent_id,
            'current_champion_at_birth': current,
            'kind': 'persistent_explore',
            'behavior_epoch': epoch,
        })
        ids.append(gid); created.append(path); counts['explore'] += 1; parent_counts[parent_id] += 1

    assert len(ids) == 64, f'lineage population budget drifted: {len(ids)}'
    behavior.f.phase_heartbeat(
        state,
        'persistent_population_created',
        challengers=len(ids),
        behavior_epoch=epoch,
        no_progress_budget=behavior.NO_PROGRESS_BUDGET,
        behavior_counts=counts,
        breeding_pool_size=len(pool),
        breeding_parent_counts=dict(parent_counts),
        directed_probes=counts['directed'],
        cma_es_candidates=counts['cma_es'],
        cma_es_generation=cma_info['es_generation'],
        cma_es_sigma=cma_info['sigma'],
        cma_es_anchor=cma_info['anchor_gid'],
        cma_es_dimension=cma_info['dimension'],
    )
    return ids, created, counts


def transaction_breeding(state: dict, txid: str):
    result = _ORIGINAL_TRANSACTION_HARDENED(state, txid)
    latest = b.load_state()
    generation = int(latest['lineage_generation'])

    if result.get('promoted'):
        latest['breeding_pool_generation'] = generation
        latest['breeding_pool'] = []
    else:
        pool = ensure_breeding_pool(latest)
        attempt = int(result.get('attempt', latest.get('promotion_attempt', 0)))
        incoming = []
        for row in result.get('finalists') or []:
            entry = _finalist_entry(row, generation, attempt)
            if entry is not None:
                incoming.append(entry)
        latest['breeding_pool'] = _merge_entries(pool, incoming, latest.get('current_champion'), generation)
        latest['breeding_pool_generation'] = generation

    cma_update = cma.update_cma_state(latest, result)

    b.dump(b.STATE, latest)
    try:
        heart = json.loads(b.HEART.read_text()) if b.HEART.exists() else {}
    except Exception:
        heart = {}
    heart['breeding_pool_size'] = len(latest.get('breeding_pool', []))
    heart['breeding_pool_generation'] = generation
    heart['breeding_pool_top'] = [
        {
            'genome_id': row['genome_id'],
            'rates': row.get('rates', {}),
            'attempt': row.get('attempt'),
        }
        for row in latest.get('breeding_pool', [])[:5]
    ]
    heart['cma_es_update'] = cma_update
    if isinstance(latest.get('cma_state'), dict):
        cs = latest['cma_state']
        heart['cma_es_state'] = {
            'es_generation': int(cs.get('es_generation', 0)),
            'sigma': float(cs.get('sigma', 0.0)),
            'anchor_gid': cs.get('anchor_gid'),
            'best_gid': cs.get('best_gid'),
            'best_fitness': cs.get('best_fitness'),
            'stagnation': int(cs.get('stagnation', 0)),
            'restarts': int(cs.get('restarts', 0)),
        }
    else:
        heart['cma_es_state'] = None
    heart['state_hash'] = b.state_hash(latest)
    b.dump(b.HEART, heart)
    b.persist([b.STATE, b.HEART], 'lineage: retain breeding pool and update CMA-ES')
    return result


def install() -> None:
    behavior.create_challengers_behavior = create_challengers_breeding
    p.transaction_hardened = transaction_breeding
