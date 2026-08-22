#!/usr/bin/env python3
from pathlib import Path

p=Path('competition/agents/juraj_v35_cpp/main.cpp')
s=p.read_text()

def rep(old,new,label):
    global s
    if new in s:
        print(f'{label}: already applied'); return
    if old not in s:
        raise SystemExit(f'{label}: source pattern not found')
    s=s.replace(old,new,1)
    print(f'{label}: applied')

rep(
'''struct EdgePickerState {bool active=false;int wall=-1,cell=-1,dir=0,phase=0,start_turn=-1,start_army=0;};''',
'''struct EdgePickerState {bool active=false;int wall=-1,cell=-1,dir=0,phase=0,start_turn=-1,start_army=0,blocked_turns=0;};''',
'picker state remembers blocked time')

rep(
''' EdgePickerState picker_;int edge_picker_threshold_=4,picker_wait_=0;long picker_starts_=0,picker_completions_=0,picker_moves_=0,picker_aborts_=0,picker_units_delivered_=0;''',
''' EdgePickerState picker_;int edge_picker_threshold_=4,picker_wait_=0;long picker_starts_=0,picker_completions_=0,picker_moves_=0,picker_aborts_=0,picker_units_delivered_=0,picker_blocked_ticks_=0,picker_lost_aborts_=0,picker_depleted_aborts_=0,picker_source_guard_rejects_=0,picker_critical_preempt_moves_=0;''',
'picker lifecycle telemetry')

rep(
''' bool picker_transit_safe(const Observation&o,int x)const{if(x<0||x>=n_||o.owner[x]!=1||!g_.passable[x])return false;if(x==general_)return true;if(o.type[x]==3||x==castles_.c1||x==castles_.c2)return false;for(int z=0;z<n_;++z)if(o.owner[z]==2&&g_.dist[x][z]<=3)return false;return true;}''',
''' bool picker_transit_safe(const Observation&o,int x)const{if(x<0||x>=n_||o.owner[x]!=1||!g_.passable[x])return false;if(x==general_)return true;if(o.type[x]==3||x==castles_.c1||x==castles_.c2)return false;for(int d=0;d<4;++d){int z=g_.neighbor(x,d);if(z>=0&&o.owner[z]==2)return false;}return true;}\n bool picker_route_safe(const Observation&o,int x,int stack)const{if(x<0||x>=n_||o.owner[x]!=1||!g_.passable[x])return false;if(x==general_)return true;for(int d=0;d<4;++d){int z=g_.neighbor(x,d);if(z>=0&&o.owner[z]==2&&o.army[z]>=std::max(1,stack-1))return false;}return true;}''',
'less brittle picker safety')

rep(
''' int owned_next_to_general(const Observation&o,int from)const{if(from<0||general_<0||from==general_)return -1;std::vector<int>d(n_,-1);std::queue<int>q;d[general_]=0;q.push(general_);while(!q.empty()){int x=q.front();q.pop();for(int k=0;k<4;++k){int y=g_.neighbor(x,k);if(y<0||d[y]>=0||o.owner[y]!=1)continue;if(y!=from&&y!=general_&&!picker_transit_safe(o,y))continue;d[y]=d[x]+1;q.push(y);}}int best=-1,bd=INF;for(int k=0;k<4;++k){int y=g_.neighbor(from,k);if(y>=0&&d[y]>=0&&d[y]<bd){best=y;bd=d[y];}}return best;}''',
''' int owned_next_to_general(const Observation&o,int from)const{if(from<0||general_<0||from==general_)return -1;int stack=std::max(2,o.army[from]);auto search=[&](bool avoid_structures){std::vector<int>d(n_,-1);std::queue<int>q;d[general_]=0;q.push(general_);while(!q.empty()){int x=q.front();q.pop();for(int k=0;k<4;++k){int y=g_.neighbor(x,k);if(y<0||d[y]>=0||o.owner[y]!=1||!g_.passable[y])continue;if(y!=from&&y!=general_){if(avoid_structures&&(o.type[y]==3||y==castles_.c1||y==castles_.c2))continue;if(!picker_route_safe(o,y,stack))continue;}d[y]=d[x]+1;q.push(y);}}int best=-1,bd=INF;for(int k=0;k<4;++k){int y=g_.neighbor(from,k);if(y>=0&&d[y]>=0&&picker_route_safe(o,y,stack)&&d[y]<bd){best=y;bd=d[y];}}return best;};int y=search(true);return y>=0?y:search(false);}\n void drop_packet_at(int x){if(x<0||x>=n_)return;long id=packet_at_[x];if(id){packets_.erase(id);packet_at_[x]=0;}}''',
'resumable route to general')

rep(
'''  if(picker_.active&&(picker_.cell<0||o.owner[picker_.cell]!=1||o.army[picker_.cell]<=1)){picker_.active=false;picker_wait_=0;++picker_aborts_;}''',
'''  if(picker_.active&&(picker_.cell<0||picker_.cell>=n_||o.owner[picker_.cell]!=1)){picker_.active=false;picker_wait_=0;++picker_aborts_;++picker_lost_aborts_;}\n  else if(picker_.active&&o.army[picker_.cell]<=1){picker_.active=false;picker_wait_=0;++picker_aborts_;++picker_depleted_aborts_;}''',
'abort only when picker stack is genuinely lost')

rep(
'''if(start>=0){int c0=wall_coord(start,best_wall);picker_={true,best_wall,start,c0<proj?1:c0>proj?-1:0,0,o.turn,o.army[start]};picker_wait_=2;++picker_starts_;}''',
'''if(start>=0&&owned_next_to_general(o,start)>=0){int c0=wall_coord(start,best_wall);picker_={true,best_wall,start,c0<proj?1:c0>proj?-1:0,0,o.turn,o.army[start],0};picker_wait_=0;++picker_starts_;}''',
'only start completable picker')

rep(
'''  if(picker_.active){int x=picker_.cell,y=-1,proj=(picker_.wall==0||picker_.wall==2)?general_%w_:general_/w_;if(picker_.phase==0){int cc=wall_coord(x,picker_.wall);if(cc!=proj&&picker_.dir!=0){int z=wall_cell_at(picker_.wall,cc+picker_.dir);if(z>=0&&picker_transit_safe(o,z))y=z;else picker_.phase=1;}else picker_.phase=1;}if(picker_.phase==1)y=owned_next_to_general(o,x);if(y>=0&&source(o,x)&&o.owner[y]==1)c.push_back({2,x,y,0,3000.+o.army[x]*5.,Reason::EDGE_PICKER,false,ActionClass::LOGISTICS,general_,-1,PacketRole::EDGE_PICKER});else if(picker_.phase==1&&x!=general_){picker_.active=false;picker_wait_=0;++picker_aborts_;}}''',
'''  if(picker_.active){int x=picker_.cell,y=-1,proj=(picker_.wall==0||picker_.wall==2)?general_%w_:general_/w_;if(picker_.phase==0){int cc=wall_coord(x,picker_.wall);if(cc!=proj&&picker_.dir!=0){int z=wall_cell_at(picker_.wall,cc+picker_.dir);if(z>=0&&picker_transit_safe(o,z))y=z;else picker_.phase=1;}else picker_.phase=1;}if(picker_.phase==1)y=owned_next_to_general(o,x);if(y>=0&&source(o,x)&&o.owner[y]==1){picker_.blocked_turns=0;c.push_back({2,x,y,0,3000.+o.army[x]*5.,Reason::EDGE_PICKER,false,ActionClass::LOGISTICS,general_,-1,PacketRole::EDGE_PICKER});}else if(x!=general_){++picker_.blocked_turns;++picker_blocked_ticks_;}}''',
'blocked picker pauses instead of aborting')

old_filter='''  std::vector<Candidate>filtered;for(auto&q:c){bool reject=history_cycle(q)||!packet_route_ok(q);if(reject&&q.tier>1&&q.role!=PacketRole::EDGE_PICKER){++candidate_reject_;continue;}filtered.push_back(q);}bool expansion_available=std::any_of(filtered.begin(),filtered.end(),[](auto&q){return q.action_class==ActionClass::EXPANSION;});bool picker_available=std::any_of(filtered.begin(),filtered.end(),[](auto&q){return q.role==PacketRole::EDGE_PICKER;});bool hard_available=std::any_of(filtered.begin(),filtered.end(),[](auto&q){return q.tier<=1;});double logistics_share=picker_.active?.24:(confirmed_war?.22:.15);std::array<double,5>share{{0,confirmed_war?.30:.12,production_==ProductionState::SEVERE_DEFICIT?.62:production_==ProductionState::SOFT_DEFICIT?.45:.35,!enemy_seen?.20:.08,logistics_share}};double total=share[1]+share[2]+share[3]+share[4];for(int i=1;i<5;++i)share[i]/=total;Candidate q;if(!hard_available&&picker_available&&picker_wait_>=2){std::vector<Candidate>pv;for(auto&z:filtered)if(z.role==PacketRole::EDGE_PICKER)pv.push_back(z);q=schedule(pv);}else q=strategic_pick(filtered,share,immediate);if(picker_.active){if(q.role==PacketRole::EDGE_PICKER)picker_wait_=0;else ++picker_wait_;}if(expansion_available&&q.action_class!=ActionClass::EXPANSION&&!immediate)++expansion_wait_;else if(q.action_class==ActionClass::EXPANSION)expansion_wait_=0;'''
new_filter='''  std::vector<Candidate>filtered;for(auto&q:c){bool reserved=picker_.active&&q.from==picker_.cell&&q.role!=PacketRole::EDGE_PICKER&&q.reason!=Reason::GENERAL_EMERGENCY&&q.reason!=Reason::TERMINAL_CAPTURE;if(reserved){++picker_source_guard_rejects_;continue;}bool reject=history_cycle(q)||!packet_route_ok(q);if(reject&&q.tier>1&&q.role!=PacketRole::EDGE_PICKER){++candidate_reject_;continue;}filtered.push_back(q);}bool expansion_available=std::any_of(filtered.begin(),filtered.end(),[](auto&q){return q.action_class==ActionClass::EXPANSION;});bool picker_available=std::any_of(filtered.begin(),filtered.end(),[](auto&q){return q.role==PacketRole::EDGE_PICKER;});auto critical=[](const Candidate&q){return q.tier<=1&&(q.reason==Reason::TERMINAL_CAPTURE||q.reason==Reason::GENERAL_EMERGENCY||q.reason==Reason::CASTLE_DEADLINE);};bool critical_available=std::any_of(filtered.begin(),filtered.end(),critical);double logistics_share=picker_.active?.24:(confirmed_war?.22:.15);std::array<double,5>share{{0,confirmed_war?.30:.12,production_==ProductionState::SEVERE_DEFICIT?.62:production_==ProductionState::SOFT_DEFICIT?.45:.35,!enemy_seen?.20:.08,logistics_share}};double total=share[1]+share[2]+share[3]+share[4];for(int i=1;i<5;++i)share[i]/=total;Candidate q;if(picker_.active&&critical_available){std::vector<Candidate>hv;for(auto&z:filtered)if(critical(z))hv.push_back(z);q=schedule(hv);}else if(picker_.active&&picker_available){std::vector<Candidate>pv;for(auto&z:filtered)if(z.role==PacketRole::EDGE_PICKER)pv.push_back(z);q=schedule(pv);}else q=strategic_pick(filtered,share,immediate);if(picker_.active){if(q.role==PacketRole::EDGE_PICKER)picker_wait_=0;else ++picker_wait_;}if(expansion_available&&q.action_class!=ActionClass::EXPANSION&&!immediate)++expansion_wait_;else if(q.action_class==ActionClass::EXPANSION)expansion_wait_=0;'''
rep(old_filter,new_filter,'reserve active picker and resume immediately after critical work')

old_exec='''if(q.role==PacketRole::EDGE_PICKER){++picker_moves_;if(q.to==general_){picker_units_delivered_+=std::max(0,o.army[q.from]-1);picker_.active=false;picker_wait_=0;++picker_completions_;}else picker_.cell=q.to;}commit_packet(o,q);'''
new_exec='''if(q.role==PacketRole::EDGE_PICKER){++picker_moves_;if(q.to==general_){picker_units_delivered_+=std::max(0,o.army[q.from]-1);picker_.active=false;picker_wait_=0;picker_.blocked_turns=0;++picker_completions_;}else{picker_.cell=q.to;picker_.blocked_turns=0;}}else if(picker_.active&&q.from==picker_.cell&&(q.reason==Reason::GENERAL_EMERGENCY||q.reason==Reason::TERMINAL_CAPTURE)){picker_.cell=q.to;picker_.phase=1;picker_.blocked_turns=0;++picker_critical_preempt_moves_;}commit_packet(o,q);if(q.role==PacketRole::EDGE_PICKER&&!picker_.active)drop_packet_at(q.to);'''
rep(old_exec,new_exec,'resume picker after critical source preemption and release packet on delivery')

rep(
'''std::fprintf(stderr,"[v36_picker] threshold=%d starts=%ld completions=%ld moves=%ld delivered=%ld aborts=%ld active=%d\\n",edge_picker_threshold_,picker_starts_,picker_completions_,picker_moves_,picker_units_delivered_,picker_aborts_,picker_.active?1:0);''',
'''std::fprintf(stderr,"[v36_picker] threshold=%d starts=%ld completions=%ld moves=%ld delivered=%ld aborts=%ld active=%d blocked_ticks=%ld lost_aborts=%ld depleted_aborts=%ld source_guard=%ld critical_preempt_moves=%ld\\n",edge_picker_threshold_,picker_starts_,picker_completions_,picker_moves_,picker_units_delivered_,picker_aborts_,picker_.active?1:0,picker_blocked_ticks_,picker_lost_aborts_,picker_depleted_aborts_,picker_source_guard_rejects_,picker_critical_preempt_moves_);''',
'picker abort reason telemetry')

rep(
'''long edge_picker_starts()const{return picker_starts_;}long edge_picker_completions()const{return picker_completions_;}long edge_picker_moves()const{return picker_moves_;}long edge_picker_delivered()const{return picker_units_delivered_;}int edge_picker_threshold()const{return edge_picker_threshold_;}bool edge_picker_active()const{return picker_.active;}''',
'''long edge_picker_starts()const{return picker_starts_;}long edge_picker_completions()const{return picker_completions_;}long edge_picker_moves()const{return picker_moves_;}long edge_picker_delivered()const{return picker_units_delivered_;}long edge_picker_aborts()const{return picker_aborts_;}long edge_picker_blocked_ticks()const{return picker_blocked_ticks_;}long edge_picker_source_guard_rejects()const{return picker_source_guard_rejects_;}int edge_picker_cell()const{return picker_.cell;}int edge_picker_threshold()const{return edge_picker_threshold_;}bool edge_picker_active()const{return picker_.active;}''',
'picker test accessors')

p.write_text(s)

t=Path('competition/agents/juraj_v35_cpp/test_picker.cpp')
t.write_text(r'''#define V35_AGENT_TEST
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
static void recount(Observation&o){o.my_army=o.my_land=o.opp_army=o.opp_land=0;for(int z=0;z<441;++z){if(o.owner[z]==1){++o.my_land;o.my_army+=o.army[z];}else if(o.owner[z]==2){++o.opp_land;o.opp_army+=o.army[z];}}}
static void apply_picker(Observation&o,const Action&a){if(a.kind!=0){++o.turn;return;}int x=psrc(a),y=pdst(a),m=o.army[x]-1;o.army[x]=1;if(o.owner[y]==1)o.army[y]+=m;else if(o.owner[y]==2){if(m>o.army[y]){o.army[y]=m-o.army[y];o.owner[y]=1;}else{o.army[y]-=m;}}else{o.owner[y]=1;o.army[y]=std::max(1,m-o.army[y]);}recount(o);++o.turn;}
int main(){
 {setenv("V35_EDGE_PICKER_THRESHOLD","6",1);Agent a(0,21,21);auto o=picker_board();a.decide(o);assert(a.edge_picker_threshold()==6);assert(a.edge_picker_starts()==0);}
 {setenv("V35_EDGE_PICKER_THRESHOLD","4",1);Agent a(0,21,21);auto o=picker_board();for(int i=0;i<80&&a.edge_picker_completions()==0;++i){auto q=a.decide(o);apply_picker(o,q);}assert(a.edge_picker_threshold()==4);assert(a.edge_picker_starts()==1);assert(a.edge_picker_moves()>=10);assert(a.edge_picker_completions()==1);assert(a.edge_picker_delivered()>=6);assert(a.edge_picker_aborts()==0);}
 // An opportunistic attack from the picker cell must not steal the collector.
 {setenv("V35_EDGE_PICKER_THRESHOLD","4",1);Agent a(0,21,21);auto o=picker_board();auto first=a.decide(o);assert(first.kind==0);apply_picker(o,first);int pc=a.edge_picker_cell();assert(pc>=0);int inward=pc-1;o.owner[inward]=2;o.army[inward]=1;recount(o);auto q=a.decide(o);assert(a.edge_picker_active());assert(a.edge_picker_starts()==1);assert(psrc(q)==pc);assert(pdst(q)!=inward);assert(a.edge_picker_source_guard_rejects()>0);apply_picker(o,q);o.owner[inward]=1;o.army[inward]=1;recount(o);for(int i=0;i<80&&a.edge_picker_completions()==0;++i){auto z=a.decide(o);apply_picker(o,z);}assert(a.edge_picker_completions()==1);assert(a.edge_picker_aborts()==0);}
 // A real general emergency may pause other work; once it clears, the same picker resumes.
 {setenv("V35_EDGE_PICKER_THRESHOLD","4",1);Agent a(0,21,21);auto o=picker_board();auto first=a.decide(o);apply_picker(o,first);int pc=a.edge_picker_cell();int enemy=219;o.owner[enemy]=2;o.army[enemy]=8;o.army[218]=12;recount(o);auto emergency=a.decide(o);assert(emergency.kind==0);assert(psrc(emergency)!=pc);assert(a.edge_picker_active());assert(a.edge_picker_cell()==pc);apply_picker(o,emergency);o.owner[enemy]=1;o.army[enemy]=1;recount(o);auto resume=a.decide(o);assert(resume.kind==0);assert(psrc(resume)==pc);apply_picker(o,resume);for(int i=0;i<80&&a.edge_picker_completions()==0;++i){auto z=a.decide(o);apply_picker(o,z);}assert(a.edge_picker_completions()==1);assert(a.edge_picker_aborts()==0);}
 std::cout<<"v36 edge picker lifecycle scenarios passed\n";
}
''')
print('test_picker.cpp: lifecycle regressions written')
print('V3.6 picker lifecycle fix complete')
