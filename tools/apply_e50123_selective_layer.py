#!/usr/bin/env python3
from pathlib import Path
import re

MAIN=Path('competition/agents/juraj_v35_cpp/main.cpp')
CORE=Path('competition/agents/juraj_v35_cpp/core.hpp')
m=MAIN.read_text(); c=CORE.read_text()

def rep(text, old, new, label):
    if new in text:
        print(label+': already applied'); return text
    n=text.count(old)
    if n != 1:
        raise SystemExit(f'{label}: expected 1 anchor, found {n}')
    print(label+': applied')
    return text.replace(old,new,1)

# Reapply the tactical pieces that made e50123 the selected V3.5 submission,
# without replacing the later picker / 3x3 exploration code.
m=rep(m,
'''std::map<long,Packet>packets_;std::vector<long>packet_at_;std::vector<int>last_owner_,last_army_,land_hist_,opp_land_hist_,opp_army_hist_;std::deque<ExecutedMove>actions_;''',
'''std::map<long,Packet>packets_;std::vector<long>packet_at_;std::vector<char>owned_castle_history_;std::vector<int>last_owner_,last_army_,land_hist_,opp_land_hist_,opp_army_hist_;std::deque<ExecutedMove>actions_;''',
'owned castle history field')

m=rep(m,
'''packet_at_.assign(n_,0);init_sector_exploration();''',
'''packet_at_.assign(n_,0);owned_castle_history_.assign(n_,0);for(int x=0;x<n_;++x)if(o.owner[x]==1&&o.type[x]==3)owned_castle_history_[x]=1;init_sector_exploration();''',
'owned castle history turn-zero init')

old_tactical='''int tactical_next(const Observation&o,int x,int target)const{int best=-1,bd=INF;for(int d=0;d<4;++d){int y=g_.neighbor(x,d);if(safe_step(o,x,y)&&g_.dist[y][target]<bd)best=y,bd=g_.dist[y][target];}return best;}'''
new_tactical=old_tactical+'''\n int tactical_next_logistics(const Observation&o,int x,int target)const{int best=-1,bd=INF,be=-1,bdeg=-1;for(int d=0;d<4;++d){int y=g_.neighbor(x,d);if(!safe_step(o,x,y))continue;int dd=g_.dist[y][target];int edge=std::min({y/w_,h_-1-y/w_,y%w_,w_-1-y%w_}),deg=g_.degree(y);if(dd<bd||(dd==bd&&(edge>be||(edge==be&&(deg>bdeg||(deg==bdeg&&(best<0||y<best))))))){best=y;bd=dd;be=edge;bdeg=deg;}}return best;}'''
m=rep(m,old_tactical,new_tactical,'e50123 logistics tie-break')

m=rep(m,
'''if(g_.passable.empty())init(o);else reconcile(o);update_sector_coverage(o);''',
'''if(g_.passable.empty())init(o);else reconcile(o);update_sector_coverage(o);for(int x=0;x<n_;++x)if(o.owner[x]==1&&o.type[x]==3)owned_castle_history_[x]=1;''',
'persist owned castle history')

immediate='''if(immediate)for(int x=0;x<n_;++x)if(source(o,x)){int y=tactical_next(o,x,general_);if(y>=0&&o.owner[y]==1)c.push_back({0,x,y,0,double(o.army[x]),Reason::GENERAL_EMERGENCY,false,ActionClass::HARD,general_,-1,PacketRole::GENERAL_DEFENSE});}'''
recapture='''\n  for(int t=0;t<n_;++t)if(owned_castle_history_[t]&&o.type[t]==3&&o.owner[t]==2)for(int d=0;d<4;++d){int x=g_.neighbor(t,d);if(source(o,x)&&safe_attack(o,x,t))c.push_back({1,x,t,0,9500.-o.army[x]*.01,Reason::CASTLE_INVALIDATED,false,ActionClass::HARD,t,-1,PacketRole::COUNTERATTACK});}\n  for(int t=0;t<n_;++t)if(o.type[t]==3&&o.owner[t]==1){for(int de=0;de<4;++de){int e=g_.neighbor(t,de);if(e<0||o.owner[e]!=2||o.army[e]<=1||o.army[e]-1<=o.army[t])continue;for(int dx=0;dx<4;++dx){int x=g_.neighbor(e,dx);if(source(o,x)&&x!=t&&safe_attack(o,x,e))c.push_back({1,x,e,0,9400.-o.army[x]*.01,Reason::CASTLE_INVALIDATED,false,ActionClass::HARD,t,-1,PacketRole::COUNTERATTACK});}for(int dx=0;dx<4;++dx){int x=g_.neighbor(t,dx);if(x<0||x==general_||!source(o,x)||o.owner[x]!=1)continue;int defended=o.army[t]+o.army[x]-1;if(defended>=o.army[e]-1)c.push_back({1,x,t,0,9300.+defended-o.army[e],Reason::CASTLE_INVALIDATED,false,ActionClass::HARD,t,-1,PacketRole::GENERAL_DEFENSE});}}}'''
if 'owned_castle_history_[t]&&o.type[t]==3&&o.owner[t]==2' not in m:
    m=rep(m,immediate,immediate+recapture,'castle recapture and defense')
else: print('castle recapture and defense: already applied')

# Preserve e50123's logistics tie-break in the later picker/search source loop.
oldlog='''int target=sink==x?general_:sink,y=target>=0?tactical_next(o,x,target):-1;'''
newlog='''int target=sink==x?general_:sink,y=target>=0?tactical_next_logistics(o,x,target):-1;'''
# There can be helper-local tactical_next calls; this exact sink expression identifies normal logistics.
m=rep(m,oldlog,newlog,'use e50123 logistics routing')

# Restore the established turn-zero/JIT castle contract: C1 <= 150, C2 <= 250.
c=c.replace('eligible(a,160)','eligible(a,150)')
m=m.replace('forecast(o.turn,160,cost1','forecast(o.turn,150,cost1')
m=m.replace('if(o.turn>175&&castle_build_[0]<0)','if(o.turn>150&&castle_build_[0]<0)')
aggressive='''for(auto [site,f,index]:{std::tuple{castles_.c1,f1,0},std::tuple{castles_.c2,f2,1}})if(site>=0&&castle_state_[index]!=CastleState::BUILT&&(index==0||castle_state_[0]==CastleState::BUILT)){bool c1=index==0,force_c1=c1&&o.turn>=120&&o.turn<=175;if(legal_build(o,site))c.push_back({c1?0:1,site,site,2,c1?7500.:100.,Reason::CASTLE_DEADLINE,false,ActionClass::HARD,site,-1,index?PacketRole::CASTLE_C2:PacketRole::CASTLE_C1});else if(f.must_fund||force_c1)for(int x=0;x<n_;++x)if(source(o,x)){int y=tactical_next(o,x,site);if(y>=0)c.push_back({1,x,y,0,(force_c1?500.:0.)+double(o.army[x])/std::max(1,g_.dist[x][site]),Reason::CASTLE_DEADLINE,false,ActionClass::HARD,site,-1,index?PacketRole::CASTLE_C2:PacketRole::CASTLE_C1});}}'''
original='''for(auto [site,f,index]:{std::tuple{castles_.c1,f1,0},std::tuple{castles_.c2,f2,1}})if(site>=0&&castle_state_[index]!=CastleState::BUILT&&(index==0||castle_state_[0]==CastleState::BUILT)){if(legal_build(o,site))c.push_back({1,site,site,2,100,Reason::CASTLE_DEADLINE,false,ActionClass::HARD,site,-1,index?PacketRole::CASTLE_C2:PacketRole::CASTLE_C1});else if(f.must_fund)for(int x=0;x<n_;++x)if(source(o,x)){int y=tactical_next(o,x,site);if(y>=0)c.push_back({1,x,y,0,double(o.army[x])/std::max(1,g_.dist[x][site]),Reason::CASTLE_DEADLINE,false,ActionClass::HARD,site,-1,index?PacketRole::CASTLE_C2:PacketRole::CASTLE_C1});}}'''
if aggressive in m: m=m.replace(aggressive,original,1); print('restore JIT castle scheduler: applied')
elif original in m: print('restore JIT castle scheduler: already applied')
else: raise SystemExit('restore JIT castle scheduler: shape not recognized')

# Castle commitments/recapture may preempt an active picker. Do not hide them behind picker source reservation.
oldres='''bool reserved=picker_.active&&q.from==picker_.cell&&q.role!=PacketRole::EDGE_PICKER&&q.reason!=Reason::GENERAL_EMERGENCY&&q.reason!=Reason::TERMINAL_CAPTURE;'''
newres='''bool reserved=picker_.active&&q.from==picker_.cell&&q.role!=PacketRole::EDGE_PICKER&&q.reason!=Reason::GENERAL_EMERGENCY&&q.reason!=Reason::TERMINAL_CAPTURE&&q.reason!=Reason::CASTLE_DEADLINE&&q.reason!=Reason::CASTLE_INVALIDATED;'''
m=rep(m,oldres,newres,'castle overrides picker reservation')

# Exact anti-cycle: only repeat of the same directed edge by the same packet in its last four transitions.
m=m.replace('while(p.path.size()>12)p.path.pop_front();','while(p.path.size()>5)p.path.pop_front();')
oldhist='''bool history_cycle(const Candidate&q)const{if(q.from<0||q.to<0)return false;for(auto it=actions_.rbegin();it!=actions_.rend();++it){if(it->event!=event_)break;if(it->from==q.to&&it->to==q.from)return true;}return false;}'''
newhist='''bool history_cycle(const Candidate&q)const{if(q.from<0||q.to<0)return false;if(q.reason==Reason::GENERAL_EMERGENCY||q.reason==Reason::TERMINAL_CAPTURE)return false;const Packet*p=packet_for(q.from);if(!p)return false;int seen_edges=0;for(int i=(int)p->path.size()-1;i>=1&&seen_edges<4;--i,++seen_edges)if(p->path[i-1]==q.from&&p->path[i]==q.to)return true;return false;}'''
if oldhist in m: m=m.replace(oldhist,newhist,1); print('per-packet anti-cycle history: applied')
elif newhist in m: print('per-packet anti-cycle history: already applied')
else: raise SystemExit('per-packet anti-cycle history: shape not recognized')

pat=r'inline bool route_allowed\(const Packet&p,int dest,int new_distance,int old_distance,int event_version,Reason reason\)\{.*?return true;\}'
route='''inline bool route_allowed(const Packet&p,int dest,int new_distance,int old_distance,int event_version,Reason reason){bool emergency=reason==Reason::GENERAL_EMERGENCY||reason==Reason::TERMINAL_CAPTURE;if(emergency)return true;int seen_edges=0;for(int i=(int)p.path.size()-1;i>=1&&seen_edges<4;--i,++seen_edges)if(p.path[i-1]==p.cell&&p.path[i]==dest)return false;bool recent_return=false;int seen_cells=0;for(auto it=p.path.rbegin();it!=p.path.rend()&&seen_cells<5;++it,++seen_cells)if(*it==dest){recent_return=true;break;}bool changed=event_version!=p.event_version&&reason!=Reason::NONE;if(!changed&&new_distance>old_distance&&!recent_return)return false;return true;}'''
c,n=re.subn(pat,route,c,count=1)
if n!=1: raise SystemExit(f'route_allowed replacement count={n}')
print('route_allowed exact edge window: applied')

MAIN.write_text(m); CORE.write_text(c)
print('selective e50123 layer complete')
