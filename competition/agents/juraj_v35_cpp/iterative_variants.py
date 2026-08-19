#!/usr/bin/env python3
import argparse
from pathlib import Path


def one(s: str, old: str, new: str, label: str) -> str:
    n = s.count(old)
    if n != 1:
        raise SystemExit(f"{label}: expected exactly one anchor, found {n}")
    return s.replace(old, new, 1)


def stage1(s: str) -> str:
    """Immediate recapture only: previously-owned enemy castle + adjacent safe winning stack."""
    s = one(
        s,
        'std::map<long,Packet>packets_;std::vector<long>packet_at_;std::vector<int>last_owner_,last_army_,land_hist_,opp_land_hist_,opp_army_hist_;std::deque<ExecutedMove>actions_;',
        'std::map<long,Packet>packets_;std::vector<long>packet_at_;std::vector<char>owned_castle_history_;std::vector<int>last_owner_,last_army_,land_hist_,opp_land_hist_,opp_army_hist_;std::deque<ExecutedMove>actions_;',
        'stage1 history member',
    )
    s = one(
        s,
        'last_owner_=o.owner;last_army_=o.army;packet_at_.assign(n_,0);std::fprintf(stderr,',
        'last_owner_=o.owner;last_army_=o.army;packet_at_.assign(n_,0);owned_castle_history_.assign(n_,0);for(int x=0;x<n_;++x)if(o.owner[x]==1&&o.type[x]==3)owned_castle_history_[x]=1;std::fprintf(stderr,',
        'stage1 init history',
    )
    s = one(
        s,
        'Action act(const Observation&o){auto begin=std::chrono::steady_clock::now();if(g_.passable.empty())init(o);else reconcile(o);',
        'Action act(const Observation&o){auto begin=std::chrono::steady_clock::now();if(g_.passable.empty())init(o);else reconcile(o);for(int x=0;x<n_;++x)if(o.owner[x]==1&&o.type[x]==3)owned_castle_history_[x]=1;',
        'stage1 history refresh',
    )
    anchor = 'if(immediate)for(int x=0;x<n_;++x)if(source(o,x)){int y=tactical_next(o,x,general_);if(y>=0&&o.owner[y]==1)c.push_back({0,x,y,0,double(o.army[x]),Reason::GENERAL_EMERGENCY,false,ActionClass::HARD,general_,-1,PacketRole::GENERAL_DEFENSE});}\n  for(auto [site,f,index]:'
    repl = 'if(immediate)for(int x=0;x<n_;++x)if(source(o,x)){int y=tactical_next(o,x,general_);if(y>=0&&o.owner[y]==1)c.push_back({0,x,y,0,double(o.army[x]),Reason::GENERAL_EMERGENCY,false,ActionClass::HARD,general_,-1,PacketRole::GENERAL_DEFENSE});}\n  for(int t=0;t<n_;++t)if(owned_castle_history_[t]&&o.type[t]==3&&o.owner[t]==2)for(int d=0;d<4;++d){int x=g_.neighbor(t,d);if(source(o,x)&&safe_attack(o,x,t))c.push_back({1,x,t,0,9500.-o.army[x]*.01,Reason::CASTLE_INVALIDATED,false,ActionClass::HARD,t,-1,PacketRole::COUNTERATTACK});}\n  for(auto [site,f,index]:'
    return one(s, anchor, repl, 'stage1 recapture candidate')


def stage2(s: str) -> str:
    """Visible one-move threatened own-castle defense: safe intercept or sufficient local reinforcement."""
    anchor = '  for(int t=0;t<n_;++t)if(owned_castle_history_[t]&&o.type[t]==3&&o.owner[t]==2)for(int d=0;d<4;++d){int x=g_.neighbor(t,d);if(source(o,x)&&safe_attack(o,x,t))c.push_back({1,x,t,0,9500.-o.army[x]*.01,Reason::CASTLE_INVALIDATED,false,ActionClass::HARD,t,-1,PacketRole::COUNTERATTACK});}\n  for(auto [site,f,index]:'
    if anchor not in s:
        # Allow standalone stage2 during diagnostics by inserting before castle planner.
        anchor = '  for(auto [site,f,index]:'
        prefix = ''
    else:
        prefix = '  for(int t=0;t<n_;++t)if(owned_castle_history_[t]&&o.type[t]==3&&o.owner[t]==2)for(int d=0;d<4;++d){int x=g_.neighbor(t,d);if(source(o,x)&&safe_attack(o,x,t))c.push_back({1,x,t,0,9500.-o.army[x]*.01,Reason::CASTLE_INVALIDATED,false,ActionClass::HARD,t,-1,PacketRole::COUNTERATTACK});}\n'
    defense = '  for(int t=0;t<n_;++t)if(o.type[t]==3&&o.owner[t]==1){for(int de=0;de<4;++de){int e=g_.neighbor(t,de);if(e<0||o.owner[e]!=2||o.army[e]<=1||o.army[e]-1<=o.army[t])continue;for(int dx=0;dx<4;++dx){int x=g_.neighbor(e,dx);if(source(o,x)&&x!=t&&safe_attack(o,x,e))c.push_back({1,x,e,0,9400.-o.army[x]*.01,Reason::CASTLE_INVALIDATED,false,ActionClass::HARD,t,-1,PacketRole::COUNTERATTACK});}for(int dx=0;dx<4;++dx){int x=g_.neighbor(t,dx);if(x<0||x==general_||!source(o,x)||o.owner[x]!=1)continue;int defended=o.army[t]+o.army[x]-1;if(defended>=o.army[e]-1)c.push_back({1,x,t,0,9300.+defended-o.army[e],Reason::CASTLE_INVALIDATED,false,ActionClass::HARD,t,-1,PacketRole::GENERAL_DEFENSE});}}}\n'
    if prefix:
        return one(s, anchor, prefix + defense + '  for(auto [site,f,index]:', 'stage2 local castle defense')
    return one(s, anchor, defense + '  for(auto [site,f,index]:', 'stage2 local castle defense standalone')


def stage3(s: str) -> str:
    """Tiny wall/corner tie-breaker: only among equally short safe logistics steps."""
    needle = ' int tactical_next(const Observation&o,int x,int target)const{int best=-1,bd=INF;for(int d=0;d<4;++d){int y=g_.neighbor(x,d);if(safe_step(o,x,y)&&g_.dist[y][target]<bd)best=y,bd=g_.dist[y][target];}return best;}\n'
    helper = ' int tactical_next_logistics(const Observation&o,int x,int target)const{int best=-1,bd=INF,be=-1,bdeg=-1;for(int d=0;d<4;++d){int y=g_.neighbor(x,d);if(!safe_step(o,x,y))continue;int dd=g_.dist[y][target];int edge=std::min({y/w_,h_-1-y/w_,y%w_,w_-1-y%w_}),deg=g_.degree(y);if(dd<bd||(dd==bd&&(edge>be||(edge==be&&(deg>bdeg||(deg==bdeg&&(best<0||y<best))))))){best=y;bd=dd;be=edge;bdeg=deg;}}return best;}\n'
    s = one(s, needle, needle + helper, 'stage3 helper')
    old = 'int target=sink==x?general_:sink,y=target>=0?tactical_next(o,x,target):-1;'
    new = 'int target=sink==x?general_:sink,y=target>=0?tactical_next_logistics(o,x,target):-1;'
    return one(s, old, new, 'stage3 logistics-only next-step tie break')


def stage4(s: str) -> str:
    """Two-turn local combine for visible enemy castle/general when next-turn capture is mathematically available."""
    anchor = '  // A local attack that exactly defeats a qualified threat is a hard emergency.\n'
    code = '  for(int t=0;t<n_;++t)if(o.owner[t]==2&&(o.type[t]==3||o.type[t]==4)){for(int ds=0;ds<4;++ds){int st=g_.neighbor(t,ds);if(st<0||st==general_||o.owner[st]!=1||!source(o,st)||safe_attack(o,st,t))continue;for(int df=0;df<4;++df){int f=g_.neighbor(st,df);if(f<0||f==general_||f==t||!source(o,f)||o.owner[f]!=1)continue;int projected=o.army[st]+o.army[f]-1;if(projected-1<=o.army[t]+1)continue;int cover=0;for(int dz=0;dz<4;++dz){int z=g_.neighbor(st,dz);if(z>=0&&z!=t&&o.owner[z]==2)cover=std::max(cover,o.army[z]);}if(cover>=projected-1)continue;c.push_back({1,f,st,0,8500.+(o.type[t]==4?400.:0.)+projected-o.army[t],Reason::OPPONENT_EXPLOIT,false,ActionClass::HARD,t,-1,PacketRole::ATTACK});}}}\n'
    return one(s, anchor, code + anchor, 'stage4 tactical combine')


def stage5(s: str) -> str:
    """Conservative conversion: boost only an already-existing attack/front spearhead under a large confirmed lead."""
    old = 'const Front*front=fronts_.primary();int sink=belief_.confirmed()?belief_.confirmed_cell():(front?front->anchor:belief_.top());for(int x=0;x<n_;++x)if(source(o,x)){'
    new = 'const Front*front=fronts_.primary();int sink=belief_.confirmed()?belief_.confirmed_cell():(front?front->anchor:belief_.top());bool finishing_lead=meaningful_contact_turn_>=0&&confirmed_war&&sink>=0&&o.my_land*2>=o.opp_land*3&&o.my_army*3>=o.opp_army*4;int spearhead=-1,spear_score=-INF;if(finishing_lead)for(int x=0;x<n_;++x)if(source(o,x)){auto p=packet_for(x);if(!p||(p->role!=PacketRole::ATTACK&&p->role!=PacketRole::FRONT))continue;int sc=o.army[x]*4-2*g_.dist[x][sink];if(sc>spear_score)spear_score=sc,spearhead=x;}for(int x=0;x<n_;++x)if(source(o,x)){'
    s = one(s, old, new, 'stage5 spearhead selection')
    old2 = 'if(y<0)continue;if(confirmed_war&&b.war>0)c.push_back({2,x,y,0,double(surplus)/std::max(1,g_.dist[x][target]),Reason::WAR_MOBILIZATION,false,ActionClass::LOGISTICS,target,front?front->id:-1,PacketRole::FRONT});'
    new2 = 'if(y<0)continue;double war_u=double(surplus)/std::max(1,g_.dist[x][target]);if(finishing_lead&&x==spearhead)war_u+=8.;if(confirmed_war&&b.war>0)c.push_back({2,x,y,0,war_u,Reason::WAR_MOBILIZATION,false,ActionClass::LOGISTICS,target,front?front->id:-1,PacketRole::FRONT});'
    return one(s, old2, new2, 'stage5 bounded spearhead preference')


STAGES = {1: stage1, 2: stage2, 3: stage3, 4: stage4, 5: stage5}
NAMES = {
    1: 'immediate_lost_castle_recapture',
    2: 'local_threatened_castle_defense',
    3: 'wall_corner_shortest_path_tiebreak',
    4: 'two_turn_local_combine',
    5: 'bounded_winning_conversion_spearhead',
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--stage', type=int, choices=sorted(STAGES), required=True)
    ap.add_argument('--input', required=True)
    ap.add_argument('--output', required=True)
    args = ap.parse_args()
    src = Path(args.input).read_text()
    out = STAGES[args.stage](src)
    if out == src:
        raise SystemExit('stage produced no change')
    # Global guards against mechanisms already proven harmful.
    forbidden = ('castle_opportunity_', 'castle_target_', 'staging_point(', 'rear_pressure(')
    for token in forbidden:
        if token in out:
            raise SystemExit(f'forbidden experimental mechanism present: {token}')
    Path(args.output).write_text(out)
    print(f'stage={args.stage} name={NAMES[args.stage]} bytes={len(out)}')


if __name__ == '__main__':
    main()
