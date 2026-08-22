from __future__ import annotations
import argparse, json, os, random, subprocess
from pathlib import Path

def transcript(seed:int, h:int=9, w:int=9, turns:int=140) -> str:
    rng=random.Random(seed); n=h*w
    types=[1]*n
    for x in rng.sample(range(1,n-1),8): types[x]=2
    types[0]=4; types[-1]=4
    lines=[f'1 {h} {w}']
    owner=[0]*n; army=[0]*n; owner[0]=1; owner[-1]=2; army[0]=1; army[-1]=1
    for t in range(turns):
        # Deterministic but varied observation stream. It intentionally need not be
        # a legal game replay: equivalence requires identical action for identical
        # state/history, so synthetic coverage is useful and reproducible.
        for i in range(n):
            if types[i]==2: owner[i]=-1; army[i]=0; continue
            r=rng.random()
            if i==0: owner[i]=1
            elif i==n-1: owner[i]=2
            elif r<.46: owner[i]=1
            elif r<.70: owner[i]=2
            else: owner[i]=0
            army[i]=rng.randint(1, max(2, 4+t//18)) if owner[i] in (1,2) else rng.randint(0,3)
        # Periodically create large rear stacks and threats to exercise picker,
        # muster and defense paths.
        if t%17==0:
            for i in (w-1,(h-1)*w,n//2):
                if types[i]!=2: owner[i]=1; army[i]=18+(t%40)
        if t%23==0:
            z=min(n-2,w+1); owner[z]=2; army[z]=12+(t%30)
        army[0]=max(2,5+t//30); army[-1]=max(2,4+t//35)
        my_land=sum(x==1 for x in owner); opp_land=sum(x==2 for x in owner)
        my_army=sum(a for a,o in zip(army,owner) if o==1); opp_army=sum(a for a,o in zip(army,owner) if o==2)
        lines.append(f'{t} {my_land} {my_army} {opp_land} {opp_army}')
        lines.append(' '.join(map(str,types))); lines.append(' '.join(map(str,owner))); lines.append(' '.join(map(str,army)))
    return '\n'.join(lines)+'\n'

def run(agent:Path, data:str, extra_env:dict[str,str]) -> tuple[str,str,int]:
    env=os.environ.copy(); env.update(extra_env)
    p=subprocess.run([str(agent)],input=data,text=True,capture_output=True,env=env,timeout=45)
    return p.stdout,p.stderr,p.returncode

def check(a:Path,b:Path,b_env:dict[str,str],seeds:int=12):
    for seed in range(91000,91000+seeds):
        data=transcript(seed)
        ao,ae,ar=run(a,data,{})
        bo,be,br=run(b,data,b_env)
        if ar or br: raise SystemExit(f'process failure seed={seed} a={ar} b={br}')
        al=ao.splitlines(); bl=bo.splitlines()
        if al!=bl:
            m=min(len(al),len(bl)); idx=next((i for i in range(m) if al[i]!=bl[i]),m)
            raise SystemExit(f'action mismatch seed={seed} index={idx} a={al[idx] if idx<len(al) else "<end>"} b={bl[idx] if idx<len(bl) else "<end>"}')
    print(f'equivalent: {seeds} transcripts')

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--original',type=Path,required=True); ap.add_argument('--template',type=Path,required=True); ap.add_argument('--env-json',default='{}'); ap.add_argument('--seeds',type=int,default=12)
    x=ap.parse_args(); check(x.original,x.template,{k:str(v) for k,v in json.loads(x.env_json).items()},x.seeds)
if __name__=='__main__': main()
