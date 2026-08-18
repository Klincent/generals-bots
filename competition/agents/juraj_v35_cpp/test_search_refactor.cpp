#define V35_AGENT_TEST
#include "main.cpp"
#include <cassert>
#include <cstdlib>
#include <iostream>

static Observation blank_board(){
 Observation o;o.turn=0;o.type.assign(441,1);o.owner.assign(441,0);o.army.assign(441,0);
 int g=10*21+10;o.type[g]=4;o.owner[g]=1;o.army[g]=80;o.my_land=1;o.my_army=80;o.opp_land=0;o.opp_army=0;return o;
}
static int sector_center(int s){int r=(s/3)*7+3,c=(s%3)*7+3;return r*21+c;}
int main(){
 setenv("V35_EDGE_PICKER_THRESHOLD","16",1);setenv("V36_EDGE_PICKER_MIN_EFFICIENCY","2.0",1);
 Agent a(0,21,21);auto o=blank_board();a.decide(o);
 assert(a.edge_picker_threshold()==16);
 assert(a.search_sector_backbone_count()==8);
 assert(a.search_reachable_sectors()==9);
 assert(a.search_touched_sectors()>=1);
 // Conservative 3x3 policy does not steal early-game moves.
 o.turn=90;auto early=a.search_probe_plan_for_test(o);assert(early[0]<0&&early[1]<0);
 // Late coverage debt activates exactly one untouched sector at a time.
 o.turn=560;o.my_army=120;o.opp_army=20;o.my_land=40;o.opp_land=20;
 auto plan=a.search_probe_plan_for_test(o);assert(plan[0]>=0);assert(plan[1]<0);assert(a.search_probe_forced_for_test(o,plan[0]));
 // Touch that sector; the next plan must move to another untouched sector.
 int x=sector_center(plan[0]);o.owner[x]=1;o.army[x]=2;++o.my_land;o.my_army+=2;a.decide(o);
 auto next=a.search_probe_plan_for_test(o);assert(next[1]<0);assert(next[0]<0||next[0]!=plan[0]);
 // Once every 3x3 sector has been touched, exploration has no remaining target.
 for(int s=0;s<9;++s){int z=sector_center(s);if(o.owner[z]!=1){o.owner[z]=1;o.army[z]=2;++o.my_land;o.my_army+=2;}}
 ++o.turn;a.decide(o);auto done=a.search_probe_plan_for_test(o);assert(done[0]<0&&done[1]<0);
 std::cout<<"v36 conservative 3x3 exploration scenarios passed\n";
}
