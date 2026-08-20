"""Parameterized adversarial stress opponent for picker9 validation.

Modes are intentionally simple and deterministic.  They are not candidate code;
they exist to expose different failure modes: one huge carrier, earlier rush,
continuous territorial flooding, and fast direct pressure.
"""
from collections import deque
import os
import sys

PASS=(1,0,0,0,0)
DIRS=[(-1,0),(1,0),(0,-1),(0,1)]

def passable(t): return t not in (2,5)

class Agent:
    def __init__(self,player_id,H,W):
        self.player_id=player_id; self.H=H; self.W=W
        self.rally=None; self.attack=False; self.own_general=None; self.last_enemy_general=None
        self.mode=os.environ.get("STRESS_MODE","doomstack").strip().lower()
        if self.mode not in {"doomstack","earlyrush","pressure","flood"}:
            self.mode="doomstack"

    def owned(self,o):
        return [(r,c) for r in range(o.H) for c in range(o.W) if o.owner_grid[r][c]==1]

    def largest(self,o):
        return max(self.owned(o),key=lambda p:o.army_grid[p[0]][p[1]],default=None)

    def direction(self,a,b):
        d=(b[0]-a[0],b[1]-a[1])
        return DIRS.index(d) if d in DIRS else 0

    def owned_dist(self,o,target):
        dist={target:0}; q=deque([target])
        while q:
            r,c=q.popleft()
            for dr,dc in DIRS:
                p=(r+dr,c+dc); nr,nc=p
                if 0<=nr<o.H and 0<=nc<o.W and p not in dist and o.owner_grid[nr][nc]==1:
                    dist[p]=dist[(r,c)]+1; q.append(p)
        return dist

    def path_step(self,o,src,target):
        if src==target:return None
        prev={src:None}; q=deque([src])
        while q:
            cur=q.popleft()
            if cur==target:break
            r,c=cur; ns=[]
            for d,(dr,dc) in enumerate(DIRS):
                nr,nc=r+dr,c+dc
                if 0<=nr<o.H and 0<=nc<o.W and passable(o.type_grid[nr][nc]):
                    p=(nr,nc); ns.append((abs(nr-target[0])+abs(nc-target[1]),d,p))
            for _,_,p in sorted(ns):
                if p not in prev: prev[p]=cur; q.append(p)
        if target not in prev:return None
        cur=target
        while prev[cur]!=src:
            cur=prev[cur]
            if cur is None:return None
        return cur

    def expand(self,o):
        best=None; bs=-10**9
        for r,c in self.owned(o):
            a=o.army_grid[r][c]
            if a<=1:continue
            for d,(dr,dc) in enumerate(DIRS):
                nr,nc=r+dr,c+dc
                if not(0<=nr<o.H and 0<=nc<o.W) or not passable(o.type_grid[nr][nc]):continue
                if o.owner_grid[nr][nc]==1:continue
                if a<=o.army_grid[nr][nc]+1:continue
                owner=o.owner_grid[nr][nc]; typ=o.type_grid[nr][nc]
                score=a+(50000 if typ==4 else 0)+(12000 if owner==2 else 3000 if typ not in (0,5) else 1200)
                if score>bs:bs=score;best=(0,r,c,d,0)
        return best

    def target(self,o,carrier):
        enemies=[]; eg=None
        for r in range(o.H):
            for c in range(o.W):
                if o.owner_grid[r][c]==2:
                    enemies.append((r,c))
                    if o.type_grid[r][c]==4:eg=(r,c)
        if eg is not None:self.last_enemy_general=eg;return eg
        if self.last_enemy_general is not None:return self.last_enemy_general
        if enemies:return min(enemies,key=lambda p:abs(p[0]-carrier[0])+abs(p[1]-carrier[1]))
        if self.own_general is None:
            for p in self.owned(o):
                if o.type_grid[p[0]][p[1]]==4:self.own_general=p;break
        g=self.own_general or carrier
        corners=[(0,0),(0,o.W-1),(o.H-1,0),(o.H-1,o.W-1)]
        return max(corners,key=lambda p:abs(p[0]-g[0])+abs(p[1]-g[1]))

    def trace(self,o,phase,carrier,feeders=0):
        if o.turn%25:return
        ca=0 if carrier is None else o.army_grid[carrier[0]][carrier[1]]
        sys.stderr.write(f"[stress_opponent] mode={self.mode} turn={o.turn} phase={phase} carrier={ca} share={ca/max(1,o.my_army):.3f} my_army={o.my_army} my_land={o.my_land} feeders={feeders}\n");sys.stderr.flush()

    def direct_pressure(self,o,minimum=2):
        carrier=self.largest(o)
        self.trace(o,"pressure",carrier)
        if carrier is None or o.army_grid[carrier[0]][carrier[1]]<minimum:return self.expand(o) or PASS
        step=self.path_step(o,carrier,self.target(o,carrier))
        if step is None:return self.expand(o) or PASS
        r,c=carrier
        return (0,r,c,self.direction(carrier,step),0)

    def act(self,o):
        for p in self.owned(o):
            if o.type_grid[p[0]][p[1]]==4:self.own_general=p;break

        # Flood never consolidates: it maximizes map/contact tempo and always
        # prioritizes capturable enemy/general cells through expand() scoring.
        if self.mode=="flood":
            c=self.largest(o); self.trace(o,"flood",c)
            return self.expand(o) or self.direct_pressure(o,2)

        # Pressure creates repeated medium packets very early.  This catches a
        # defender that only reacts once a single doomstack is already huge.
        if self.mode=="pressure":
            if o.turn<55:
                c=self.largest(o); self.trace(o,"expand",c)
                return self.expand(o) or PASS
            return self.direct_pressure(o,12)

        expand_until=125
        ready_abs=90; ready_share=.48; force_turn=500; force_abs=70
        if self.mode=="earlyrush":
            expand_until=75; ready_abs=52; ready_share=.34; force_turn=260; force_abs=38

        if o.turn<expand_until:
            c=self.largest(o);self.trace(o,"expand",c)
            return self.expand(o) or PASS

        if self.rally is None or o.owner_grid[self.rally[0]][self.rally[1]]!=1:
            self.rally=self.largest(o)
        if self.rally is None:return PASS

        ca=o.army_grid[self.rally[0]][self.rally[1]]
        ready=(ca>=ready_abs and ca>=int(ready_share*max(1,o.my_army)))
        forced=(o.turn>=force_turn and ca>=force_abs)
        if ready or forced:self.attack=True

        if not self.attack:
            dist=self.owned_dist(o,self.rally); feeders=[]
            min_stack=3 if o.turn<175 else 2
            if self.mode=="earlyrush": min_stack=2
            for p,d in dist.items():
                if p==self.rally or d<=0:continue
                a=o.army_grid[p[0]][p[1]]
                if a<min_stack:continue
                feeders.append(((a-1)*100-d*3,a,-d,p))
            self.trace(o,"harvest",self.rally,len(feeders))
            if feeders:
                *_,src=max(feeders); sd=dist[src]; r,c=src
                opts=[]
                for direction,(dr,dc) in enumerate(DIRS):
                    p=(r+dr,c+dc)
                    if dist.get(p,10**9)==sd-1:opts.append((direction,p))
                if opts:return (0,r,c,min(opts)[0],0)
            m=self.expand(o)
            if m is not None:return m
            return PASS

        if o.owner_grid[self.rally[0]][self.rally[1]]!=1:
            self.rally=self.largest(o)
            if self.rally is None:return PASS
        carrier=self.rally; self.trace(o,"attack",carrier)
        if o.army_grid[carrier[0]][carrier[1]]<=1:return PASS
        step=self.path_step(o,carrier,self.target(o,carrier))
        if step is None:return self.expand(o) or PASS
        r,c=carrier; d=self.direction(carrier,step); self.rally=step
        return (0,r,c,d,0)
