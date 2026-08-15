#define V35_AGENT_TEST
#include "main.cpp"
#include <cassert>
#include <iostream>
static Observation board(int turn=1){Observation o;o.turn=turn;o.type.assign(441,1);o.owner.assign(441,0);o.army.assign(441,0);o.type[220]=4;o.owner[220]=1;o.army[220]=12;o.my_land=1;o.my_army=12;return o;}
static int src(const Action&a){return a.row*21+a.col;}static int dst(const Action&a){if(a.kind)return -1;static int dr[4]={-1,1,0,0},dc[4]={0,0,-1,1};return (a.row+dr[a.dir])*21+a.col+dc[a.dir];}
static void apply(Observation&o,const Action&a){if(a.kind!=0){++o.turn;return;}int x=src(a),y=dst(a),m=o.army[x]-1;if(o.owner[y]==2)m-=o.army[y];o.owner[y]=1;o.army[y]=std::max(1,m);o.army[x]=1;o.my_land=std::count(o.owner.begin(),o.owner.end(),1);o.my_army=0;for(int z=0;z<441;++z)if(o.owner[z]==1)o.my_army+=o.army[z];++o.turn;}
int main(){
 // Favorable ordinary conquest is explicit; losing head-on combat is never selected.
 {Agent a(0,21,21);auto o=board();o.owner[40]=1;o.army[40]=20;o.owner[41]=2;o.army[41]=5;for(int z:{19,39,61})o.owner[z]=1,o.army[z]=1;auto q=a.decide(o);assert(q.kind==0&&src(q)==40&&dst(q)==41);}
 {Agent a(0,21,21);auto o=board();o.owner[40]=1;o.army[40]=5;o.owner[41]=2;o.army[41]=20;for(int z:{19,39,61})o.owner[z]=1,o.army[z]=1;auto q=a.decide(o);assert(!(q.kind==0&&src(q)==40&&dst(q)==41));}
 // Distant static territory is intelligence, not contact/front/war.
 {Agent a(0,21,21);auto o=board();for(int x=0;x<12;++x)o.owner[x]=2,o.army[x]=1;o.opp_land=12;o.opp_army=12;a.decide(o);assert(a.active_fronts()==0&&a.meaningful_contact_turn()<0);assert(a.confidence()[(int)Archetype::SMALL_PACKET_SWARM]<.2);}
 // Interaction adjacent to our territory creates exactly one clustered front.
 {Agent a(0,21,21);auto o=board();for(int x:{22,23,24,25})o.owner[x]=2,o.army[x]=8;o.owner[43]=1;o.army[43]=3;o.opp_land=4;o.opp_army=32;a.decide(o);assert(a.active_fronts()==1&&a.meaningful_contact_turn()==1);}
 // Strategic action debt prevents a live front/logistics stream starving expansion.
 {Agent a(0,21,21);auto o=board();o.owner[22]=2;o.army[22]=20;o.owner[23]=1;o.army[23]=2;o.owner[420]=1;o.army[420]=35;o.my_army=49;o.my_land=3;o.opp_land=25;o.opp_army=20;for(int i=0;i<8;++i){auto q=a.decide(o);apply(o,q);}assert(a.action_stats().expansion>0);assert(a.production_state()==ProductionState::SEVERE_DEFICIT);}
 // Packet creation happens only for selected actions, and persists over observations.
 {Agent a(0,21,21);auto o=board();o.owner[0]=1;o.army[0]=25;o.my_land=2;o.my_army=37;auto q=a.decide(o);size_t before=a.packet_count();apply(o,q);a.decide(o);assert(before<=1&&a.packet_count()>=1&&a.objective_changes()<=2);}
 // Confirmed general remains exact despite later fog.
 {Agent a(0,21,21);auto o=board();o.type[230]=4;o.owner[230]=2;o.army[230]=3;o.owner[229]=1;o.army[229]=1;a.decide(o);assert(a.enemy_general_confirmed()&&a.enemy_general_cell()==230);o.turn++;o.type[230]=-1;o.owner[230]=-1;a.decide(o);assert(a.enemy_general_cell()==230);}
 std::cout<<"v35 agent recovery scenarios passed\n";
}
