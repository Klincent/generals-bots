#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path.cwd()
ORCH = ROOT / 'tools/evolution4/orchestrator.py'
TELEMETRY = ROOT / 'tools/evolution4/telemetry.py'
EVALUATOR = ROOT / 'tools/evolution4/evaluator.py'
STATE = ROOT / 'evolution4/state.json'
RESULTS = ROOT / 'evolution4/results'


def patch_telemetry() -> bool:
    text = TELEMETRY.read_text()
    if 'def _exploration_is_active() -> bool:' in text:
        return False
    text = text.replace('import re\n', 'import json\nimport re\n', 1)
    marker = 'from pathlib import Path\n\n'
    text = text.replace(marker, marker + "ROOT = Path(__file__).resolve().parents[2]\nSTATE = ROOT / 'evolution4' / 'state.json'\n\n", 1)
    old = 'def suggested_chromosome(t:dict, archetype_scores:dict|None=None) -> str|None:\n'
    helper = '''def _exploration_is_active() -> bool:\n    try:\n        s=json.loads(STATE.read_text())\n        return s.get('phase') == 'exploration'\n    except Exception:\n        return True\n\n'''
    if old not in text:
        raise SystemExit('suggested_chromosome marker not found')
    text = text.replace(old, helper + old + "    if _exploration_is_active():\n        return None\n", 1)
    TELEMETRY.write_text(text)
    return True


def patch_evaluator() -> bool:
    text = EVALUATOR.read_text()
    if 'BENCH RETRY' in text and '_PIN_LOCK' in text:
        return False
    text = text.replace('import json, os, shutil, subprocess, time\n', 'import json, os, shutil, subprocess, time, threading\n', 1)
    pin_marker = "PINNED_PAIRED=ROOT/'competition'/'evolution4_paired_benchmark_pinned.py'\n"
    if pin_marker not in text:
        raise SystemExit('evaluator pin marker not found')
    text = text.replace(pin_marker, pin_marker + '_PIN_LOCK=threading.Lock()\n', 1)
    old_ensure = '''def ensure_pinned_evaluator():\n    # Deterministic idempotent writes; safe when several evaluation threads call it.\n    matchup=_git_show(f'{EVAL_SHA}:competition/matchup.py')\n    paired_src=_git_show(f'{EVAL_SHA}:competition/agents/juraj_v35_cpp/paired_benchmark.py')\n    paired_src=paired_src.replace("'competition/matchup.py'", "'competition/evolution4_matchup_pinned.py'")\n    if "competition/evolution4_matchup_pinned.py" not in paired_src:\n        raise RuntimeError('failed to pin paired benchmark matchup path')\n    PINNED_MATCHUP.parent.mkdir(parents=True,exist_ok=True)\n    if not PINNED_MATCHUP.exists() or PINNED_MATCHUP.read_text()!=matchup:\n        PINNED_MATCHUP.write_text(matchup)\n    if not PINNED_PAIRED.exists() or PINNED_PAIRED.read_text()!=paired_src:\n        PINNED_PAIRED.write_text(paired_src)\n'''
    new_ensure = '''def ensure_pinned_evaluator():\n    # Four genome workers share these files: serialize materialization to avoid races.\n    with _PIN_LOCK:\n        matchup=_git_show(f'{EVAL_SHA}:competition/matchup.py')\n        paired_src=_git_show(f'{EVAL_SHA}:competition/agents/juraj_v35_cpp/paired_benchmark.py')\n        paired_src=paired_src.replace("'competition/matchup.py'", "'competition/evolution4_matchup_pinned.py'")\n        if "competition/evolution4_matchup_pinned.py" not in paired_src:\n            raise RuntimeError('failed to pin paired benchmark matchup path')\n        PINNED_MATCHUP.parent.mkdir(parents=True,exist_ok=True)\n        if not PINNED_MATCHUP.exists() or PINNED_MATCHUP.read_text()!=matchup:\n            PINNED_MATCHUP.write_text(matchup)\n        if not PINNED_PAIRED.exists() or PINNED_PAIRED.read_text()!=paired_src:\n            PINNED_PAIRED.write_text(paired_src)\n'''
    if old_ensure not in text:
        raise SystemExit('ensure_pinned_evaluator marker not found')
    text = text.replace(old_ensure, new_ensure, 1)
    start = text.index('def paired(candidate:Path,baseline:Path,start:int,seeds:int,out:Path)->dict:\n')
    end = text.index('\ndef combine(summaries:list[dict])->dict:\n', start)
    new_paired = '''def paired(candidate:Path,baseline:Path,start:int,seeds:int,out:Path)->dict:\n    ensure_pinned_evaluator()\n    cmd=['python',str(PINNED_PAIRED.relative_to(ROOT)),'--candidate',str(candidate),'--baseline',str(baseline),'--start',str(start),'--seeds',str(seeds),'--output',str(out)]\n    tag=str(out.relative_to(ROOT)) if out.is_relative_to(ROOT) else str(out)\n    timeout=max(420, int(seeds)*2*70+120)\n    for attempt in (1,2):\n        shutil.rmtree(out,ignore_errors=True); out.mkdir(parents=True,exist_ok=True)\n        print(f'[evolution4] BENCH START {tag} attempt={attempt} seeds={seeds} games={seeds*2} seed_start={start} timeout={timeout}s',flush=True)\n        t0=time.monotonic()\n        try:\n            p=run(cmd,check=False,capture=True,timeout=timeout)\n        except Exception as e:\n            print(f'[evolution4] BENCH TIMEOUT/ERROR {tag} attempt={attempt} elapsed={time.monotonic()-t0:.1f}s: {e}',flush=True)\n            if attempt==1:\n                print(f'[evolution4] BENCH RETRY {tag} reason=driver_exception',flush=True); continue\n            raise\n        (out/'driver.stdout').write_text(p.stdout); (out/'driver.stderr').write_text(p.stderr)\n        s=None\n        if (out/'summary.json').exists():\n            try: s=json.loads((out/'summary.json').read_text())\n            except Exception: s=None\n        illegal=int((s or {}).get('illegal_actions',0))\n        errors=int((s or {}).get('errors',0))\n        if p.returncode==0 and s is not None and not errors and not illegal:\n            print(f'[evolution4] BENCH DONE {tag} elapsed={time.monotonic()-t0:.1f}s W/D/L={s.get("W")}/{s.get("D")}/{s.get("L")} score={s.get("score",s.get("paired_score"))}',flush=True)\n            return s\n        games_tail=''\n        gp=out/'games.jsonl'\n        if gp.exists(): games_tail=gp.read_text(errors='ignore')[-4000:]\n        diagnostic=f'rc={p.returncode} errors={errors} illegal={illegal} stdout={p.stdout[-1500:]} stderr={p.stderr[-1500:]} games={games_tail}'\n        print(f'[evolution4] BENCH FAILED {tag} attempt={attempt} {diagnostic}',flush=True)\n        if illegal:\n            raise RuntimeError(f'benchmark illegal action: {diagnostic}')\n        if attempt==1:\n            evidence=out.with_name(out.name+'.attempt1')\n            shutil.rmtree(evidence,ignore_errors=True)\n            out.rename(evidence)\n            print(f'[evolution4] BENCH RETRY {tag} reason=infra_or_protocol_error',flush=True)\n            continue\n        raise RuntimeError(f'paired benchmark failed after retry: {diagnostic}')\n    raise RuntimeError('unreachable paired benchmark retry state')\n'''
    text = text[:start] + new_paired + text[end:]
    EVALUATOR.write_text(text)
    return True


def patch_orchestrator() -> bool:
    text = ORCH.read_text()
    if 'def dead_genome_ids(s):' in text and 'archive_generation_results(s,g,rows1,rows2,top4)' in text:
        return False
    marker = "def genome_values(gid): return load_genome(genome_path(gid))['values']\n"
    helper = r'''def dead_genome_ids(s):
    return {gid for gid,rec in s.get('tested_genomes',{}).items() if rec.get('status')=='dead'}

def archive_generation_results(s,g,rows1,rows2,top4):
    archive=s.setdefault('tested_genomes',{})
    stage2={r['genome_id']:r for r in rows2}
    survivors={r['genome_id'] for r in top4}
    for r in rows1:
        gid=r['genome_id']; rec=archive.setdefault(gid,{'first_tested_generation':g,'times_tested':0})
        rec['last_tested_generation']=g; rec['times_tested']=int(rec.get('times_tested',0))+1
        rec['stage1_score']=float(r.get('fitness',{}).get('aggregate',0.0))
        if gid in stage2: rec['stage2_score']=float(stage2[gid].get('fitness',{}).get('aggregate',0.0))
        rec['status']='survivor' if gid in survivors else 'dead'
    s['dead_genome_count']=sum(1 for x in archive.values() if x.get('status')=='dead')
    s['tested_genome_count']=len(archive)
    return dead_genome_ids(s)

'''
    if marker not in text: raise SystemExit('orchestrator genome_values marker not found')
    text=text.replace(marker,marker+helper,1)
    old="def next_population(top4,g):\n    rng=random.Random(880000+g); elites=[x['genome_id'] for x in top4]; known=set(elites); out=list(elites); vals=[genome_values(x) for x in elites]\n"
    new="def next_population(top4,g,dead_ids=None):\n    rng=random.Random(880000+g); elites=[x['genome_id'] for x in top4]; known=set(elites)|set(dead_ids or ()); out=list(elites); vals=[genome_values(x) for x in elites]\n"
    if old not in text: raise SystemExit('next_population marker not found')
    text=text.replace(old,new,1)
    old2="    nxt,elites,bias=next_population(top4,g); s['current_population']=nxt; s['breeding_elites']=elites; s['generation']=g\n"
    new2="    dead_ids=archive_generation_results(s,g,rows1,rows2,top4)\n    nxt,elites,bias=next_population(top4,g,dead_ids); s['current_population']=nxt; s['breeding_elites']=elites; s['generation']=g\n"
    if old2 not in text: raise SystemExit('generation next_population marker not found')
    text=text.replace(old2,new2,1)
    ORCH.write_text(text); return True


def backfill_state() -> bool:
    s=json.loads(STATE.read_text()); archive=s.setdefault('tested_genomes',{}); changed=False
    for p in sorted(RESULTS.glob('g*/report.json')):
        try: rep=json.loads(p.read_text())
        except Exception: continue
        g=int(rep.get('generation',0)); rows1=rep.get('stage1',[]); rows2={r.get('genome_id'):r for r in rep.get('stage2',[])}; top4=set(rep.get('top4',[]))
        for r in rows1:
            gid=r.get('genome_id')
            if not gid: continue
            rec=archive.setdefault(gid,{'first_tested_generation':g,'times_tested':0})
            rec['first_tested_generation']=min(int(rec.get('first_tested_generation',g)),g); rec['last_tested_generation']=max(int(rec.get('last_tested_generation',g)),g); rec['times_tested']=max(int(rec.get('times_tested',0)),1)
            rec['stage1_score']=float(r.get('fitness',{}).get('aggregate',0.0))
            if gid in rows2: rec['stage2_score']=float(rows2[gid].get('fitness',{}).get('aggregate',0.0))
            rec['status']='survivor' if gid in top4 else 'dead'; changed=True
    dead=sum(1 for rec in archive.values() if rec.get('status')=='dead')
    s['tested_genome_count']=len(archive); s['dead_genome_count']=dead
    s['genome_archive_policy']={'exact_dead_genome_retest':'forbidden','surviving_elite_retest':'allowed_on_fresh_seeds','near_neighbor_retest':'allowed','reason':'avoid exact dead-end repeats without over-pruning epistatic neighborhoods'}
    s['state_schema_version']=max(int(s.get('state_schema_version',1)),2)
    STATE.write_text(json.dumps(s,indent=2,sort_keys=True)+'\n'); return changed


if __name__=='__main__':
    t=patch_telemetry(); e=patch_evaluator(); a=patch_orchestrator(); b=backfill_state()
    print(f'[evolution4 migration] random={t} evaluator={e} archive={a} state={b}')
