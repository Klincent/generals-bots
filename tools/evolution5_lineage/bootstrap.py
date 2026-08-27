from __future__ import annotations
import json
from pathlib import Path
from tools.evolution4.evaluator import ROOT

E5 = ROOT / 'evolution5'
L = ROOT / 'evolution5_lineage'
STATE = L / 'state.json'
HEART = L / 'heartbeat.json'
GENOMES = E5 / 'genomes'


def dump(path: Path, obj: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + '\n')


def _candidate_rows(old: dict) -> list[dict]:
    rows = []
    seen = set()
    for r in old.get('league', []):
        gid = r.get('genome_id')
        if not gid or gid in seen or not (GENOMES / f'{gid}.json').exists():
            continue
        seen.add(gid)
        rows.append(dict(r))
    gid = old.get('best_fresh_genome_id')
    if gid and gid not in seen and (GENOMES / f'{gid}.json').exists():
        rows.append({
            'genome_id': gid,
            'fresh_win_rate': float(old.get('best_fresh_win_rate', 0.0)),
            'fresh_score': float(old.get('best_fresh_score', 0.0)),
            'minimum': 0.0,
            'novelty': 0.0,
        })
    return rows


def _rank(r: dict):
    # Bootstrap for generalization: prefer a strong floor first, then raw wins.
    return (
        1 if float(r.get('fresh_win_rate', 0.0)) >= 0.70 else 0,
        float(r.get('minimum', 0.0)),
        float(r.get('fresh_win_rate', 0.0)),
        float(r.get('fresh_score', 0.0)),
        float(r.get('novelty', 0.0)),
    )


def build(force: bool = False) -> dict:
    if STATE.exists() and not force:
        return json.loads(STATE.read_text())
    old = json.loads((E5 / 'state.json').read_text())
    rows = sorted(_candidate_rows(old), key=_rank, reverse=True)
    if not rows:
        raise RuntimeError('no reproducible Evolution5 genomes available for lineage bootstrap')
    pool = [r['genome_id'] for r in rows[:8]]
    root = pool[0]
    state = {
        'mode': 'evolution5_lineage_selfplay_v1',
        'phase': 'active',
        'lineage_generation': 0,
        'promotion_attempt': 0,
        'current_champion': root,
        'previous_champion': None,
        'grandparent_champion': None,
        'great_grandparent_champion': None,
        'champion_pool': pool,
        'generation_elites': {'0': pool},
        'lineage_hof': [root],
        'lineage_history': [{
            'generation': 0,
            'genome_id': root,
            'parent': None,
            'grandparent': None,
            'great_grandparent': None,
            'bootstrap': True,
            'source_cambrian_generation': int(old.get('generation', -1)),
        }],
        'bootstrap_candidates': rows[:16],
        'bootstrap_population': list(old.get('current_population', [])),
        'source_cambrian_generation': int(old.get('generation', -1)),
        'source_cambrian_best': old.get('best_fresh_genome_id'),
        'promotion_gate_passed': False,
        'dominance_gate_passed': False,
        'vs_parent_win_rate': None,
        'vs_grandparent_win_rate': None,
        'vs_great_grandparent_win_rate': None,
        'attempt_history': [],
        'watchdog_history': [],
        'watchdog_regression_warnings': [],
        'ancestor_gauntlets': [],
        'seed_ledger': {
            'screen': {'next_seed': 1200000},
            'parent': {'next_seed': 2200000},
            'grandparent': {'next_seed': 3200000},
            'great': {'next_seed': 4200000},
            'reference': {'next_seed': 5200000},
            'watchdog': {'next_seed': 6200000},
            'gauntlet': {'next_seed': 7200000},
        },
        'mutation_temperature': 1.0,
        'mutation_bias': 'normal',
        'failed_promotion_streak': 0,
        'tested_challengers': 0,
    }
    for d in (L / 'results', L / 'checkpoints'):
        d.mkdir(parents=True, exist_ok=True)
    dump(STATE, state)
    dump(HEART, {
        'result': 'ready',
        'lineage_generation': 0,
        'attempt': 0,
        'current_champion': root,
        'challenger_status': 'bootstrap-complete',
    })
    return state


def main():
    s = build()
    print('LINEAGE BOOTSTRAP root=', s['current_champion'], 'pool=', len(s['champion_pool']), 'source_g=', s['source_cambrian_generation'])


if __name__ == '__main__':
    main()
