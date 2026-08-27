from __future__ import annotations

HARD_GATES = {1: 0.55, 2: 0.60, 3: 0.65}
DOMINANCE_TARGETS = {1: 0.60, 2: 0.70, 3: 0.80}


def phase(lineage_generation: int) -> str:
    if lineage_generation <= 1:
        return 'early'
    if lineage_generation <= 4:
        return 'mid'
    if lineage_generation <= 7:
        return 'advanced'
    return 'mature'


def opponent_mix(lineage_generation: int) -> dict[str, float]:
    p = phase(lineage_generation)
    if p == 'early':
        return {'reference': 0.50, 'lineage': 0.50}
    if p == 'mid':
        return {'reference': 0.25, 'lineage': 0.75}
    if p == 'advanced':
        return {'reference': 0.10, 'lineage': 0.90}
    return {'reference': 0.0, 'lineage': 1.0}


def lineage_weights() -> dict[int, float]:
    return {1: 0.50, 2: 0.30, 3: 0.20}


def gate_pass(matchups: dict[int, dict]) -> bool:
    for distance, result in matchups.items():
        if distance not in HARD_GATES:
            continue
        if float(result.get('raw_win_rate', 0.0)) < HARD_GATES[distance]:
            return False
        if int(result.get('errors', 0)) != 0 or int(result.get('illegal_actions', 0)) != 0:
            return False
    return bool(matchups)


def dominance_pass(matchups: dict[int, dict]) -> bool:
    # 60/70/80 is only a true dominance claim once all three ancestors exist.
    if not all(distance in matchups for distance in DOMINANCE_TARGETS):
        return False
    for distance, target in DOMINANCE_TARGETS.items():
        if float(matchups[distance].get('raw_win_rate', 0.0)) < target:
            return False
    return True


def weighted_lineage_score(matchups: dict[int, dict]) -> float:
    weights = lineage_weights()
    total = 0.0
    denom = 0.0
    for distance, result in matchups.items():
        if distance not in weights:
            continue
        w = weights[distance]
        total += w * float(result.get('score', 0.0))
        denom += w
    return total / denom if denom else 0.0


def minimum_lineage_score(matchups: dict[int, dict]) -> float:
    vals = [float(v.get('score', 0.0)) for k, v in matchups.items() if k in HARD_GATES]
    return min(vals) if vals else 0.0


def promotion_key(row: dict) -> tuple:
    m = row.get('matchups', {})
    return (
        1 if gate_pass(m) else 0,
        float(m.get(1, {}).get('raw_win_rate', 0.0)),
        weighted_lineage_score(m),
        minimum_lineage_score(m),
        float(m.get(2, {}).get('raw_win_rate', 0.0)),
        float(m.get(3, {}).get('raw_win_rate', 0.0)),
        float(row.get('novelty', 0.0)),
        float(row.get('reference_score', 0.0)),
    )
