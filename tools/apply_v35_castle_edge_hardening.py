from pathlib import Path

MAIN = Path('competition/agents/juraj_v35_cpp/main.cpp')
CORE = Path('competition/agents/juraj_v35_cpp/core.hpp')


def repl(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        print(f'{label}: already applied')
        return text
    if old not in text:
        raise SystemExit(f'{label}: anchor not found')
    print(f'{label}: applied')
    return text.replace(old, new, 1)

m = MAIN.read_text()
c = CORE.read_text()

# Keep the immutable V3.5 architecture, but move the C1 planning/forecast target
# to turn 160 and treat 175 as the hard miss boundary.
c = repl(c, 'if(eligible(a,150))', 'if(eligible(a,160))', 'C1 planning deadline 160')
m = repl(m, 'forecast(o.turn,150,cost1', 'forecast(o.turn,160,cost1', 'C1 forecast deadline 160')
m = repl(m, 'if(o.turn>150&&castle_build_[0]<0)', 'if(o.turn>175&&castle_build_[0]<0)', 'C1 hard miss boundary 175')

# From turn 120 the planned C1 route is no longer optional. Emergency defense
# remains tier 0, but once C1 is legally buildable its build action is promoted
# to tier 0 with utility 7500: below terminal capture / direct reaction / choke
# interception, but above ordinary funding, expansion, search and logistics.
# There is intentionally NO turn gate on a legal C1 build: if C1 is buildable,
# emit BUILD immediately regardless of whether the current turn is below 145.
old_castle = '''for(auto [site,f,index]:{std::tuple{castles_.c1,f1,0},std::tuple{castles_.c2,f2,1}})if(site>=0&&castle_state_[index]!=CastleState::BUILT&&(index==0||castle_state_[0]==CastleState::BUILT)){if(legal_build(o,site))c.push_back({1,site,site,2,100,Reason::CASTLE_DEADLINE,false,ActionClass::HARD,site,-1,index?PacketRole::CASTLE_C2:PacketRole::CASTLE_C1});else if(f.must_fund)for(int x=0;x<n_;++x)if(source(o,x)){int y=tactical_next(o,x,site);if(y>=0)c.push_back({1,x,y,0,double(o.army[x])/std::max(1,g_.dist[x][site]),Reason::CASTLE_DEADLINE,false,ActionClass::HARD,site,-1,index?PacketRole::CASTLE_C2:PacketRole::CASTLE_C1});}}'''
new_castle = '''for(auto [site,f,index]:{std::tuple{castles_.c1,f1,0},std::tuple{castles_.c2,f2,1}})if(site>=0&&castle_state_[index]!=CastleState::BUILT&&(index==0||castle_state_[0]==CastleState::BUILT)){bool c1=index==0,force_c1=c1&&o.turn>=120&&o.turn<=175;if(legal_build(o,site))c.push_back({c1?0:1,site,site,2,c1?7500.:100.,Reason::CASTLE_DEADLINE,false,ActionClass::HARD,site,-1,index?PacketRole::CASTLE_C2:PacketRole::CASTLE_C1});else if(f.must_fund||force_c1)for(int x=0;x<n_;++x)if(source(o,x)){int y=tactical_next(o,x,site);if(y>=0)c.push_back({1,x,y,0,(force_c1?500.:0.)+double(o.army[x])/std::max(1,g_.dist[x][site]),Reason::CASTLE_DEADLINE,false,ActionClass::HARD,site,-1,index?PacketRole::CASTLE_C2:PacketRole::CASTLE_C1});}}'''
m = repl(m, old_castle, new_castle, 'C1 forced acquisition/funding and strict build priority')

# Add explicit two-rally pre-contact edge collection. Rally points are selected
# deterministically from currently owned interior cells, with the second rally
# biased to be spatially separated from the first. Boundary stacks move FULL-1
# only through owned safe cells toward the nearer rally. This creates one or
# two chunks instead of leaving 2/3/4-army crumbs on top/right/bottom/left edges.
anchor = '''const Front*front=fronts_.primary();int sink=belief_.confirmed()?belief_.confirmed_cell():(front?front->anchor:belief_.top());for(int x=0;x<n_;++x)if(source(o,x)){int surplus=o.army[x]-reserve(o,x);if(surplus<=0)continue;int edge=std::min({x/w_,h_-1-x/w_,x%w_,w_-1-x%w_});bool rear=edge<=1||g_.degree(x)<=1;int target=sink==x?general_:sink,y=target>=0?tactical_next(o,x,target):-1;if(y<0)continue;if(confirmed_war&&b.war>0)c.push_back({2,x,y,0,double(surplus)/std::max(1,g_.dist[x][target]),Reason::WAR_MOBILIZATION,false,ActionClass::LOGISTICS,target,front?front->id:-1,PacketRole::FRONT});else if(rear&&b.free+b.search>0)c.push_back({2,x,y,0,double(surplus),Reason::REAR_EVACUATION,false,ActionClass::LOGISTICS,target,-1,PacketRole::FREE_SURPLUS_RELOCATION});else if(!enemy_seen&&b.search>0)c.push_back({3,x,y,0,double(surplus)/std::max(1,g_.dist[x][target]),Reason::SEARCH_PROGRESS,false,ActionClass::SEARCH,target,-1,PacketRole::SEARCH});}'''
replacement = '''const Front*front=fronts_.primary();int sink=belief_.confirmed()?belief_.confirmed_cell():(front?front->anchor:belief_.top());
  auto edge_depth=[&](int x){return std::min({x/w_,h_-1-x/w_,x%w_,w_-1-x%w_});};std::array<int,2>rally{{-1,-1}};if(!enemy_seen&&!confirmed_war){for(int k=0;k<2;++k){double best=-1e100;for(int x=0;x<n_;++x)if(o.owner[x]==1&&g_.passable[x]&&x!=general_&&edge_depth(x)>=2){if(k==1&&rally[0]>=0&&g_.dist[x][rally[0]]<4)continue;double s=edge_depth(x)*45.+g_.degree(x)*12.+std::min(o.army[x],20)*3.;if(k==1&&rally[0]>=0)s+=std::min(g_.dist[x][rally[0]],10)*8.;if(s>best){best=s;rally[k]=x;}}}if(rally[0]<0)rally[0]=general_;if(rally[1]<0)rally[1]=rally[0];for(int x=0;x<n_;++x)if(source(o,x)&&x!=general_&&x!=castles_.c1&&x!=castles_.c2&&edge_depth(x)<=1){int surplus=o.army[x]-reserve(o,x);if(surplus<=0)continue;int target=rally[0];if(rally[1]>=0&&g_.dist[x][rally[1]]<g_.dist[x][rally[0]])target=rally[1];int y=target>=0?tactical_next(o,x,target):-1;if(y<0||o.owner[y]!=1||g_.dist[y][target]>=g_.dist[x][target]||edge_depth(y)<edge_depth(x))continue;c.push_back({2,x,y,0,700.+surplus*25.+(edge_depth(y)-edge_depth(x))*120.,Reason::REAR_EVACUATION,false,ActionClass::LOGISTICS,target,-1,PacketRole::FREE_SURPLUS_RELOCATION});}}
  for(int x=0;x<n_;++x)if(source(o,x)){int surplus=o.army[x]-reserve(o,x);if(surplus<=0)continue;int edge=edge_depth(x);bool rear=edge<=1||g_.degree(x)<=1;int target=sink==x?general_:sink,y=target>=0?tactical_next(o,x,target):-1;if(y<0)continue;if(confirmed_war&&b.war>0)c.push_back({2,x,y,0,double(surplus)/std::max(1,g_.dist[x][target]),Reason::WAR_MOBILIZATION,false,ActionClass::LOGISTICS,target,front?front->id:-1,PacketRole::FRONT});else if(rear&&b.free+b.search>0)c.push_back({2,x,y,0,double(surplus),Reason::REAR_EVACUATION,false,ActionClass::LOGISTICS,target,-1,PacketRole::FREE_SURPLUS_RELOCATION});else if(!enemy_seen&&b.search>0)c.push_back({3,x,y,0,double(surplus)/std::max(1,g_.dist[x][target]),Reason::SEARCH_PROGRESS,false,ActionClass::SEARCH,target,-1,PacketRole::SEARCH});}'''
m = repl(m, anchor, replacement, 'two-rally edge consolidation')

# When edge collection candidates exist before contact, give logistics enough
# scheduler share to actually execute them; the expansion starvation guard and
# all hard tactical/castle actions remain authoritative.
old_share = '''bool expansion_available=std::any_of(filtered.begin(),filtered.end(),[](auto&q){return q.action_class==ActionClass::EXPANSION;});std::array<double,5>share{{0,confirmed_war?.30:.12,production_==ProductionState::SEVERE_DEFICIT?.62:production_==ProductionState::SOFT_DEFICIT?.45:.35,!enemy_seen?.20:.08,confirmed_war?.22:.15}};'''
new_share = '''bool expansion_available=std::any_of(filtered.begin(),filtered.end(),[](auto&q){return q.action_class==ActionClass::EXPANSION;});bool edge_pull_available=!enemy_seen&&std::any_of(filtered.begin(),filtered.end(),[](auto&q){return q.reason==Reason::REAR_EVACUATION&&q.action_class==ActionClass::LOGISTICS;});double logistics_share=edge_pull_available?.32:(confirmed_war?.22:.15);std::array<double,5>share{{0,confirmed_war?.30:.12,production_==ProductionState::SEVERE_DEFICIT?.62:production_==ProductionState::SOFT_DEFICIT?.45:.35,!enemy_seen?.20:.08,logistics_share}};'''
m = repl(m, old_share, new_share, 'pre-contact logistics scheduler share')

MAIN.write_text(m)
CORE.write_text(c)
print('V3.5 champion hardening patch complete')
