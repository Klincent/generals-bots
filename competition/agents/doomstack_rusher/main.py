import sys
from dataclasses import dataclass
from typing import List
from agent import Agent

@dataclass
class Observation:
    H:int; W:int; turn:int; my_land:int; my_army:int; opp_land:int; opp_army:int
    type_grid:List[List[int]]; owner_grid:List[List[int]]; army_grid:List[List[int]]

def read_grid(stdin,H):
    return [[int(x) for x in stdin.readline().split()] for _ in range(H)]

def main():
    stdin=sys.stdin; stdout=sys.stdout
    hs=stdin.readline()
    if not hs: return
    player_id,H,W=(int(x) for x in hs.split())
    agent=Agent(player_id,H,W)
    while True:
        first=stdin.readline()
        if not first: return
        turn,my_land,my_army,opp_land,opp_army=(int(x) for x in first.split())
        obs=Observation(H,W,turn,my_land,my_army,opp_land,opp_army,
                        read_grid(stdin,H),read_grid(stdin,H),read_grid(stdin,H))
        p,r,c,d,s=agent.act(obs)
        stdout.write(f"{p} {r} {c} {d} {s}\n"); stdout.flush()

if __name__ == '__main__': main()
