from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.evolution4.evaluator import ROOT
from tools.evolution5.freeze import freeze_submission
from tools.evolution5_lineage import orchestrator as b


def _rate(row: dict, distance: int) -> tuple[float, float]:
    q = (row.get('matchups') or {}).get(str(distance)) or (row.get('matchups') or {}).get(distance) or {}
    return float(q.get('raw_win_rate', 0.0)), float(q.get('score', 0.0))


def _best(rows: list[dict], distance: int) -> dict | None:
    eligible = [r for r in rows if str(distance) in (r.get('matchups') or {}) or distance in (r.get('matchups') or {})]
    if not eligible:
        return None
    return max(
        eligible,
        key=lambda r: (
            *_rate(r, distance),
            float(r.get('weighted_lineage_score', 0.0)),
            float(r.get('minimum_lineage_score', 0.0)),
            float(r.get('selection_score', 0.0)),
        ),
    )


def freeze_one(result: dict, row: dict, label: str, out_dir: Path) -> dict:
    attempt = int(result['attempt'])
    generation = int(result['lineage_generation_before'])
    gid = row['genome_id']
    base = f'attempt_{attempt:04d}_g{generation:03d}_{label}_{gid[:12]}'
    z = out_dir / f'{base}_submission.zip'
    info = freeze_submission(b.genome(gid), ROOT, z)
    manifest = out_dir / f'{base}.json'
    payload = {
        'attempt': attempt,
        'lineage_generation': generation,
        'label': label,
        'genome_id': gid,
        'matchups': row.get('matchups', {}),
        'g1': _rate(row, 1),
        'g2': _rate(row, 2) if (str(2) in (row.get('matchups') or {}) or 2 in (row.get('matchups') or {})) else None,
        'promotion_gate_passed': bool(row.get('promotion_gate_passed', False)),
        'evaluation_complete': bool(row.get('evaluation_complete', False)),
        'submission': info,
    }
    manifest.write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n')
    return payload


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--result', required=True)
    ap.add_argument('--out-dir', required=True)
    args = ap.parse_args()
    result_path = Path(args.result)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    result = json.loads(result_path.read_text())
    finalists = list(result.get('finalists') or [])
    if not finalists:
        raise SystemExit('result has no finalists')

    chosen: list[tuple[str, dict]] = []
    g1 = _best(finalists, 1)
    if g1 is not None:
        chosen.append(('best_g1', g1))
    g2 = _best(finalists, 2)
    if g2 is not None:
        chosen.append(('best_g2', g2))

    summaries = []
    for label, row in chosen:
        summaries.append(freeze_one(result, row, label, out_dir))
    (out_dir / 'summary.json').write_text(json.dumps(summaries, indent=2, sort_keys=True) + '\n')
    print(json.dumps(summaries, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
