from __future__ import annotations
from pathlib import Path


def once(s,old,new,label):
    n=s.count(old)
    if n!=1: raise RuntimeError(f'{label}: expected 1 match got {n}')
    return s.replace(old,new,1)

def main():
    p=Path('tools/evolution4/orchestrator.py'); s=p.read_text()
    if "CONTROL='evolution4/turbo-structural'" in s:
        print('turbo orchestrator already applied'); return
    s=once(s,"CONTROL='evolution4/control'; TEMPLATE='evolution4/template'; CHAMPION='evolution4/champion'","CONTROL='evolution4/turbo-structural'; TEMPLATE='evolution4/turbo-template'; CHAMPION='evolution4/turbo-champion'",'branch constants')
    s=once(s,"    if g>=30: s['phase']='final'\n    elif g>=12: s['phase']='exploitation'\n    else: s['phase']='exploration'","    if g>=60: s['phase']='final'\n    elif g>=20: s['phase']='exploitation'\n    else: s['phase']='exploration'",'turbo horizon')
    s=once(s,"    report={'generation':g,'phase':s['phase'],'stage1':rows1,'stage2':rows2,'top4':[x['genome_id'] for x in top4],'mutation_bias':bias,'promotion':evidence,'promoted_commit':prom}","    report={'generation':g,'phase':s['phase'],'mode':s.get('mode','turbo_structural'),'genome_schema_version':s.get('genome_schema_version',2),'stage1':rows1,'stage2':rows2,'top4':[x['genome_id'] for x in top4],'mutation_bias':bias,'promotion':evidence,'promoted_commit':prom}",'report metadata')
    p.write_text(s)
    print('turbo orchestrator applied')

if __name__=='__main__': main()
