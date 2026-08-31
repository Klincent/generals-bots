from __future__ import annotations

import copy
import math

import numpy as np

from . import orchestrator as b
from tools.evolution4.schema import load_schema
from tools.evolution5.genome import canonical_genome, genome_id, save_genome
from tools.evolution5.graph import graph_hash


CMA_LAMBDA = 16
CMA_INITIAL_SIGMA = 0.12
CMA_MIN_SIGMA = 0.015
CMA_MAX_SIGMA = 0.35
CMA_STAGNATION_RESTART = 6


def numeric_genes() -> list[dict]:
    data, _ = load_schema()
    return [gene for gene in data['genes'] if gene['type'] in ('int', 'float')]


def vector_from_genome(genome: dict) -> np.ndarray:
    c = canonical_genome(genome)
    out = []
    for gene in numeric_genes():
        lo = float(gene['minimum'])
        hi = float(gene['maximum'])
        out.append((float(c['params'][gene['name']]) - lo) / max(1e-12, hi - lo))
    return np.asarray(out, dtype=float)


def _reflect_unit(x: np.ndarray) -> np.ndarray:
    y = np.mod(np.asarray(x, dtype=float), 2.0)
    return np.where(y <= 1.0, y, 2.0 - y)


def genome_from_vector(anchor: dict, x: np.ndarray) -> dict:
    base = canonical_genome(anchor)
    params = dict(base['params'])
    x = _reflect_unit(np.asarray(x, dtype=float))
    for value, gene in zip(x, numeric_genes()):
        lo = float(gene['minimum'])
        hi = float(gene['maximum'])
        raw = lo + float(value) * (hi - lo)
        params[gene['name']] = int(round(raw)) if gene['type'] == 'int' else raw
    return canonical_genome({'graph': copy.deepcopy(base['graph']), 'params': params})


def _new_state(state: dict, pool: list[dict], restarts: int = 0) -> dict:
    generation = int(state.get('lineage_generation', 0))
    current = state['current_champion']
    anchor_gid = pool[0]['genome_id'] if pool else current
    if not (b.GENOMES / f'{anchor_gid}.json').exists():
        anchor_gid = current
    anchor = b.genome(anchor_gid)
    mean = vector_from_genome(anchor)
    n = int(mean.size)
    return {
        'lineage_generation': generation,
        'anchor_gid': anchor_gid,
        'anchor_graph_hash': graph_hash(anchor['graph']),
        'dimension': n,
        'mean': mean.tolist(),
        'sigma': CMA_INITIAL_SIGMA,
        'C': np.eye(n, dtype=float).tolist(),
        'pc': np.zeros(n, dtype=float).tolist(),
        'ps': np.zeros(n, dtype=float).tolist(),
        'es_generation': 0,
        'best_fitness': None,
        'best_gid': anchor_gid,
        'stagnation': 0,
        'restarts': int(restarts),
    }


def ensure_cma_state(state: dict, pool: list[dict]) -> dict:
    genes = numeric_genes()
    current = state['current_champion']
    cma = state.get('cma_state')
    invalid = (
        not isinstance(cma, dict)
        or int(cma.get('lineage_generation', -1)) != int(state.get('lineage_generation', 0))
        or int(cma.get('dimension', -1)) != len(genes)
        or not cma.get('anchor_gid')
        or not (b.GENOMES / f"{cma.get('anchor_gid')}.json").exists()
    )
    if invalid:
        cma = _new_state(state, pool, int((cma or {}).get('restarts', 0)))
        state['cma_state'] = cma
        return cma

    # After several CMA generations without a better numerical region, restart the
    # island from the strongest currently known near-winner.  This keeps CMA from
    # polishing one graph forever while the structural evolution has moved elsewhere.
    if int(cma.get('stagnation', 0)) >= CMA_STAGNATION_RESTART:
        restarts = int(cma.get('restarts', 0)) + 1
        cma = _new_state(state, pool, restarts)
        state['cma_state'] = cma
        return cma

    # A promoted champion starts a new lineage generation, handled by the generation
    # check above.  Otherwise keep one fixed graph topology for covariance learning.
    if cma.get('anchor_gid') == current:
        cma['anchor_graph_hash'] = graph_hash(b.genome(current)['graph'])
    state['cma_state'] = cma
    return cma


def _spd(C: np.ndarray) -> np.ndarray:
    C = (np.asarray(C, dtype=float) + np.asarray(C, dtype=float).T) * 0.5
    vals, vecs = np.linalg.eigh(C)
    vals = np.clip(vals, 1e-10, 1e3)
    return vecs @ np.diag(vals) @ vecs.T


def _eigensystem(C: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    C = _spd(C)
    vals, B = np.linalg.eigh(C)
    vals = np.clip(vals, 1e-10, 1e3)
    D = np.sqrt(vals)
    invsqrt = B @ np.diag(1.0 / D) @ B.T
    return B, D, invsqrt


def sample_candidates(
    state: dict,
    pool: list[dict],
    known: set[str],
    attempt: int,
    count: int = CMA_LAMBDA,
) -> tuple[list[str], list[object], dict]:
    cma = ensure_cma_state(state, pool)
    anchor_gid = cma['anchor_gid']
    anchor = b.genome(anchor_gid)
    mean = np.asarray(cma['mean'], dtype=float)
    sigma = float(cma['sigma'])
    C = _spd(np.asarray(cma['C'], dtype=float))
    B, D, _ = _eigensystem(C)
    generation = int(state['lineage_generation'])
    es_generation = int(cma.get('es_generation', 0))
    rng = np.random.default_rng(
        14159000 + generation * 10007 + int(attempt) * 101 + es_generation * 1000003
    )

    ids: list[str] = []
    created: list[object] = []
    samples: list[dict] = []
    for slot in range(int(count)):
        for retry in range(64):
            z = rng.standard_normal(mean.size)
            y = B @ (D * z)
            x = _reflect_unit(mean + sigma * y)
            child = genome_from_vector(anchor, x)
            actual = vector_from_genome(child)
            gid = genome_id(child)
            if gid not in known:
                break
            # Integer rounding can occasionally collapse two samples.  Widen only
            # the resample, not the persistent sigma, so uniqueness does not distort
            # the strategy state.
            z = rng.standard_normal(mean.size)
            y = B @ (D * z)
            x = _reflect_unit(mean + sigma * (1.0 + 0.08 * retry) * y)
            child = genome_from_vector(anchor, x)
            actual = vector_from_genome(child)
            gid = genome_id(child)
            if gid not in known:
                break
        else:
            raise RuntimeError('unable to create unique CMA-ES challenger')

        known.add(gid)
        path = b.GENOMES / f'{gid}.json'
        save_genome(path, child, {
            'lineage_generation_target': generation + 1,
            'promotion_attempt': int(attempt),
            'lineage_parent': anchor_gid,
            'current_champion_at_birth': state['current_champion'],
            'kind': 'cma_es_numeric',
            'cma_es_generation': es_generation,
            'cma_sigma': sigma,
            'cma_anchor': anchor_gid,
            'cma_slot': slot,
        })
        ids.append(gid)
        created.append(path)
        samples.append({'genome_id': gid, 'x': actual.tolist(), 'slot': slot})

    state['cma_pending'] = {
        'lineage_generation': generation,
        'attempt': int(attempt),
        'es_generation': es_generation,
        'anchor_gid': anchor_gid,
        'samples': samples,
    }
    return ids, created, {
        'count': len(ids),
        'anchor_gid': anchor_gid,
        'es_generation': es_generation,
        'sigma': sigma,
        'dimension': int(mean.size),
    }


def _row_fitness(row: dict | None) -> float:
    if not row:
        return 0.0
    matchups = row.get('matchups') or {}
    if 1 in matchups:
        g1 = float(matchups[1].get('raw_win_rate', 0.0))
        if 3 in matchups:
            g2 = float(matchups[2].get('raw_win_rate', 0.0))
            g3 = float(matchups[3].get('raw_win_rate', 0.0))
            return 5.0 + 0.50 * g1 + 0.30 * g2 + 0.20 * g3
        if 2 in matchups:
            g2 = float(matchups[2].get('raw_win_rate', 0.0))
            return 4.0 + 0.60 * g1 + 0.40 * g2
        return 3.0 + g1
    preview = row.get('g1_preview') or {}
    if preview:
        return 2.0 + float(preview.get('raw_win_rate', 0.0))
    return 1.0 + float(row.get('selection_score', 0.0))


def _result_rows(result: dict) -> dict[str, dict]:
    rows: dict[str, dict] = {}
    for row in result.get('screened') or []:
        gid = row.get('genome_id')
        if gid:
            rows[gid] = row
    for row in result.get('finalists') or []:
        gid = row.get('genome_id')
        if gid:
            rows[gid] = row
    return rows


def _constants(n: int, mu: int):
    weights = np.log(mu + 0.5) - np.log(np.arange(1, mu + 1, dtype=float))
    weights /= np.sum(weights)
    mueff = 1.0 / float(np.sum(weights ** 2))
    cc = (4.0 + mueff / n) / (n + 4.0 + 2.0 * mueff / n)
    cs = (mueff + 2.0) / (n + mueff + 5.0)
    c1 = 2.0 / ((n + 1.3) ** 2 + mueff)
    cmu = min(1.0 - c1, 2.0 * (mueff - 2.0 + 1.0 / mueff) / ((n + 2.0) ** 2 + mueff))
    damps = 1.0 + 2.0 * max(0.0, math.sqrt((mueff - 1.0) / (n + 1.0)) - 1.0) + cs
    chi_n = math.sqrt(n) * (1.0 - 1.0 / (4.0 * n) + 1.0 / (21.0 * n * n))
    return weights, mueff, cc, cs, c1, cmu, damps, chi_n


def update_cma_state(state: dict, result: dict) -> dict:
    if result.get('promoted'):
        restarts = int((state.get('cma_state') or {}).get('restarts', 0))
        state.pop('cma_pending', None)
        state.pop('cma_state', None)
        return {'result': 'reset_on_promotion', 'restarts': restarts}

    pending = state.pop('cma_pending', None)
    cma = state.get('cma_state')
    if not pending or not isinstance(cma, dict):
        return {'result': 'no_pending_population'}
    if int(pending.get('lineage_generation', -1)) != int(state.get('lineage_generation', 0)):
        return {'result': 'stale_pending_population'}

    row_map = _result_rows(result)
    ranked = []
    for sample in pending.get('samples', []):
        gid = sample['genome_id']
        fitness = _row_fitness(row_map.get(gid))
        ranked.append((fitness, gid, np.asarray(sample['x'], dtype=float)))
    ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
    positive = [item for item in ranked if item[0] > 0.0]
    best_fitness = float(ranked[0][0]) if ranked else 0.0
    best_gid = ranked[0][1] if ranked else None

    previous_best = cma.get('best_fitness')
    improved = previous_best is None or best_fitness > float(previous_best) + 1e-9
    cma['best_fitness'] = best_fitness if improved else previous_best
    if improved and best_gid:
        cma['best_gid'] = best_gid
        cma['anchor_gid'] = best_gid
    cma['stagnation'] = 0 if improved else int(cma.get('stagnation', 0)) + 1

    # If fewer than two CMA samples even survive the common screen, there is no
    # reliable covariance direction.  Expand the search radius and try again.
    if len(positive) < 2:
        cma['sigma'] = min(CMA_MAX_SIGMA, max(CMA_MIN_SIGMA, float(cma['sigma']) * 1.25))
        cma['es_generation'] = int(cma.get('es_generation', 0)) + 1
        state['cma_state'] = cma
        return {
            'result': 'expanded_after_weak_screen',
            'survivors': len(positive),
            'best_fitness': best_fitness,
            'best_gid': best_gid,
            'sigma': float(cma['sigma']),
            'stagnation': int(cma['stagnation']),
        }

    n = int(cma['dimension'])
    mu = max(2, min(len(positive), len(ranked) // 2))
    selected = positive[:mu]
    weights, mueff, cc, cs, c1, cmu, damps, chi_n = _constants(n, mu)

    old_mean = np.asarray(cma['mean'], dtype=float)
    sigma = float(cma['sigma'])
    C = _spd(np.asarray(cma['C'], dtype=float))
    pc = np.asarray(cma['pc'], dtype=float)
    ps = np.asarray(cma['ps'], dtype=float)
    _, _, invsqrt = _eigensystem(C)

    X = np.stack([item[2] for item in selected], axis=0)
    new_mean = np.sum(weights[:, None] * X, axis=0)
    y_k = (X - old_mean[None, :]) / max(1e-12, sigma)
    y_w = (new_mean - old_mean) / max(1e-12, sigma)

    ps_new = (1.0 - cs) * ps + math.sqrt(cs * (2.0 - cs) * mueff) * (invsqrt @ y_w)
    es_generation = int(cma.get('es_generation', 0)) + 1
    denom = math.sqrt(max(1e-12, 1.0 - (1.0 - cs) ** (2 * es_generation)))
    hsig = 1.0 if (np.linalg.norm(ps_new) / denom / chi_n) < (1.4 + 2.0 / (n + 1.0)) else 0.0
    pc_new = (1.0 - cc) * pc + hsig * math.sqrt(cc * (2.0 - cc) * mueff) * y_w

    rank_mu = np.zeros_like(C)
    for weight, y in zip(weights, y_k):
        rank_mu += float(weight) * np.outer(y, y)
    C_new = (
        (1.0 - c1 - cmu) * C
        + c1 * (np.outer(pc_new, pc_new) + (1.0 - hsig) * cc * (2.0 - cc) * C)
        + cmu * rank_mu
    )
    C_new = _spd(C_new)
    sigma_new = sigma * math.exp((cs / damps) * (float(np.linalg.norm(ps_new)) / chi_n - 1.0))
    sigma_new = min(CMA_MAX_SIGMA, max(CMA_MIN_SIGMA, sigma_new))

    cma.update({
        'mean': _reflect_unit(new_mean).tolist(),
        'sigma': float(sigma_new),
        'C': C_new.tolist(),
        'pc': pc_new.tolist(),
        'ps': ps_new.tolist(),
        'es_generation': es_generation,
        'last_population_survivors': len(positive),
        'last_best_fitness': best_fitness,
        'last_best_gid': best_gid,
    })
    state['cma_state'] = cma
    return {
        'result': 'updated',
        'survivors': len(positive),
        'mu': mu,
        'best_fitness': best_fitness,
        'best_gid': best_gid,
        'sigma': float(sigma_new),
        'es_generation': es_generation,
        'stagnation': int(cma['stagnation']),
        'restarts': int(cma.get('restarts', 0)),
    }
