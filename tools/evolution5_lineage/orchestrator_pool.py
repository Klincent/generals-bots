from __future__ import annotations
import json
from pathlib import Path

from . import orchestrator as b
from .policy import HARD_GATES

_ORIG_CREATE = b.create_challengers
_ORIG_TRANSACTION = b.transaction

ANTI_OVERFIT_MIX = {
    'micro': .05,
    'crossover': .35,
    'bundle': .15,
    'module': .10,
    'graph': .30,
    'immigrant': .05,
}
PRESSURE_MIX = {
    'micro': .10,
    'crossover': .15,
    'bundle': .20,
    'module': .20,
    'graph': .25,
    'immigrant': .10,
}


def _generation_members(state: dict, target_generation: int, main: str | None) -> list[str]:
    raw = list(state.get('generation_elites', {}).get(str(target_generation), []))
    if main:
        raw = [main] + raw
    out = []
    for gid in raw:
        if gid and gid not in out and (b.GENOMES / f'{gid}.json').exists():
            out.append(gid)
    return out[:4]


def _pair_distribution(total_pairs: int, n: int) -> list[int]:
    if n <= 1:
        return [total_pairs]
    main = total_pairs // 2
    remaining = total_pairs - main
    peers = n - 1
    base, rem = divmod(remaining, peers)
    return [main] + [base + (1 if i < rem else 0) for i in range(peers)]


def generation_matchup(state: dict, cand: str, distance: int, total_pairs: int, stream: str, label: str, out: Path) -> dict:
    g = int(state['lineage_generation'])
    target_generation = g - (distance - 1)
    main = {
        1: state.get('current_champion'),
        2: state.get('previous_champion'),
        3: state.get('grandparent_champion'),
    }[distance]
    members = _generation_members(state, target_generation, main)
    if not members:
        raise RuntimeError(f'no lineage opponents for distance {distance} generation {target_generation}')
    pairs = _pair_distribution(total_pairs, len(members))
    cw = b.wrapper(cand, out / f'{cand[:10]}-candidate.sh')
    raw_summaries = []
    details = {}
    timing_ok = True
    for idx, (opp, n_pairs) in enumerate(zip(members, pairs)):
        st = b.allocate(state, stream, n_pairs, f'{label}-d{distance}-{idx}-{opp[:8]}')
        ow = b.wrapper(opp, out / f'{idx}-{opp[:10]}-opponent.sh')
        s = b.ev.paired(cw, ow, st, n_pairs, out / f'{idx}-{opp[:8]}-games')
        raw_summaries.append(s)
        details[opp] = b.compact(s)
        timing_ok = timing_ok and b.timing_ok(s)
    agg = b.ev.combine(raw_summaries)
    q = b.compact(agg)
    q['timing_ok'] = timing_ok
    q['target_generation'] = target_generation
    q['main_champion'] = main
    q['elite_members'] = members
    q['pair_distribution'] = pairs
    q['member_results'] = details
    return q


def deep_lineage_pool(state: dict, rows: list[dict]) -> list[dict]:
    g = int(state['lineage_generation'])
    a = int(state['promotion_attempt']) + 1
    available = {
        1: bool(state.get('current_champion')),
        2: bool(state.get('previous_champion')),
        3: bool(state.get('grandparent_champion')),
    }
    # Funnel: 16 screened -> 6 deep G-1 -> 4 G-2 -> up to 4 G-3.
    parent_rows = rows[:6]
    for r in parent_rows:
        r['matchups'] = {
            1: generation_matchup(
                state, r['genome_id'], 1, 48, 'parent',
                f'g{g}-a{a}-parent-{r["genome_id"][:8]}',
                b.TMP / 'deep-parent' / r['genome_id'][:10],
            )
        }
    parent_rows.sort(key=lambda r: (
        r['matchups'][1]['raw_win_rate'],
        r['matchups'][1]['score'],
        r['novelty'],
    ), reverse=True)
    survivors = parent_rows[:4]

    if available[2]:
        for r in survivors:
            r['matchups'][2] = generation_matchup(
                state, r['genome_id'], 2, 32, 'grandparent',
                f'g{g}-a{a}-grand-{r["genome_id"][:8]}',
                b.TMP / 'deep-grand' / r['genome_id'][:10],
            )
        survivors.sort(key=lambda r: (
            r['matchups'][1]['raw_win_rate'],
            r['matchups'][2]['raw_win_rate'],
            b.weighted_lineage_score(r['matchups']),
        ), reverse=True)

    if available[3]:
        for r in survivors:
            r['matchups'][3] = generation_matchup(
                state, r['genome_id'], 3, 24, 'great',
                f'g{g}-a{a}-great-{r["genome_id"][:8]}',
                b.TMP / 'deep-great' / r['genome_id'][:10],
            )

    for r in survivors:
        r['promotion_gate_passed'] = b.gate_pass(r['matchups']) and all(
            bool(x.get('timing_ok', False)) for x in r['matchups'].values()
        )
        r['dominance_gate_passed'] = b.dominance_pass(r['matchups'])
        r['weighted_lineage_score'] = b.weighted_lineage_score(r['matchups'])
        r['minimum_lineage_score'] = b.minimum_lineage_score(r['matchups'])
    survivors.sort(key=b.promotion_key, reverse=True)
    return survivors


def create_challengers_biased(state: dict):
    bias = state.get('mutation_bias', 'normal')
    old_normal, old_plateau = b.NORMAL_MIX, b.PLATEAU_MIX
    try:
        if bias == 'anti_overfit':
            b.NORMAL_MIX = ANTI_OVERFIT_MIX
            b.PLATEAU_MIX = ANTI_OVERFIT_MIX
        elif bias == 'pressure':
            b.NORMAL_MIX = PRESSURE_MIX
            b.PLATEAU_MIX = PRESSURE_MIX
        return _ORIG_CREATE(state)
    finally:
        b.NORMAL_MIX, b.PLATEAU_MIX = old_normal, old_plateau


def _failure_bias(result: dict) -> str:
    finalists = result.get('finalists') or []
    if not finalists:
        return 'pressure'
    m = finalists[0].get('matchups', {})
    if float(m.get(1, {}).get('raw_win_rate', 0.0)) < HARD_GATES[1]:
        return 'pressure'
    for d in (2, 3):
        if d in m and float(m[d].get('raw_win_rate', 0.0)) < HARD_GATES[d]:
            return 'anti_overfit'
    return 'normal'


def _watchdog_warnings(state: dict) -> list[dict]:
    hist = state.get('watchdog_history', [])
    if len(hist) < 2:
        return []
    prev, cur = hist[-2], hist[-1]
    out = []
    for archetype, q in cur.get('results', {}).items():
        if archetype not in prev.get('results', {}):
            continue
        old = float(prev['results'][archetype].get('score', 0.0))
        new = float(q.get('score', 0.0))
        if old - new > .20:
            out.append({
                'generation': int(cur.get('generation', state.get('lineage_generation', 0))),
                'archetype': archetype,
                'previous_score': old,
                'new_score': new,
                'drop': old - new,
                'warning': 'REGRESSION WARNING',
            })
    return out


def transaction_hardened(state: dict, txid: str):
    state.setdefault('generation_elites', {str(state.get('lineage_generation', 0)): list(state.get('champion_pool', []))})
    state.setdefault('mutation_bias', 'normal')
    state.setdefault('watchdog_regression_warnings', [])
    result = _ORIG_TRANSACTION(state, txid)

    # Original transaction has already durably committed its result. Add lineage-pool
    # metadata in a second tiny durable commit so future attempts can sample peers.
    latest = b.load_state()
    if result.get('promoted'):
        gen = int(latest['lineage_generation'])
        finalists = result.get('finalists') or []
        elite = [latest['current_champion']] + [r['genome_id'] for r in finalists]
        latest.setdefault('generation_elites', {})[str(gen)] = list(dict.fromkeys(elite))[:8]
        keep = sorted((int(k), k) for k in latest['generation_elites'])[-20:]
        latest['generation_elites'] = {k: latest['generation_elites'][k] for _, k in keep}
        latest['mutation_bias'] = 'normal'
        warnings = _watchdog_warnings(latest)
        if warnings:
            latest.setdefault('watchdog_regression_warnings', []).extend(warnings)
    else:
        latest['mutation_bias'] = _failure_bias(result)

    b.dump(b.STATE, latest)
    heart = json.loads(b.HEART.read_text())
    heart['mutation_bias'] = latest['mutation_bias']
    heart['state_hash'] = b.state_hash(latest)
    b.dump(b.HEART, heart)
    b.persist([b.STATE, b.HEART], 'lineage: update elite pools and adaptive mutation bias')
    return result


def main():
    b.deep_lineage = deep_lineage_pool
    b.create_challengers = create_challengers_biased
    b.transaction = transaction_hardened
    b.main()


if __name__ == '__main__':
    main()
