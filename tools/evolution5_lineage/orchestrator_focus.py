from __future__ import annotations

import json
from pathlib import Path

from . import orchestrator as b
from . import orchestrator_pool as p
from .policy import HARD_GATES


# Exploit near-winners more aggressively when the current champion has stalled.
# Random graph rewrites/immigrants remain present, but no longer dominate expensive cycles.
FOCUS_PRESSURE_MIX = {
    'micro': .10,
    'crossover': .35,
    'bundle': .20,
    'module': .20,
    'graph': .10,
    'immigrant': .05,
}

_ORIG_OPPONENT_MIX = b.opponent_mix


def focus_opponent_mix(lineage_generation: int) -> dict[str, float]:
    """Prioritise beating the current lineage while retaining an anti-overfit reference check."""
    if lineage_generation <= 1:
        return {'reference': 0.15, 'lineage': 0.85}
    return _ORIG_OPPONENT_MIX(lineage_generation)


def persist_resilient(paths: list[Path], message: str) -> None:
    """Persist transaction commits even if a maintenance commit advanced the control branch."""
    uniq = []
    for path in paths:
        if path.exists() and path not in uniq:
            uniq.append(path)
    if not uniq:
        return

    b.run_git('add', *[str(path) for path in uniq])
    if b.run_git('diff', '--cached', '--quiet', check=False).returncode == 0:
        return
    b.run_git('commit', '-m', message)

    for retry in range(4):
        push = b.run_git('push', 'origin', f'HEAD:{b.CONTROL}', check=False)
        if push.returncode == 0:
            return
        b.run_git('fetch', '--no-tags', 'origin', b.CONTROL)
        rebased = b.run_git('rebase', f'origin/{b.CONTROL}', check=False)
        if rebased.returncode != 0:
            b.run_git('rebase', '--abort', check=False)
            raise RuntimeError('lineage persist failed: remote advanced and automatic rebase conflicted')
    raise RuntimeError('lineage persist failed after four push/rebase attempts')


def phase_heartbeat(state: dict, status: str, **extra) -> None:
    try:
        heart = json.loads(b.HEART.read_text()) if b.HEART.exists() else {}
    except Exception:
        heart = {}
    attempt = int(heart.get('attempt', state.get('promotion_attempt', 0)))
    heart.update({
        'result': 'in_progress',
        'lineage_generation': int(state.get('lineage_generation', 0)),
        'attempt': attempt,
        'current_champion': state.get('current_champion'),
        'challenger_status': status,
        'last_progress_time': b.now(),
        **extra,
    })
    b.dump(b.HEART, heart)
    b.persist([b.HEART], f'lineage: progress {status}')


def create_challengers_focus(state: dict):
    """Breed from recent near-winners instead of repeatedly restarting around only the champion."""
    original_pool = list(state.get('champion_pool', []))
    original_pressure = dict(p.PRESSURE_MIX)
    current = state.get('current_champion')

    near = []
    for row in reversed(state.get('attempt_history', [])):
        gid = row.get('best_challenger')
        rate = float(row.get('best_vs_parent_win_rate', 0.0))
        if gid and gid != current and rate >= 0.54 and (b.GENOMES / f'{gid}.json').exists() and gid not in near:
            near.append(gid)
        if len(near) >= 4:
            break

    # Keep a compact breeding pool so crossover actually samples the useful near-winners.
    breeding = []
    for gid in [current, *near, *original_pool[:4]]:
        if gid and gid not in breeding and (b.GENOMES / f'{gid}.json').exists():
            breeding.append(gid)

    try:
        state['champion_pool'] = breeding
        if state.get('mutation_bias', 'normal') == 'pressure' or int(state.get('failed_promotion_streak', 0)) >= 2:
            p.PRESSURE_MIX = FOCUS_PRESSURE_MIX
            state['mutation_bias'] = 'pressure'
        return p.create_challengers_biased(state)
    finally:
        state['champion_pool'] = original_pool
        p.PRESSURE_MIX = original_pressure


def deep_lineage_focus(state: dict, rows: list[dict]) -> list[dict]:
    """Two-stage G-1 funnel: test more ideas cheaply, spend full samples only on the best few."""
    g = int(state['lineage_generation'])
    a = int(state['promotion_attempt']) + 1
    available = {
        1: bool(state.get('current_champion')),
        2: bool(state.get('previous_champion')),
        3: bool(state.get('grandparent_champion')),
    }

    # Old funnel spent 6 * 48 G-1 pairs. New funnel explores 10 candidates with
    # 8-pair previews, then validates only the top 3 on the full configured 48 pairs.
    previews = rows[:10]
    phase_heartbeat(state, 'g1_preview', candidates=len(previews), preview_pairs=8)
    for index, row in enumerate(previews, 1):
        row['g1_preview'] = p.generation_matchup(
            state, row['genome_id'], 1, 8, 'parent',
            f'g{g}-a{a}-preview-{row["genome_id"][:8]}',
            b.TMP / 'g1-preview' / row['genome_id'][:10],
        )
        if index in (2, 4, 6, 8, 10):
            phase_heartbeat(state, 'g1_preview', completed=index, candidates=len(previews), preview_pairs=8)

    previews.sort(key=lambda row: (
        row['g1_preview']['raw_win_rate'],
        row['g1_preview']['score'],
        row['screen_parent']['raw_win_rate'],
        row['selection_score'],
        row['novelty'],
    ), reverse=True)

    finalists = previews[:3]
    phase_heartbeat(state, 'deep_g1', candidates=len(finalists), full_pairs=48)
    for index, row in enumerate(finalists, 1):
        row['matchups'] = {
            1: p.generation_matchup(
                state, row['genome_id'], 1, 48, 'parent',
                f'g{g}-a{a}-parent-{row["genome_id"][:8]}',
                b.TMP / 'deep-parent' / row['genome_id'][:10],
            )
        }
        phase_heartbeat(state, 'deep_g1', completed=index, candidates=len(finalists), full_pairs=48)

    finalists.sort(key=lambda row: (
        row['matchups'][1]['raw_win_rate'],
        row['matchups'][1]['score'],
        row['novelty'],
    ), reverse=True)

    # Do not burn G-2 CPU on candidates that are not already convincing against G-1.
    g2_rows = [row for row in finalists if float(row['matchups'][1]['raw_win_rate']) >= 0.56][:2]
    if available[2] and g2_rows:
        phase_heartbeat(state, 'deep_g2', candidates=len(g2_rows), advance_threshold_g1=0.56)
        for index, row in enumerate(g2_rows, 1):
            row['matchups'][2] = p.generation_matchup(
                state, row['genome_id'], 2, 32, 'grandparent',
                f'g{g}-a{a}-grand-{row["genome_id"][:8]}',
                b.TMP / 'deep-grand' / row['genome_id'][:10],
            )
            phase_heartbeat(state, 'deep_g2', completed=index, candidates=len(g2_rows), advance_threshold_g1=0.56)

    # G-3 is even more expensive: only candidates already near the desired G-1 dominance
    # and safely above the G-2 hard gate earn this evaluation.
    g3_rows = [
        row for row in g2_rows
        if 2 in row.get('matchups', {})
        and float(row['matchups'][1]['raw_win_rate']) >= 0.58
        and float(row['matchups'][2]['raw_win_rate']) >= 0.62
    ][:2]
    if available[3] and g3_rows:
        phase_heartbeat(state, 'deep_g3', candidates=len(g3_rows), advance_thresholds={'g1': 0.58, 'g2': 0.62})
        for index, row in enumerate(g3_rows, 1):
            row['matchups'][3] = p.generation_matchup(
                state, row['genome_id'], 3, 24, 'great',
                f'g{g}-a{a}-great-{row["genome_id"][:8]}',
                b.TMP / 'deep-great' / row['genome_id'][:10],
            )
            phase_heartbeat(state, 'deep_g3', completed=index, candidates=len(g3_rows), advance_thresholds={'g1': 0.58, 'g2': 0.62})

    required = [distance for distance, exists in available.items() if exists]
    for row in finalists:
        matchups = row.get('matchups', {})
        complete = all(distance in matchups for distance in required)
        row['promotion_gate_passed'] = (
            complete
            and b.gate_pass(matchups)
            and all(bool(result.get('timing_ok', False)) for result in matchups.values())
        )
        row['dominance_gate_passed'] = complete and b.dominance_pass(matchups)
        row['weighted_lineage_score'] = b.weighted_lineage_score(matchups)
        row['minimum_lineage_score'] = b.minimum_lineage_score(matchups)
        row['evaluation_complete'] = complete

    finalists.sort(key=b.promotion_key, reverse=True)
    phase_heartbeat(
        state,
        'deep_complete',
        finalists=len(finalists),
        g2_evaluated=len(g2_rows) if available[2] else 0,
        g3_evaluated=len(g3_rows) if available[3] else 0,
    )
    return finalists


def main() -> None:
    # Install durability first so every progress/state commit in this run can recover
    # from a non-fast-forward caused by maintenance changes.
    b.persist = persist_resilient
    b.opponent_mix = focus_opponent_mix
    p._phase_heartbeat = phase_heartbeat

    # Keep the proven pool transaction bookkeeping, but replace search economics.
    b.screen = p.screen_parallel
    b.create_challengers = create_challengers_focus
    b.deep_lineage = deep_lineage_focus
    b.transaction = p.transaction_hardened
    b.main()


if __name__ == '__main__':
    main()
