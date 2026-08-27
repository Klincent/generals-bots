from __future__ import annotations
import hashlib
import json
import os
import random
import shutil
import subprocess
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from tools.evolution4 import evaluator as ev
from tools.evolution4.evaluator import ROOT, AGENT
from tools.evolution5.freeze import freeze_submission
from tools.evolution5.genome import env_for, genome_id, load_genome as load_genome_file, save_genome
from tools.evolution5.graph import graph_distance, ISLANDS
from tools.evolution5.mutate import (
    NORMAL_MIX, PLATEAU_MIX, choose_kind, micro_mutation, module_mutation,
    graph_rewrite, strategy_bundle, crossover_genomes, random_immigrant,
)
from .bootstrap import build as ensure_bootstrap
from .policy import (
    HARD_GATES, DOMINANCE_TARGETS, gate_pass, dominance_pass, minimum_lineage_score,
    opponent_mix, phase, promotion_key, weighted_lineage_score,
)

CONTROL = 'evolution5/lineage-selfplay'
E5 = ROOT / 'evolution5'
L = ROOT / 'evolution5_lineage'
STATE = L / 'state.json'
HEART = L / 'heartbeat.json'
STOP = L / 'STOP'
RESULTS = L / 'results'
CHECKPOINTS = L / 'checkpoints'
GENOMES = E5 / 'genomes'
TMP = Path('/tmp/e5-lineage')


def now():
    return datetime.now(timezone.utc).isoformat()


def dump(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + '\n')


def load_state():
    return json.loads(STATE.read_text())


def state_hash(s):
    return hashlib.sha256(json.dumps(s, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def run_git(*args, check=True, capture=False):
    return ev.run(['git', *args], cwd=ROOT, check=check, capture=capture, timeout=120)


def persist(paths: list[Path], message: str):
    uniq = []
    for p in paths:
        if p.exists() and p not in uniq:
            uniq.append(p)
    if not uniq:
        return
    run_git('add', *[str(p) for p in uniq])
    if run_git('diff', '--cached', '--quiet', check=False).returncode == 0:
        return
    run_git('commit', '-m', message)
    run_git('push', 'origin', f'HEAD:{CONTROL}')


def stop_check():
    run_git('fetch', '--no-tags', 'origin', CONTROL)
    if run_git('cat-file', '-e', f'origin/{CONTROL}:evolution5_lineage/STOP', check=False, capture=True).returncode == 0:
        raise StopIteration('lineage STOP present')


def genome(gid: str) -> dict:
    return load_genome_file(GENOMES / f'{gid}.json')['genome']


def allocate(state: dict, stream: str, maps: int, label: str) -> int:
    led = state['seed_ledger'][stream]
    start = int(led['next_seed'])
    led['next_seed'] = start + maps + 37
    led.setdefault('ranges', []).append({'label': label, 'start': start, 'maps': maps})
    return start


def wrapper(gid: str, out: Path) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = ['#!/usr/bin/env bash', 'set -euo pipefail']
    for k, v in env_for(genome(gid)).items():
        lines.append(f'export {k}={json.dumps(v)}')
    lines.append(f'exec {json.dumps(str(ROOT / AGENT / "run.sh"))}')
    out.write_text('\n'.join(lines) + '\n')
    out.chmod(0o755)
    return out


def compact(summary: dict) -> dict:
    return {
        'W': int(summary.get('W', 0)),
        'D': int(summary.get('D', 0)),
        'L': int(summary.get('L', 0)),
        'games': int(summary.get('games', 0)),
        'raw_win_rate': float(summary.get('raw_win_rate', 0.0)),
        'score': float(summary.get('score', 0.0)),
        'errors': int(summary.get('errors', 0)),
        'illegal_actions': int(summary.get('illegal_actions', 0)),
        'paired_ci95': list(summary.get('paired_ci95', [])),
        'decision_roundtrip_ms': dict(summary.get('decision_roundtrip_ms', {})),
    }


def timing_ok(summary: dict) -> bool:
    q = summary.get('decision_roundtrip_ms', {})
    return float(q.get('max', 0.0)) <= 150.0


def paired_ids(state: dict, cand: str, opp: str, stream: str, pairs: int, label: str, out: Path) -> dict:
    start = allocate(state, stream, pairs, label)
    c = wrapper(cand, out / f'{cand[:10]}-cand.sh')
    o = wrapper(opp, out / f'{opp[:10]}-opp.sh')
    s = ev.paired(c, o, start, pairs, out / 'games')
    q = compact(s)
    q['timing_ok'] = timing_ok(s)
    return q


def reference_score(state: dict, gid: str, generation: int, attempt: int, refs: list[dict], count: int) -> dict:
    if count <= 0 or not refs:
        return {'score': 0.0, 'raw_win_rate': 0.0, 'games': 0, 'summaries': {}}
    start_index = (generation * 3 + attempt * 5) % len(refs)
    chosen = [refs[(start_index + i) % len(refs)] for i in range(min(count, len(refs)))]
    cw = wrapper(gid, TMP / 'reference' / gid[:10] / 'candidate.sh')
    summaries = {}
    for i, r in enumerate(chosen):
        st = allocate(state, 'reference', 1, f'g{generation}-a{attempt}-ref-{r["archetype"]}')
        s = ev.paired(cw, Path(r['run']), st, 1, TMP / 'reference' / gid[:10] / f'{i}-{r["archetype"]}')
        summaries[r['archetype']] = s
    agg = ev.combine(list(summaries.values()))
    return {
        'score': float(agg.get('score', 0.0)),
        'raw_win_rate': float(agg.get('raw_win_rate', 0.0)),
        'games': int(agg.get('games', 0)),
        'summaries': {k: compact(v) for k, v in summaries.items()},
    }


def make_child(parent: dict, other: dict | None, rng: random.Random, kind: str, temperature: float, island: str) -> dict:
    if kind == 'micro':
        return micro_mutation(parent, rng, temperature)
    if kind == 'module':
        return module_mutation(parent, rng)
    if kind == 'graph':
        return graph_rewrite(parent, rng, min(.40, .25 + .05 * temperature))
    if kind == 'bundle':
        return strategy_bundle(parent, rng)
    if kind == 'immigrant':
        return random_immigrant(parent['params'], rng, island)
    if kind == 'crossover':
        return crossover_genomes(parent, other or parent, rng)
    raise ValueError(kind)


def create_challengers(state: dict) -> tuple[list[str], list[Path], dict[str, int]]:
    g = int(state['lineage_generation'])
    attempt = int(state['promotion_attempt']) + 1
    rng = random.Random(8800000 + g * 1009 + attempt * 97)
    temp = float(state.get('mutation_temperature', 1.0))
    mix = PLATEAU_MIX if int(state.get('failed_promotion_streak', 0)) >= 3 else NORMAL_MIX
    current = state['current_champion']
    pool = [x for x in state.get('champion_pool', []) if (GENOMES / f'{x}.json').exists()]
    diversity = [x for x in state.get('bootstrap_population', []) if (GENOMES / f'{x}.json').exists()]
    if current not in pool:
        pool.insert(0, current)
    known = set(p.name[:-5] for p in GENOMES.glob('*.json'))
    ids, created = [], []
    counts = {k: 0 for k in mix}
    for slot in range(64):
        island = ISLANDS[slot % len(ISLANDS)]
        r = rng.random()
        if r < 0.50:
            parent_id = current
        elif r < 0.85 and pool:
            parent_id = rng.choice(pool)
        elif diversity:
            parent_id = rng.choice(diversity)
        else:
            parent_id = current
        parent = genome(parent_id)
        kind = choose_kind(rng, mix)
        other_id = rng.choice(pool) if kind == 'crossover' and pool else parent_id
        child = make_child(parent, genome(other_id) if other_id else None, rng, kind, temp, island)
        for retry in range(50):
            gid = genome_id(child)
            if gid not in known:
                break
            child = graph_rewrite(child, rng, .35)
        else:
            raise RuntimeError('unable to create unique lineage challenger')
        known.add(gid)
        meta = {
            'lineage_generation_target': g + 1,
            'promotion_attempt': attempt,
            'lineage_parent': parent_id,
            'crossover_parent': other_id if kind == 'crossover' else None,
            'kind': kind,
            'island': island,
            'temperature': temp,
        }
        p = GENOMES / f'{gid}.json'
        save_genome(p, child, meta)
        ids.append(gid)
        created.append(p)
        counts[kind] += 1
    return ids, created, counts


def screen(state: dict, ids: list[str], refs: list[dict]) -> list[dict]:
    g = int(state['lineage_generation'])
    a = int(state['promotion_attempt']) + 1
    parent = state['current_champion']
    mix = opponent_mix(g)
    ref_count = 2 if mix['reference'] >= .50 else 1 if mix['reference'] > 0 else 0
    pgraph = genome(parent)['graph']

    def one(gid: str):
        m = paired_ids(state, gid, parent, 'screen', 4, f'g{g}-a{a}-screen-{gid[:8]}', TMP / 'screen' / gid[:10])
        ref = reference_score(state, gid, g, a, refs, ref_count) if ref_count else {'score': 0.0, 'raw_win_rate': 0.0, 'games': 0, 'summaries': {}}
        selection = mix['lineage'] * float(m['score']) + mix['reference'] * float(ref['score'])
        return {
            'genome_id': gid,
            'screen_parent': m,
            'reference': ref,
            'reference_score': float(ref['score']),
            'selection_score': selection,
            'novelty': float(graph_distance(genome(gid)['graph'], pgraph)),
        }

    # Seed allocation mutates state, so allocate/evaluate sequentially for strict deterministic ledgers.
    rows = [one(gid) for gid in ids]
    rows.sort(key=lambda r: (r['selection_score'], r['screen_parent']['raw_win_rate'], r['novelty']), reverse=True)
    return rows[:16]


def deep_lineage(state: dict, rows: list[dict]) -> list[dict]:
    g = int(state['lineage_generation'])
    a = int(state['promotion_attempt']) + 1
    ancestors = {
        1: state.get('current_champion'),
        2: state.get('previous_champion'),
        3: state.get('grandparent_champion'),
    }
    # 96 actual games vs parent, 64 vs grandparent, 48 vs great-grandparent.
    parent_rows = rows[:6]
    for r in parent_rows:
        q = paired_ids(state, r['genome_id'], ancestors[1], 'parent', 48, f'g{g}-a{a}-parent-{r["genome_id"][:8]}', TMP / 'deep-parent' / r['genome_id'][:10])
        r['matchups'] = {1: q}
    parent_rows.sort(key=lambda r: (r['matchups'][1]['raw_win_rate'], r['matchups'][1]['score'], r['novelty']), reverse=True)
    survivors = parent_rows[:4]
    if ancestors[2]:
        for r in survivors:
            r['matchups'][2] = paired_ids(state, r['genome_id'], ancestors[2], 'grandparent', 32, f'g{g}-a{a}-grand-{r["genome_id"][:8]}', TMP / 'deep-grand' / r['genome_id'][:10])
        survivors.sort(key=lambda r: (r['matchups'][1]['raw_win_rate'], r['matchups'][2]['raw_win_rate'], weighted_lineage_score(r['matchups'])), reverse=True)
    if ancestors[3]:
        for r in survivors:
            r['matchups'][3] = paired_ids(state, r['genome_id'], ancestors[3], 'great', 24, f'g{g}-a{a}-great-{r["genome_id"][:8]}', TMP / 'deep-great' / r['genome_id'][:10])
    for r in survivors:
        r['promotion_gate_passed'] = gate_pass(r['matchups']) and all(bool(x.get('timing_ok', False)) for x in r['matchups'].values())
        r['dominance_gate_passed'] = dominance_pass(r['matchups']) if len(r['matchups']) == 3 else False
        r['weighted_lineage_score'] = weighted_lineage_score(r['matchups'])
        r['minimum_lineage_score'] = minimum_lineage_score(r['matchups'])
    survivors.sort(key=promotion_key, reverse=True)
    return survivors


def watchdog(state: dict, gid: str, refs: list[dict]) -> dict:
    if not refs:
        return {}
    g = int(state['lineage_generation'])
    chosen = refs[:min(7, len(refs))]
    cw = wrapper(gid, TMP / 'watchdog' / 'candidate.sh')
    out = {}
    for r in chosen:
        st = allocate(state, 'watchdog', 2, f'g{g}-watchdog-{r["archetype"]}')
        s = ev.paired(cw, Path(r['run']), st, 2, TMP / 'watchdog' / r['archetype'])
        out[r['archetype']] = compact(s)
    return out


def gauntlet(state: dict, gid: str) -> dict:
    g = int(state['lineage_generation'])
    if g == 0 or g % 5 != 0:
        return {}
    hist = state.get('lineage_history', [])
    by_gen = {int(x['generation']): x['genome_id'] for x in hist}
    distances = [1, 2, 3, 5, 10]
    out = {}
    for d in distances:
        target_gen = g - d
        opp = by_gen.get(target_gen)
        if not opp:
            continue
        out[str(d)] = paired_ids(state, gid, opp, 'gauntlet', 8, f'g{g}-gauntlet-d{d}', TMP / 'gauntlet' / f'd{d}')
    return out


def freeze_promoted(state: dict, row: dict) -> list[Path]:
    g = int(state['lineage_generation'])
    gid = row['genome_id']
    z = CHECKPOINTS / f'lineage_g{g:03d}_{gid[:12]}_submission.zip'
    info = freeze_submission(genome(gid), ROOT, z)
    manifest = CHECKPOINTS / f'lineage_g{g:03d}_{gid[:12]}.json'
    dump(manifest, {
        'lineage_generation': g,
        'genome_id': gid,
        'matchups': row['matchups'],
        'promotion_gate_passed': row['promotion_gate_passed'],
        'dominance_gate_passed': row['dominance_gate_passed'],
        'submission': info,
        'state_hash': state_hash(state),
    })
    return [z, manifest]


def transaction(state: dict, txid: str):
    stop_check()
    ev.build(ROOT)
    refs = ev.resolve_opponents()
    g = int(state['lineage_generation'])
    attempt = int(state['promotion_attempt']) + 1
    shutil.rmtree(TMP, ignore_errors=True)
    dump(HEART, {
        'result': 'in_progress',
        'transaction_id': txid,
        'lineage_generation': g,
        'attempt': attempt,
        'current_champion': state['current_champion'],
        'challenger_status': 'creating_population',
        'start_time': now(),
    })
    persist([HEART], f'lineage: heartbeat g{g} attempt {attempt}')

    ids, created, mutation_counts = create_challengers(state)
    state['tested_challengers'] = int(state.get('tested_challengers', 0)) + len(ids)
    state['promotion_attempt'] = attempt
    screened = screen(state, ids, refs)
    finalists = deep_lineage(state, screened)
    promoted = next((r for r in finalists if r['promotion_gate_passed']), None)
    old_current = state['current_champion']
    checkpoint_paths = []
    watchdog_result = {}
    gauntlet_result = {}

    if promoted:
        new_gid = promoted['genome_id']
        old_prev = state.get('previous_champion')
        old_grand = state.get('grandparent_champion')
        state['great_grandparent_champion'] = old_grand
        state['grandparent_champion'] = old_prev
        state['previous_champion'] = old_current
        state['current_champion'] = new_gid
        state['lineage_generation'] = g + 1
        state['failed_promotion_streak'] = 0
        state['mutation_temperature'] = 1.0
        state['promotion_gate_passed'] = True
        state['dominance_gate_passed'] = bool(promoted['dominance_gate_passed'])
        state['vs_parent_win_rate'] = float(promoted['matchups'][1]['raw_win_rate'])
        state['vs_grandparent_win_rate'] = float(promoted['matchups'].get(2, {}).get('raw_win_rate', 0.0)) if 2 in promoted['matchups'] else None
        state['vs_great_grandparent_win_rate'] = float(promoted['matchups'].get(3, {}).get('raw_win_rate', 0.0)) if 3 in promoted['matchups'] else None
        state['lineage_hof'].append(new_gid)
        state['lineage_hof'] = state['lineage_hof'][-20:]
        # Keep several contemporaneous elites to avoid a single-champion bottleneck.
        elite_pool = [r['genome_id'] for r in finalists[:8]] + [new_gid, old_current]
        state['champion_pool'] = list(dict.fromkeys(elite_pool))[:8]
        entry = {
            'generation': g + 1,
            'genome_id': new_gid,
            'parent': old_current,
            'grandparent': old_prev,
            'great_grandparent': old_grand,
            'vs_parent': promoted['matchups'].get(1),
            'vs_grandparent': promoted['matchups'].get(2),
            'vs_great_grandparent': promoted['matchups'].get(3),
            'dominance': bool(promoted['dominance_gate_passed']),
            'attempt': attempt,
        }
        state['lineage_history'].append(entry)
        watchdog_result = watchdog(state, new_gid, refs)
        state['watchdog_history'].append({'generation': g + 1, 'results': watchdog_result})
        gauntlet_result = gauntlet(state, new_gid)
        if gauntlet_result:
            state['ancestor_gauntlets'].append({'generation': g + 1, 'results': gauntlet_result})
        checkpoint_paths = freeze_promoted(state, promoted)
    else:
        state['failed_promotion_streak'] = int(state.get('failed_promotion_streak', 0)) + 1
        state['mutation_temperature'] = min(2.5, 1.0 + .20 * state['failed_promotion_streak'])
        state['promotion_gate_passed'] = False
        state['dominance_gate_passed'] = False
        state['vs_parent_win_rate'] = float(finalists[0]['matchups'][1]['raw_win_rate']) if finalists else None
        state['vs_grandparent_win_rate'] = float(finalists[0]['matchups'].get(2, {}).get('raw_win_rate', 0.0)) if finalists and 2 in finalists[0]['matchups'] else None
        state['vs_great_grandparent_win_rate'] = float(finalists[0]['matchups'].get(3, {}).get('raw_win_rate', 0.0)) if finalists and 3 in finalists[0]['matchups'] else None

    result = {
        'transaction_id': txid,
        'attempt': attempt,
        'lineage_generation_before': g,
        'lineage_generation_after': int(state['lineage_generation']),
        'phase': phase(g),
        'opponent_mix': opponent_mix(g),
        'hard_gates': HARD_GATES,
        'dominance_targets': DOMINANCE_TARGETS,
        'mutation_counts': mutation_counts,
        'screened': screened,
        'finalists': finalists,
        'promoted': promoted['genome_id'] if promoted else None,
        'watchdog': watchdog_result,
        'ancestor_gauntlet': gauntlet_result,
    }
    state['attempt_history'].append({
        'attempt': attempt,
        'generation_before': g,
        'generation_after': int(state['lineage_generation']),
        'best_challenger': finalists[0]['genome_id'] if finalists else None,
        'promoted': promoted['genome_id'] if promoted else None,
        'best_vs_parent_win_rate': finalists[0]['matchups'][1]['raw_win_rate'] if finalists else None,
        'promotion_gate_passed': bool(promoted),
        'dominance_gate_passed': bool(promoted and promoted['dominance_gate_passed']),
    })
    state['attempt_history'] = state['attempt_history'][-100:]
    rp = RESULTS / f'attempt_{attempt:04d}_g{g:03d}.json'
    dump(rp, result)
    dump(STATE, state)
    dump(HEART, {
        'result': 'success',
        'transaction_id': txid,
        'completion_time': now(),
        'lineage_generation': int(state['lineage_generation']),
        'attempt': attempt,
        'current_champion': state['current_champion'],
        'challenger_status': 'promoted' if promoted else 'rejected_retry',
        'promoted': promoted['genome_id'] if promoted else None,
        'promotion_gate_passed': bool(promoted),
        'dominance_gate_passed': bool(promoted and promoted['dominance_gate_passed']),
        'state_hash': state_hash(state),
    })
    persist(created + [rp, STATE, HEART] + checkpoint_paths, f'lineage: complete g{g} attempt {attempt}' + (f' promote g{g+1}' if promoted else ' no-promotion'))
    return result


def main():
    ensure_bootstrap()
    state = load_state()
    txid = str(uuid.uuid4())
    try:
        transaction(state, txid)
    except StopIteration as e:
        dump(HEART, {
            'result': 'stopped',
            'lineage_generation': int(state.get('lineage_generation', 0)),
            'attempt': int(state.get('promotion_attempt', 0)),
            'current_champion': state.get('current_champion'),
            'challenger_status': str(e),
            'completion_time': now(),
        })
        persist([HEART], 'lineage: stopped')
        return
    except Exception as e:
        dump(HEART, {
            'result': 'failure',
            'transaction_id': txid,
            'lineage_generation': int(state.get('lineage_generation', 0)),
            'attempt': int(state.get('promotion_attempt', 0)) + 1,
            'current_champion': state.get('current_champion'),
            'challenger_status': type(e).__name__,
            'error': str(e),
            'completion_time': now(),
        })
        persist([HEART], 'lineage: transaction failure')
        raise


if __name__ == '__main__':
    main()
