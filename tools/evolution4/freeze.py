from __future__ import annotations
import re
from pathlib import Path
from .genome import canonical_values

NON_BEHAVIORAL={'picker_neutrals_max'}

def _lit(v):
    if isinstance(v,bool): return 'true' if v else 'false'
    if isinstance(v,int): return str(v)
    return format(float(v),'.12g')

def freeze_header(template_header:Path, values:dict, out_header:Path):
    s=template_header.read_text(); c=canonical_values(values)
    for name,v in c.items():
        if name in NON_BEHAVIORAL: continue
        pat=re.compile(r'(\b'+re.escape(name)+r'\s*=\s*)([^,;]+)')
        s2,n=pat.subn(lambda m:m.group(1)+_lit(v),s,count=1)
        if n!=1: raise RuntimeError(f'cannot freeze {name}: matches={n}')
        s=s2
    out_header.write_text(s)

def inline_for_submission(main_cpp:Path, header:Path, out_main:Path):
    s=main_cpp.read_text(); marker='#include "evolution4_genome.hpp"\n'
    if marker not in s: raise RuntimeError('genome header include missing')
    h=header.read_text()
    h=h.replace('#pragma once\n','',1)
    s=s.replace(marker,h+'\n',1)
    out_main.write_text(s)
