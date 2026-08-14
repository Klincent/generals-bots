#define V35_AGENT_TEST
#include "main.cpp"
#include <cassert>
#include <iostream>
static Observation board(int turn){Observation o;o.turn=turn;o.type.assign(441,1);o.owner.assign(441,0);o.army.assign(441,0);o.type[220]=4;o.owner[220]=1;o.army[220]=12;o.owner[0]=1;o.army[0]=25;o.my_land=2;o.my_army=37;return o;}
static int destination(const Action&a){if(a.kind)return -1;static int dr[4]={-1,1,0,0},dc[4]={0,0,-1,1};return (a.row+dr[a.dir])*21+a.col+dc[a.dir];}
int main(){
  Agent rear(0,21,21);auto o=board(1);Action a=rear.decide(o);assert(a.kind==0&&a.row==0&&a.col==0);int to=destination(a);assert(to==1||to==21);auto n=o;n.turn=2;n.owner[0]=1;n.army[0]=1;n.owner[to]=1;n.army[to]=24;rear.decide(n);assert(rear.packet_count()>=1); // real state survived an observation/action boundary
  Agent known(0,21,21);auto k=board(20);k.type[230]=4;k.owner[230]=2;k.army[230]=3;k.opp_land=1;k.opp_army=3;known.decide(k);assert(known.enemy_general_confirmed()&&known.enemy_general_cell()==230&&known.active_fronts()==1);
  Agent deficit(0,21,21);auto d=board(45);d.opp_land=30;d.opp_army=20;deficit.decide(d);assert(deficit.production_state()==ProductionState::SEVERE_DEFICIT);
  // A real front remains alive through temporary fog rather than selecting a new largest stack each turn.
  auto fog=k;fog.turn=21;fog.owner[230]=-1;fog.type[230]=-1;known.decide(fog);assert(known.active_fronts()==1);
  std::cout<<"v35 agent: persistent logistics, confirmed general, production and front scenarios passed\n";
}
