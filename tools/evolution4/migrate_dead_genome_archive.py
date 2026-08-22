#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path.cwd()
ORCH = ROOT / 'tools/evolution4/orchestrator.py'
STATE = ROOT / 'evolution4/state.json'
RESULTS = ROOT / 'evolution4/results'


def patch_orchestrator() -> bool:
    text = ORCH.read_text()
    if 'def dead_genome_ids(s):' in text and 'archive_generation_results(s,g,rows1,rows2,top4)' in text:
        return False

    marker = "def genome_values(gid): return load_genome(genome_path(gid))['values']\n"
    helper = r'''def dead_genome_ids(s):
    return {gid for gid,rec in s.get('tested_genomes',{}).items() if rec.get('status')=='dead'}

def archive_generation_results(s,g,rows1,rows2,top4):
    """Persist exact tested genotypes. Survivors may be retested; dead genotypes are tabu forever."""
    archive=s.setdefault('tested_genomes',{})
    stage2={r['genome_id']:r for r in rows2}
    survivors={r['genome_id'] for r in top4}
    for r in rows1:
        gid=r['genome_id']; rec=archive.setdefault(gid,{'first_tested_generation':g,'times_tested':0})
        rec['last_tested_generation']=g
        rec['times_tested']=int(rec.get('times_tested',0))+1
        rec['stage1_score']=float(r.get('fitness',{}).get('aggregate',0.0))
        if gid in stage2:
            rec['stage2_score']=float(stage2[gid].get('fitness',{}).get('aggregate',0.0))
        rec['status']='survivor' if gid in survivors else 'dead'
    s['dead_genome_count']=sum(1 for x in archive.values() if x.get('status')=='dead')
    s['tested_genome_count']=len(archive)
    return dead_genome_ids(s)

'''
    if marker not in text:
        raise SystemExit('orchestrator genome_values marker not found')
    text = text.replace(marker, marker + helper, 1)

    old = "def next_population(top4,g):\n    rng=random.Random(880000+g); elites=[x['genome_id'] for x in top4]; known=set(elites); out=list(elites); vals=[genome_values(x) for x in elites]\n"
    new = "def next_population(top4,g,dead_ids=None):\n    rng=random.Random(880000+g); elites=[x['genome_id'] for x in top4]; known=set(elites)|set(dead_ids or ()); out=list(elites); vals=[genome_values(x) for x in elites]\n"
    if old not in text:
        raise SystemExit('next_population marker not found')
    text = text.replace(old, new, 1)

    old2 = "    nxt,elites,bias=next_population(top4,g); s['current_population']=nxt; s['breeding_elites']=elites; s['generation']=g\n"
    new2 = "    dead_ids=archive_generation_results(s,g,rows1,rows2,top4)\n    nxt,elites,bias=next_population(top4,g,dead_ids); s['current_population']=nxt; s['breeding_elites']=elites; s['generation']=g\n"
    if old2 not in text:
        raise SystemExit('generation next_population marker not found')
    text = text.replace(old2, new2, 1)

    old3 = "    report={'generation':g,'phase':s['phase'],'stage1':rows1,'stage2':rows2,'top4':[x['genome_id'] for x in top4],'mutation_bias':bias,'promotion':evidence,'promoted_commit':prom};"
    new3 = "    report={'generation':g,'phase':s['phase'],'stage1':rows1,'stage2':rows2,'top4':[x['genome_id'] for x in top4],'mutation_bias':bias,'tested_genome_count':s.get('tested_genome_count',0),'dead_genome_count':s.get('dead_genome_count',0),'promotion':evidence,'promoted_commit':prom};"
    if old3 in text:
        text = text.replace(old3, new3, 1)

    ORCH.write_text(text)
    return True


def backfill_state() -> bool:
    s = json.loads(STATE.read_text())
    archive = s.setdefault('tested_genomes', {})
    changed = False
    # Backfill every completed generation report already persisted before this migration.
    for p in sorted(RESULTS.glob('g*/report.json')):
        try:
            rep = json.loads(p.read_text())
        except Exception:
            continue
        g = int(rep.get('generation', 0))
        rows1 = rep.get('stage1', [])
        rows2 = {r.get('genome_id'): r for r in rep.get('stage2', [])}
        top4 = set(rep.get('top4', []))
        for r in rows1:
            gid = r.get('genome_id')
            if not gid:
                continue
            rec = archive.setdefault(gid, {'first_tested_generation': g, 'times_tested': 0})
            rec['first_tested_generation'] = min(int(rec.get('first_tested_generation', g)), g)
            rec['last_tested_generation'] = max(int(rec.get('last_tested_generation', g)), g)
            rec['times_tested'] = max(int(rec.get('times_tested', 0)), 1)
            rec['stage1_score'] = float(r.get('fitness', {}).get('aggregate', 0.0))
            if gid in rows2:
                rec['stage2_score'] = float(rows2[gid].get('fitness', {}).get('aggregate', 0.0))
            rec['status'] = 'survivor' if gid in top4 else 'dead'
            changed = True
    dead = sum(1 for rec in archive.values() if rec.get('status') == 'dead')
    if s.get('tested_genome_count') != len(archive) or s.get('dead_genome_count') != dead:
        changed = True
    s['tested_genome_count'] = len(archive)
    s['dead_genome_count'] = dead
    s['genome_archive_policy'] = {
        'exact_dead_genome_retest': 'forbidden',
        'surviving_elite_retest': 'allowed_on_fresh_seeds',
        'near_neighbor_retest': 'allowed',
        'reason': 'avoid exact dead-end repeats without over-pruning epistatic neighborhoods'
    }
    s['state_schema_version'] = max(int(s.get('state_schema_version', 1)), 2)
    STATE.write_text(json.dumps(s, indent=2, sort_keys=True) + '\n')
    return changed


if __name__ == '__main__':
    a = patch_orchestrator()
    b = backfill_state()
    print(f'[evolution4 migration] dead-genome archive orchestrator_changed={a} state_changed={b}')
