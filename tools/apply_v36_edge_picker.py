from pathlib import Path

MAIN = Path('competition/agents/juraj_v35_cpp/main.cpp')
CORE = Path('competition/agents/juraj_v35_cpp/core.hpp')
TEST_SH = Path('competition/agents/juraj_v35_cpp/test.sh')
TEST_PICKER = Path('competition/agents/juraj_v35_cpp/test_picker.cpp')


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
t = TEST_SH.read_text()

c = repl(c,
    'enum class PacketRole {GENERAL_DEFENSE,REACTION,CASTLE_C1,CASTLE_C2,EXPANSION,SEARCH,FRONT,ATTACK,COUNTERATTACK,FREE_SURPLUS_RELOCATION};',
    'enum class PacketRole {GENERAL_DEFENSE,REACTION,CASTLE_C1,CASTLE_C2,EXPANSION,SEARCH,FRONT,ATTACK,COUNTERATTACK,FREE_SURPLUS_RELOCATION,EDGE_PICKER};',
    'edge picker packet role')
c = repl(c,
    'enum class Reason {NONE,TERMINAL_CAPTURE,GENERAL_EMERGENCY,CASTLE_DEADLINE,PRODUCTION_TICK,WAR_MOBILIZATION,REAR_EVACUATION,SEARCH_PROGRESS,TOPOLOGY_CHANGED,OPPONENT_EXPLOIT,FRONT_CHANGED,GENERAL_DISCOVERED,PRODUCTION_EMERGENCY,CASTLE_INVALIDATED,DEATHTOUCH};',
    'enum class Reason {NONE,TERMINAL_CAPTURE,GENERAL_EMERGENCY,CASTLE_DEADLINE,PRODUCTION_TICK,WAR_MOBILIZATION,REAR_EVACUATION,EDGE_PICKER,SEARCH_PROGRESS,TOPOLOGY_CHANGED,OPPONENT_EXPLOIT,FRONT_CHANGED,GENERAL_DISCOVERED,PRODUCTION_EMERGENCY,CASTLE_INVALIDATED,DEATHTOUCH};',
    'edge picker reason')

m = repl(m,
    'struct PassStats {long no_movable=0,no_legal=0,no_safe=0,cycle_blocked=0,no_strategic_candidate=0,other=0,replaced=0;};',
    'struct PassStats {long no_movable=0,no_legal=0,no_safe=0,cycle_blocked=0,no_strategic_candidate=0,other=0,replaced=0;};\nstruct EdgePickerState {bool active=false;int wall=-1,cell=-1,dir=0,phase=0,start_turn=-1,start_army=0;};',
    'edge picker state type')

m = repl(m,
    ' std::array<int,2> live_cost_{{35,35}};std::array<int,2> castle_start_{{-1,-1}},castle_build_{{-1,-1}},castle_latest_{{-1,-1}},castle_actions_{{0,0}};std::string castle_miss_="none";',
    ' std::array<int,2> live_cost_{{35,35}};std::array<int,2> castle_start_{{-1,-1}},castle_build_{{-1,-1}},castle_latest_{{-1,-1}},castle_actions_{{0,0}};std::string castle_miss_="none";\n EdgePickerState picker_;int edge_picker_threshold_=4,picker_wait_=0;long picker_starts_=0,picker_completions_=0,picker_moves_=0,picker_aborts_=0,picker_units_delivered_=0;',
    'edge picker fields')

old_init = ' void init(const Observation&o){g_={h_,w_,std::vector<char>(n_),{}, {}};for(int x=0;x<n_;++x){g_.passable[x]=o.type[x]!=2&&o.type[x]!=5;if(o.type[x]==4&&o.owner[x]==1)general_=x;}g_.build();castles_=plan_castles(g_,general_);belief_.initialise(g_,general_);last_owner_=o.owner;last_army_=o.army;packet_at_.assign(n_,0);std::fprintf(stderr,"[v35_plan] c1=%d cost1=%d c2=%d cost2=%d total=%d\\n",castles_.c1,castles_.cost1,castles_.c2,castles_.cost2,castles_.total);}'
new_init = ' void init(const Observation&o){g_={h_,w_,std::vector<char>(n_),{}, {}};for(int x=0;x<n_;++x){g_.passable[x]=o.type[x]!=2&&o.type[x]!=5;if(o.type[x]==4&&o.owner[x]==1)general_=x;}g_.build();castles_=plan_castles(g_,general_);belief_.initialise(g_,general_);last_owner_=o.owner;last_army_=o.army;packet_at_.assign(n_,0);if(const char*e=std::getenv("V35_EDGE_PICKER_THRESHOLD")){int v=std::atoi(e);if(v>=0&&v<=100)edge_picker_threshold_=v;}std::fprintf(stderr,"[v35_plan] c1=%d cost1=%d c2=%d cost2=%d total=%d\\n",castles_.c1,castles_.cost1,castles_.c2,castles_.cost2,castles_.total);}'
m = repl(m, old_init, new_init, 'runtime picker threshold')

old_tactical = ' int tactical_next(const Observation&o,int x,int target)const{int best=-1,bd=INF;for(int d=0;d<4;++d){int y=g_.neighbor(x,d);if(safe_step(o,x,y)&&g_.dist[y][target]<bd)best=y,bd=g_.dist[y][target];}return best;}'
new_tactical = old_tactical + '''
 bool picker_transit_safe(const Observation&o,int x)const{if(x<0||x>=n_||o.owner[x]!=1||!g_.passable[x])return false;if(x==general_)return true;if(o.type[x]==3||x==castles_.c1||x==castles_.c2)return false;for(int z=0;z<n_;++z)if(o.owner[z]==2&&g_.dist[x][z]<=3)return false;return true;}
 bool wall_contains(int x,int wall)const{int r=x/w_,col=x%w_;return wall==0?r==0:wall==1?col==w_-1:wall==2?r==h_-1:col==0;}
 int wall_coord(int x,int wall)const{return (wall==0||wall==2)?x%w_:x/w_;}
 int wall_cell_at(int wall,int coord)const{if(wall==0)return coord>=0&&coord<w_?coord:-1;if(wall==2)return coord>=0&&coord<w_?(h_-1)*w_+coord:-1;if(wall==1)return coord>=0&&coord<h_?coord*w_+w_-1:-1;return coord>=0&&coord<h_?coord*w_:-1;}
 bool wall_irrelevant(int wall,int sink)const{if(general_<0)return false;if(sink<0)return true;int gr=general_/w_,gc=general_%w_,sr=sink/w_,sc=sink%w_;if(wall==0)return sr>=gr-1;if(wall==2)return sr<=gr+1;if(wall==3)return sc>=gc-1;return sc<=gc+1;}
 bool cell_on_irrelevant_wall(int x,int sink)const{for(int wall=0;wall<4;++wall)if(wall_contains(x,wall)&&wall_irrelevant(wall,sink))return true;return false;}
 int owned_next_to_general(const Observation&o,int from)const{if(from<0||general_<0||from==general_)return -1;std::vector<int>d(n_,-1);std::queue<int>q;d[general_]=0;q.push(general_);while(!q.empty()){int x=q.front();q.pop();for(int k=0;k<4;++k){int y=g_.neighbor(x,k);if(y<0||d[y]>=0||o.owner[y]!=1)continue;if(y!=from&&y!=general_&&!picker_transit_safe(o,y))continue;d[y]=d[x]+1;q.push(y);}}int best=-1,bd=INF;for(int k=0;k<4;++k){int y=g_.neighbor(from,k);if(y>=0&&d[y]>=0&&d[y]<bd){best=y;bd=d[y];}}return best;}'''
m = repl(m, old_tactical, new_tactical, 'edge picker helpers')

old_edge = '''  auto edge_depth=[&](int x){return std::min({x/w_,h_-1-x/w_,x%w_,w_-1-x%w_});};std::array<int,2>rally{{-1,-1}};if(!enemy_seen&&!confirmed_war){for(int k=0;k<2;++k){double best=-1e100;for(int x=0;x<n_;++x)if(o.owner[x]==1&&g_.passable[x]&&x!=general_&&edge_depth(x)>=2){if(k==1&&rally[0]>=0&&g_.dist[x][rally[0]]<4)continue;double s=edge_depth(x)*45.+g_.degree(x)*12.+std::min(o.army[x],20)*3.;if(k==1&&rally[0]>=0)s+=std::min(g_.dist[x][rally[0]],10)*8.;if(s>best){best=s;rally[k]=x;}}}if(rally[0]<0)rally[0]=general_;if(rally[1]<0)rally[1]=rally[0];for(int x=0;x<n_;++x)if(source(o,x)&&x!=general_&&x!=castles_.c1&&x!=castles_.c2&&edge_depth(x)<=1){int surplus=o.army[x]-reserve(o,x);if(surplus<=0)continue;int target=rally[0];if(rally[1]>=0&&g_.dist[x][rally[1]]<g_.dist[x][rally[0]])target=rally[1];int y=target>=0?tactical_next(o,x,target):-1;if(y<0||o.owner[y]!=1||g_.dist[y][target]>=g_.dist[x][target]||edge_depth(y)<edge_depth(x))continue;c.push_back({2,x,y,0,700.+surplus*25.+(edge_depth(y)-edge_depth(x))*120.,Reason::REAR_EVACUATION,false,ActionClass::LOGISTICS,target,-1,PacketRole::FREE_SURPLUS_RELOCATION});}}
  for(int x=0;x<n_;++x)if(source(o,x)){int surplus=o.army[x]-reserve(o,x);if(surplus<=0)continue;int edge=edge_depth(x);bool rear=edge<=1||g_.degree(x)<=1;int target=sink==x?general_:sink,y=target>=0?tactical_next(o,x,target):-1;if(y<0)continue;if(confirmed_war&&b.war>0)c.push_back({2,x,y,0,double(surplus)/std::max(1,g_.dist[x][target]),Reason::WAR_MOBILIZATION,false,ActionClass::LOGISTICS,target,front?front->id:-1,PacketRole::FRONT});else if(rear&&b.free+b.search>0)c.push_back({2,x,y,0,double(surplus),Reason::REAR_EVACUATION,false,ActionClass::LOGISTICS,target,-1,PacketRole::FREE_SURPLUS_RELOCATION});else if(!enemy_seen&&b.search>0)c.push_back({3,x,y,0,double(surplus)/std::max(1,g_.dist[x][target]),Reason::SEARCH_PROGRESS,false,ActionClass::SEARCH,target,-1,PacketRole::SEARCH});}'''
new_edge = '''  auto edge_depth=[&](int x){return std::min({x/w_,h_-1-x/w_,x%w_,w_-1-x%w_});};int picker_sink=belief_.confirmed()?belief_.confirmed_cell():(front?front->anchor:-1);
  if(picker_.active&&(picker_.cell<0||o.owner[picker_.cell]!=1||o.army[picker_.cell]<=1)){picker_.active=false;picker_wait_=0;++picker_aborts_;}
  if(!picker_.active&&!immediate&&general_>=0){int best_wall=-1,best_mass=edge_picker_threshold_;for(int wall=0;wall<4;++wall)if(wall_irrelevant(wall,picker_sink)){int mass=0;for(int x=0;x<n_;++x)if(wall_contains(x,wall)&&x!=general_&&picker_transit_safe(o,x))mass+=std::max(0,o.army[x]-1);if(mass>edge_picker_threshold_&&(best_wall<0||mass>best_mass)){best_wall=wall;best_mass=mass;}}if(best_wall>=0){int proj=(best_wall==0||best_wall==2)?general_%w_:general_/w_,start=-1,far=-1;for(int x=0;x<n_;++x)if(wall_contains(x,best_wall)&&x!=general_&&picker_transit_safe(o,x)&&o.army[x]>1){int d=std::abs(wall_coord(x,best_wall)-proj);if(d>far){far=d;start=x;}}if(start>=0){int c0=wall_coord(start,best_wall);picker_={true,best_wall,start,c0<proj?1:c0>proj?-1:0,0,o.turn,o.army[start]};picker_wait_=2;++picker_starts_;}}}
  if(picker_.active){int x=picker_.cell,y=-1,proj=(picker_.wall==0||picker_.wall==2)?general_%w_:general_/w_;if(picker_.phase==0){int cc=wall_coord(x,picker_.wall);if(cc!=proj&&picker_.dir!=0){int z=wall_cell_at(picker_.wall,cc+picker_.dir);if(z>=0&&picker_transit_safe(o,z))y=z;else picker_.phase=1;}else picker_.phase=1;}if(picker_.phase==1)y=owned_next_to_general(o,x);if(y>=0&&source(o,x)&&o.owner[y]==1)c.push_back({2,x,y,0,3000.+o.army[x]*5.,Reason::EDGE_PICKER,false,ActionClass::LOGISTICS,general_,-1,PacketRole::EDGE_PICKER});else if(picker_.phase==1&&x!=general_){picker_.active=false;picker_wait_=0;++picker_aborts_;}}
  for(int x=0;x<n_;++x)if(source(o,x)){if(picker_.active&&x==picker_.cell)continue;int surplus=o.army[x]-reserve(o,x);if(surplus<=0)continue;int edge=edge_depth(x);if(edge==0&&cell_on_irrelevant_wall(x,picker_sink))continue;bool rear=g_.degree(x)<=1;int target=sink==x?general_:sink,y=target>=0?tactical_next(o,x,target):-1;if(y<0)continue;if(confirmed_war&&b.war>0)c.push_back({2,x,y,0,double(surplus)/std::max(1,g_.dist[x][target]),Reason::WAR_MOBILIZATION,false,ActionClass::LOGISTICS,target,front?front->id:-1,PacketRole::FRONT});else if(rear&&b.free+b.search>0)c.push_back({2,x,y,0,double(surplus),Reason::REAR_EVACUATION,false,ActionClass::LOGISTICS,target,-1,PacketRole::FREE_SURPLUS_RELOCATION});else if(!enemy_seen&&b.search>0)c.push_back({3,x,y,0,double(surplus)/std::max(1,g_.dist[x][target]),Reason::SEARCH_PROGRESS,false,ActionClass::SEARCH,target,-1,PacketRole::SEARCH});}'''
m = repl(m, old_edge, new_edge, 'replace two-rally edge shift with persistent wall picker')

old_sched = '''  std::vector<Candidate>filtered;for(auto&q:c){bool reject=history_cycle(q)||!packet_route_ok(q);if(reject&&q.tier>1){++candidate_reject_;continue;}filtered.push_back(q);}bool expansion_available=std::any_of(filtered.begin(),filtered.end(),[](auto&q){return q.action_class==ActionClass::EXPANSION;});bool edge_pull_available=!enemy_seen&&std::any_of(filtered.begin(),filtered.end(),[](auto&q){return q.reason==Reason::REAR_EVACUATION&&q.action_class==ActionClass::LOGISTICS;});double logistics_share=edge_pull_available?.32:(confirmed_war?.22:.15);std::array<double,5>share{{0,confirmed_war?.30:.12,production_==ProductionState::SEVERE_DEFICIT?.62:production_==ProductionState::SOFT_DEFICIT?.45:.35,!enemy_seen?.20:.08,logistics_share}};double total=share[1]+share[2]+share[3]+share[4];for(int i=1;i<5;++i)share[i]/=total;Candidate q=strategic_pick(filtered,share,immediate);if(expansion_available&&q.action_class!=ActionClass::EXPANSION&&!immediate)++expansion_wait_;else if(q.action_class==ActionClass::EXPANSION)expansion_wait_=0;'''
new_sched = '''  std::vector<Candidate>filtered;for(auto&q:c){bool reject=history_cycle(q)||!packet_route_ok(q);if(reject&&q.tier>1&&q.role!=PacketRole::EDGE_PICKER){++candidate_reject_;continue;}filtered.push_back(q);}bool expansion_available=std::any_of(filtered.begin(),filtered.end(),[](auto&q){return q.action_class==ActionClass::EXPANSION;});bool picker_available=std::any_of(filtered.begin(),filtered.end(),[](auto&q){return q.role==PacketRole::EDGE_PICKER;});bool hard_available=std::any_of(filtered.begin(),filtered.end(),[](auto&q){return q.tier<=1;});double logistics_share=picker_.active?.24:(confirmed_war?.22:.15);std::array<double,5>share{{0,confirmed_war?.30:.12,production_==ProductionState::SEVERE_DEFICIT?.62:production_==ProductionState::SOFT_DEFICIT?.45:.35,!enemy_seen?.20:.08,logistics_share}};double total=share[1]+share[2]+share[3]+share[4];for(int i=1;i<5;++i)share[i]/=total;Candidate q;if(!hard_available&&picker_available&&picker_wait_>=2){std::vector<Candidate>pv;for(auto&z:filtered)if(z.role==PacketRole::EDGE_PICKER)pv.push_back(z);q=schedule(pv);}else q=strategic_pick(filtered,share,immediate);if(picker_.active){if(q.role==PacketRole::EDGE_PICKER)picker_wait_=0;else ++picker_wait_;}if(expansion_available&&q.action_class!=ActionClass::EXPANSION&&!immediate)++expansion_wait_;else if(q.action_class==ActionClass::EXPANSION)expansion_wait_=0;'''
m = repl(m, old_sched, new_sched, 'picker persistence scheduling')

m = repl(m,
    'if(q.reason==Reason::WAR_MOBILIZATION)++stats_.war;if(q.reason==Reason::REAR_EVACUATION)++stats_.rear;',
    'if(q.reason==Reason::WAR_MOBILIZATION)++stats_.war;if(q.reason==Reason::REAR_EVACUATION||q.reason==Reason::EDGE_PICKER)++stats_.rear;',
    'count picker as rear logistics')

m = repl(m,
    'if(a.kind==0){if(q.reason==Reason::GENERAL_EMERGENCY&&q.role==PacketRole::REACTION)++winning_intercepts_;else if(q.reason==Reason::GENERAL_EMERGENCY&&q.role==PacketRole::GENERAL_DEFENSE){if(q.target==general_)++general_reinforcements_;else ++local_blocks_;}commit_packet(o,q);',
    'if(a.kind==0){if(q.reason==Reason::GENERAL_EMERGENCY&&q.role==PacketRole::REACTION)++winning_intercepts_;else if(q.reason==Reason::GENERAL_EMERGENCY&&q.role==PacketRole::GENERAL_DEFENSE){if(q.target==general_)++general_reinforcements_;else ++local_blocks_;}if(q.role==PacketRole::EDGE_PICKER){++picker_moves_;if(q.to==general_){picker_units_delivered_+=std::max(0,o.army[q.from]-1);picker_.active=false;picker_wait_=0;++picker_completions_;}else picker_.cell=q.to;}commit_packet(o,q);',
    'advance persistent picker state')

m = repl(m,
    'std::fprintf(stderr,"[v35_logistics] packets=%zu objective_changes=%ld allowed_reversals=%ld\\n",packets_.size(),objective_changes_,allowed_reversals_);std::fprintf(stderr,"[v35_timing] p50=%.3f p95=%.3f p99=%.3f max=%.3f\\n",pct(.5),pct(.95),pct(.99),times_.back());}',
    'std::fprintf(stderr,"[v35_logistics] packets=%zu objective_changes=%ld allowed_reversals=%ld\\n",packets_.size(),objective_changes_,allowed_reversals_);std::fprintf(stderr,"[v36_picker] threshold=%d starts=%ld completions=%ld moves=%ld delivered=%ld aborts=%ld active=%d\\n",edge_picker_threshold_,picker_starts_,picker_completions_,picker_moves_,picker_units_delivered_,picker_aborts_,picker_.active?1:0);std::fprintf(stderr,"[v35_timing] p50=%.3f p95=%.3f p99=%.3f max=%.3f\\n",pct(.5),pct(.95),pct(.99),times_.back());}',
    'picker telemetry')

m = repl(m,
    'long legacy_escape_started()const{return legacy_escape_started_;}long legacy_escape_actions()const{return legacy_escape_actions_;}long local_blocks()const{return local_blocks_;}long threat_plans_created()const{return threat_plans_created_;}long threat_plans_released()const{return threat_plans_released_;}~Agent(){report();}',
    'long legacy_escape_started()const{return legacy_escape_started_;}long legacy_escape_actions()const{return legacy_escape_actions_;}long local_blocks()const{return local_blocks_;}long threat_plans_created()const{return threat_plans_created_;}long threat_plans_released()const{return threat_plans_released_;}long edge_picker_starts()const{return picker_starts_;}long edge_picker_completions()const{return picker_completions_;}long edge_picker_moves()const{return picker_moves_;}long edge_picker_delivered()const{return picker_units_delivered_;}int edge_picker_threshold()const{return edge_picker_threshold_;}bool edge_picker_active()const{return picker_.active;}~Agent(){report();}',
    'picker test accessors')

picker_test = r'''#define V35_AGENT_TEST
#include "main.cpp"
#include <cassert>
#include <cstdlib>
#include <iostream>

static Observation picker_board(){
 Observation o;o.turn=20;o.type.assign(441,1);o.owner.assign(441,1);o.army.assign(441,1);o.type[220]=4;o.army[220]=5;
 for(int r:{2,5,8})o.army[r*21+20]=3;
 o.my_land=441;o.my_army=452;o.opp_land=0;o.opp_army=0;return o;
}
static int psrc(const Action&a){return a.row*21+a.col;}
static int pdst(const Action&a){if(a.kind)return -1;static int dr[4]={-1,1,0,0},dc[4]={0,0,-1,1};return (a.row+dr[a.dir])*21+a.col+dc[a.dir];}
static void apply_picker(Observation&o,const Action&a){if(a.kind!=0){++o.turn;return;}int x=psrc(a),y=pdst(a),m=o.army[x]-1;o.army[x]=1;if(o.owner[y]==1)o.army[y]+=m;else if(o.owner[y]==2){o.army[y]=std::max(1,m-o.army[y]);o.owner[y]=1;}else{o.owner[y]=1;o.army[y]=std::max(1,m-o.army[y]);}o.my_army=0;o.my_land=0;for(int z=0;z<441;++z)if(o.owner[z]==1){++o.my_land;o.my_army+=o.army[z];}++o.turn;}
int main(){
 {setenv("V35_EDGE_PICKER_THRESHOLD","6",1);Agent a(0,21,21);auto o=picker_board();a.decide(o);assert(a.edge_picker_threshold()==6);assert(a.edge_picker_starts()==0);}
 {setenv("V35_EDGE_PICKER_THRESHOLD","4",1);Agent a(0,21,21);auto o=picker_board();for(int i=0;i<80&&a.edge_picker_completions()==0;++i){auto q=a.decide(o);apply_picker(o,q);}assert(a.edge_picker_threshold()==4);assert(a.edge_picker_starts()>=1);assert(a.edge_picker_moves()>=10);assert(a.edge_picker_completions()>=1);assert(a.edge_picker_delivered()>=6);}
 std::cout<<"v36 edge picker scenarios passed\n";
}
'''
TEST_PICKER.write_text(picker_test)
print('test_picker.cpp: written')

t = repl(t,
    'g++ -O2 -std=c++17 -Wall -Wextra -Wpedantic test_agent.cpp -o test_agent\n./test_agent\n',
    'g++ -O2 -std=c++17 -Wall -Wextra -Wpedantic test_agent.cpp -o test_agent\n./test_agent\n\ng++ -O2 -std=c++17 -Wall -Wextra -Wpedantic test_picker.cpp -o test_picker\n./test_picker\n',
    'run picker regression')

MAIN.write_text(m)
CORE.write_text(c)
TEST_SH.write_text(t)
print('V3.6 persistent edge picker patch complete')
