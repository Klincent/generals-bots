from pathlib import Path

MAIN = Path('competition/agents/juraj_v35_cpp/main.cpp')
TEST = Path('competition/agents/juraj_v35_cpp/test_agent.cpp')

s = MAIN.read_text()

reps = [
    (
        'std::map<long,Packet>packets_;std::vector<long>packet_at_;std::vector<int>last_owner_,last_army_,land_hist_,opp_land_hist_,opp_army_hist_;std::deque<ExecutedMove>actions_;',
        'std::map<long,Packet>packets_;std::vector<long>packet_at_;std::vector<char>owned_castle_history_;std::vector<int>last_owner_,last_army_,land_hist_,opp_land_hist_,opp_army_hist_;std::deque<ExecutedMove>actions_;',
    ),
    (
        'std::array<int,2> live_cost_{{35,35}};std::array<int,2> castle_start_{{-1,-1}},castle_build_{{-1,-1}},castle_latest_{{-1,-1}},castle_actions_{{0,0}};std::string castle_miss_="none";',
        'int recapture_castle_=-1,recapture_since_=-1;long lost_castles_detected_=0,castle_recapture_feasible_=0,castle_recapture_actions_=0,castle_recaptures_completed_=0;\n std::array<int,2> live_cost_{{35,35}};std::array<int,2> castle_start_{{-1,-1}},castle_build_{{-1,-1}},castle_latest_{{-1,-1}},castle_actions_{{0,0}};std::string castle_miss_="none";',
    ),
    (
        'last_owner_=o.owner;last_army_=o.army;packet_at_.assign(n_,0);std::fprintf(stderr,',
        'last_owner_=o.owner;last_army_=o.army;packet_at_.assign(n_,0);owned_castle_history_.assign(n_,0);for(int x=0;x<n_;++x)if(o.owner[x]==1&&o.type[x]==3)owned_castle_history_[x]=1;std::fprintf(stderr,',
    ),
    (
        'Action act(const Observation&o){auto begin=std::chrono::steady_clock::now();if(g_.passable.empty())init(o);else reconcile(o);',
        'Action act(const Observation&o){auto begin=std::chrono::steady_clock::now();if(g_.passable.empty())init(o);else reconcile(o);update_castle_recapture(o);',
    ),
    (
        'if(immediate)for(int x=0;x<n_;++x)if(source(o,x)){int y=tactical_next(o,x,general_);if(y>=0&&o.owner[y]==1)c.push_back({0,x,y,0,double(o.army[x]),Reason::GENERAL_EMERGENCY,false,ActionClass::HARD,general_,-1,PacketRole::GENERAL_DEFENSE});}\n  for(auto [site,f,index]:',
        'if(immediate)for(int x=0;x<n_;++x)if(source(o,x)){int y=tactical_next(o,x,general_);if(y>=0&&o.owner[y]==1)c.push_back({0,x,y,0,double(o.army[x]),Reason::GENERAL_EMERGENCY,false,ActionClass::HARD,general_,-1,PacketRole::GENERAL_DEFENSE});}\n  add_castle_recapture_candidates(o,c,immediate);\n  for(auto [site,f,index]:',
    ),
    (
        'if(a.kind==0){if(q.reason==Reason::GENERAL_EMERGENCY&&q.role==PacketRole::REACTION)++winning_intercepts_;',
        'if(a.kind==0){if(q.reason==Reason::CASTLE_INVALIDATED&&q.role==PacketRole::COUNTERATTACK)++castle_recapture_actions_;if(q.reason==Reason::GENERAL_EMERGENCY&&q.role==PacketRole::REACTION)++winning_intercepts_;',
    ),
    (
        'std::fprintf(stderr,"[v35_castle_live] prevented_invalid_builds=%ld\\n",live_cost_blocked_);',
        'std::fprintf(stderr,"[v35_castle_live] prevented_invalid_builds=%ld\\n",live_cost_blocked_);std::fprintf(stderr,"[v35_castle_recapture] lost_detected=%ld current_target=%d since=%d feasible_turns=%ld actions=%ld completed=%ld\\n",lost_castles_detected_,recapture_castle_,recapture_since_,castle_recapture_feasible_,castle_recapture_actions_,castle_recaptures_completed_);',
    ),
    (
        'long threat_plans_released()const{return threat_plans_released_;}~Agent(){report();}',
        'long threat_plans_released()const{return threat_plans_released_;}int recapture_castle()const{return recapture_castle_;}long lost_castles_detected()const{return lost_castles_detected_;}long castle_recapture_actions()const{return castle_recapture_actions_;}long castle_recaptures_completed()const{return castle_recaptures_completed_;}~Agent(){report();}',
    ),
]

needle = ' int tactical_next(const Observation&o,int x,int target)const{int best=-1,bd=INF;for(int d=0;d<4;++d){int y=g_.neighbor(x,d);if(safe_step(o,x,y)&&g_.dist[y][target]<bd)best=y,bd=g_.dist[y][target];}return best;}\n'
helper = r'''
 void update_castle_recapture(const Observation&o){for(int x=0;x<n_;++x)if(o.owner[x]==1&&o.type[x]==3)owned_castle_history_[x]=1;for(int x=0;x<n_;++x)if(owned_castle_history_[x]&&o.type[x]==3&&o.owner[x]==2&&last_owner_[x]==1)++lost_castles_detected_;int old=recapture_castle_;if(old>=0&&old<n_&&o.type[old]==3&&o.owner[old]==1)++castle_recaptures_completed_;int best=-1,bd=INF;if(old>=0&&old<n_&&owned_castle_history_[old]&&(o.owner[old]==2||o.owner[old]<0)){best=old;bd=general_>=0?g_.dist[general_][old]:INF;}for(int x=0;x<n_;++x)if(owned_castle_history_[x]&&o.type[x]==3&&o.owner[x]==2){int d=general_>=0?g_.dist[general_][x]:INF;if(best<0||std::tuple(d,x)<std::tuple(bd,best))best=x,bd=d;}if(best!=old){recapture_castle_=best;recapture_since_=best>=0?o.turn:-1;++event_;}}
 void add_castle_recapture_candidates(const Observation&o,std::vector<Candidate>&c,bool immediate){int t=recapture_castle_;if(immediate||t<0||t>=n_||o.owner[t]!=2||o.type[t]!=3)return;std::vector<Candidate>take;for(int d=0;d<4;++d){int x=g_.neighbor(t,d);if(source(o,x)&&safe_attack(o,x,t))take.push_back({1,x,t,0,9800.-o.army[x]*.01,Reason::CASTLE_INVALIDATED,false,ActionClass::HARD,t,-1,PacketRole::COUNTERATTACK});}if(!take.empty()){c.push_back(schedule(take));return;}int stage=-1,stage_army=-1;for(int d=0;d<4;++d){int x=g_.neighbor(t,d);if(x>=0&&o.owner[x]==1&&g_.passable[x]&&o.army[x]>stage_army)stage=x,stage_army=o.army[x];}if(stage<0)return;int cover=0;for(int d=0;d<4;++d){int z=g_.neighbor(t,d);if(z>=0&&z!=stage&&o.owner[z]==2)cover=std::max(cover,o.army[z]);}int needed=o.army[t]+cover+2,missing=std::max(0,needed-o.army[stage]);if(missing<=0)return;std::vector<std::tuple<int,int,int>>feed;for(int x=0;x<n_;++x)if(x!=stage&&x!=general_&&source(o,x)){int d=g_.dist[x][stage];if(d<=0||d>8||d>=INF)continue;int deliver=std::max(0,o.army[x]-d);if(deliver>0)feed.push_back({d,-deliver,x});}std::sort(feed.begin(),feed.end());int total=0;std::vector<std::tuple<int,int,int>>chosen;for(auto z:feed){chosen.push_back(z);total+=-std::get<1>(z);if(total>=missing)break;}if(total<missing)return;++castle_recapture_feasible_;for(auto [d,neg,x]:chosen){int deliver=-neg,y=tactical_next(o,x,stage);if(y<0&&d==1&&o.owner[stage]==1&&o.army[stage]+o.army[x]-1>=o.army[t]-1)y=stage;if(y>=0&&o.owner[y]==1)c.push_back({1,x,y,0,9000.-d*10+deliver,Reason::CASTLE_INVALIDATED,false,ActionClass::HARD,t,-1,PacketRole::COUNTERATTACK});}}
'''
if s.count(needle) != 1:
    raise SystemExit(f'tactical_next anchor count={s.count(needle)}')
s = s.replace(needle, needle + helper, 1)
for old, new in reps:
    count = s.count(old)
    if count != 1:
        raise SystemExit(f'patch anchor expected 1 got {count}: {old[:100]}')
    s = s.replace(old, new, 1)
if any(token in s for token in ('staging_point(', 'rear_pressure(', 'castle_opportunity_', 'castle_target_')):
    raise SystemExit('forbidden prior experimental mechanism present')
MAIN.write_text(s)

t = TEST.read_text()
anchor = ' std::cout<<"v35 agent recovery scenarios passed\\n";\n'
tests = r''' // A castle that was ours and is captured is immediately retaken by a safe adjacent winning stack.
 {Agent a(0,21,21);auto o=board();o.type[100]=3;o.owner[100]=1;o.army[100]=4;o.owner[99]=1;o.army[99]=14;a.decide(o);++o.turn;o.owner[100]=2;o.army[100]=5;auto q=a.decide(o);assert(a.lost_castles_detected()==1&&a.recapture_castle()==100);assert(q.kind==0&&src(q)==99&&dst(q)==100);apply(o,q);a.decide(o);assert(a.castle_recaptures_completed()==1&&a.recapture_castle()<0);}
 // If the adjacent foothold is too weak, a nearby feeder is pulled into it instead of suiciding into the castle.
 {Agent a(0,21,21);auto o=board();o.type[100]=3;o.owner[100]=1;o.army[100]=4;o.owner[99]=1;o.army[99]=3;o.owner[98]=1;o.army[98]=15;a.decide(o);++o.turn;o.owner[100]=2;o.army[100]=8;auto q=a.decide(o);assert(a.recapture_castle()==100);assert(q.kind==0&&src(q)==98&&dst(q)==99);assert(a.castle_recapture_actions()==1);}
 // A general emergency remains tier-0 and preempts castle recapture.
 {Agent a(0,21,21);auto o=board();o.type[100]=3;o.owner[100]=1;o.army[100]=4;o.owner[99]=1;o.army[99]=14;a.decide(o);++o.turn;o.owner[100]=2;o.army[100]=5;o.army[220]=5;o.owner[219]=2;o.army[219]=10;o.owner[218]=1;o.army[218]=12;auto q=a.decide(o);assert(a.recapture_castle()==100);assert(q.kind==0&&src(q)==218&&dst(q)==219);}
 // A generic enemy castle that was never ours does not create a recapture objective.
 {Agent a(0,21,21);auto o=board();o.type[100]=3;o.owner[100]=2;o.army[100]=3;o.owner[99]=1;o.army[99]=10;a.decide(o);assert(a.recapture_castle()<0&&a.lost_castles_detected()==0);}
'''
if t.count(anchor) != 1:
    raise SystemExit('test anchor mismatch')
TEST.write_text(t.replace(anchor, tests + anchor, 1))
print('castle recapture patch + targeted tests materialized')
