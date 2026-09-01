from pathlib import Path

p = Path('competition/agents/juraj_v35_cpp/main.cpp')
s = p.read_text()
old = '''  for(int x=0;x<n_;++x)if(source(o,x)){if(picker_.active&&x==picker_.cell)continue;int surplus=o.army[x]-reserve(o,x);if(surplus<=0)continue;int edge=std::min({x/w_,h_-1-x/w_,x%w_,w_-1-x%w_});bool rear=edge<=1||g_.degree(x)<=1;int target=sink==x?general_:sink,y=target>=0?tactical_next_logistics(o,x,target):-1;if(y<0)continue;if(confirmed_war&&b.war>0)c.push_back({2,x,y,0,double(surplus)/std::max(1,g_.dist[x][target]),Reason::WAR_MOBILIZATION,false,ActionClass::LOGISTICS,target,front?front->id:-1,PacketRole::FRONT});else if(rear&&b.free+b.search>0)c.push_back({2,x,y,0,double(surplus),Reason::REAR_EVACUATION,false,ActionClass::LOGISTICS,target,-1,PacketRole::FREE_SURPLUS_RELOCATION});else if(!enemy_seen&&b.search>0)c.push_back({3,x,y,0,double(surplus)/std::max(1,g_.dist[x][target]),Reason::SEARCH_PROGRESS,false,ActionClass::SEARCH,target,-1,PacketRole::SEARCH});}
'''
new = '''  int rear_belief_target=(!belief_.confirmed()&&o.turn>=900&&!immediate&&production_!=ProductionState::SEVERE_DEFICIT&&o.my_land>=o.opp_land&&o.my_army*20>=std::max(1,o.opp_army)*23)?belief_.top():-1;
  for(int x=0;x<n_;++x)if(source(o,x)){if(picker_.active&&x==picker_.cell)continue;int surplus=o.army[x]-reserve(o,x);if(surplus<=0)continue;int edge=std::min({x/w_,h_-1-x/w_,x%w_,w_-1-x%w_});bool rear=edge<=1||g_.degree(x)<=1;bool rear_hunt=rear_belief_target>=0&&rear&&x!=general_&&o.type[x]!=3&&x!=castles_.c1&&x!=castles_.c2&&reserve(o,x)==1&&o.army[x]>=4&&o.army[x]<=24;int target=rear_hunt?rear_belief_target:(sink==x?general_:sink),y=target>=0?tactical_next_logistics(o,x,target):-1;if(y<0)continue;if(rear_hunt)c.push_back({3,x,y,0,.25+double(surplus)/std::max(1,g_.dist[x][target]),Reason::SEARCH_PROGRESS,false,ActionClass::LOGISTICS,target,-1,PacketRole::FREE_SURPLUS_RELOCATION});else if(confirmed_war&&b.war>0)c.push_back({2,x,y,0,double(surplus)/std::max(1,g_.dist[x][target]),Reason::WAR_MOBILIZATION,false,ActionClass::LOGISTICS,target,front?front->id:-1,PacketRole::FRONT});else if(rear&&b.free+b.search>0)c.push_back({2,x,y,0,double(surplus),Reason::REAR_EVACUATION,false,ActionClass::LOGISTICS,target,-1,PacketRole::FREE_SURPLUS_RELOCATION});else if(!enemy_seen&&b.search>0)c.push_back({3,x,y,0,double(surplus)/std::max(1,g_.dist[x][target]),Reason::SEARCH_PROGRESS,false,ActionClass::SEARCH,target,-1,PacketRole::SEARCH});}
'''
if s.count(old) != 1:
    raise SystemExit(f'source-loop anchor count={s.count(old)}')
s = s.replace(old, new, 1)
p.write_text(s)
print('patched rear-only low-mass belief logistics after turn 900; frontline war routing unchanged')
