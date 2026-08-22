from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / 'evolution4' / 'genome_schema.json'
STRUCTURAL_PATH = ROOT / 'evolution4' / 'structural_genes.json'

def load_schema(path: Path = SCHEMA_PATH):
    data = json.loads(path.read_text())
    genes = list(data['genes'])
    if path == SCHEMA_PATH and STRUCTURAL_PATH.exists():
        structural = json.loads(STRUCTURAL_PATH.read_text())
        genes.extend(structural.get('genes', []))
        data = dict(data)
        data['version'] = max(int(data.get('version', 1)), int(structural.get('version', 2)))
        data['genes'] = genes
    by_name = {g['name']: g for g in genes}
    if len(by_name) != len(genes):
        raise ValueError('duplicate gene names')
    return data, by_name

def defaults():
    data, _ = load_schema()
    return {g['name']: g['default'] for g in data['genes']}

def chromosomes():
    data, _ = load_schema()
    out = {}
    for g in data['genes']:
        out.setdefault(g['chromosome'], []).append(g['name'])
    return out
