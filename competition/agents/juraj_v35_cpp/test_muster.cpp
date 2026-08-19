#define V35_AGENT_TEST
#include "main.cpp"
#include <cassert>
#include <iostream>

static Observation board(){
 Observation o;o.turn=0;o.type.assign(441,1);o.owner.assign(441,1);o.army.assign(441,1);
 o.type[220]=4;o.army[220]=10;o.my_land=441;o.my_army=450;return o;
}
static void recount(Observation&o){o.my_army=o.my_land=o.opp_army=o.opp_land=0;for(int z=0;z<441;++z){if(o.owner[z]==1){++o.my_land;o.my_army+=o.army[z];}else if(o.owner[z]==2){++o.opp_land;o.opp_army+=o.army[z];}}}
static int src(const Action&a){return a.row*21+a.col;}
static int dst(const Action&a){if(a.kind!=0)return -1;static int dr[4]={-1,1,0,0},dc[4]={0,0,-1,1};return (a.row+dr[a.dir])*21+(a.col+dc[a.dir]);}
static int free_cell(std::initializer_list<int> avoid,int start){for(int x=start;x<441;++x){bool bad=false;for(int a:avoid)bad|=x==a;if(!bad&&x!=220)return x;}return -1;}

int main(){
 // Once both castles exist and the enemy general is known, a late-game army
 // advantage must harvest an interior 8+ donor instead of leaving it idle.
 {
  Agent a(0,21,21);auto o=board();a.decide(o);int c1=a.planned_castle(0),c2=a.planned_castle(1);assert(c1>=0&&c2>=0);
  o.type[c1]=3;o.type[c2]=3;o.army[c1]=8;o.army[c2]=8;
  int eg=20;o.owner[eg]=2;o.type[eg]=4;o.army[eg]=12;
  int anchor=free_cell({c1,c2,eg},300),d1=free_cell({c1,c2,eg,anchor},350),d2=free_cell({c1,c2,eg,anchor,d1},370),d3=free_cell({c1,c2,eg,anchor,d1,d2},390);
  o.army[anchor]=79;o.army[d1]=12;o.army[d2]=10;o.army[d3]=8;o.turn=594;recount(o);
  auto q=a.decide(o);assert(q.kind==0);int s=src(q),t=dst(q);assert(s!=anchor&&s!=220&&s!=c1&&s!=c2);assert(o.army[s]>=8);assert(t>=0&&o.owner[t]==1);
 }
 // Missing C1 after its deadline must trigger active funding rather than be
 // abandoned forever.
 {
  Agent a(0,21,21);auto o=board();a.decide(o);int c1=a.planned_castle(0),c2=a.planned_castle(1);assert(c1>=0);
  int donor=free_cell({c1,c2},400);o.turn=200;o.army[c1]=1;o.army[donor]=150;recount(o);
  auto q=a.decide(o);assert(q.kind==0);assert(src(q)==donor);assert(dst(q)>=0&&o.owner[dst(q)]==1);
 }
 // Capturing the visible enemy general is terminal: do it whenever the stack
 // wins the target, even if post-capture exposure would fail safe_attack().
 {
  Agent a(0,21,21);auto o=board();a.decide(o);int eg=221,strong_enemy=200;o.turn=300;o.owner[eg]=2;o.type[eg]=4;o.army[eg]=5;o.owner[strong_enemy]=2;o.army[strong_enemy]=100;o.army[222]=30;recount(o);
  auto q=a.decide(o);assert(q.kind==0);assert(dst(q)==eg);
 }
 std::cout<<"v9 late muster/castle/general-capture scenarios passed\n";
}
