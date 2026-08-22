#define V35_AGENT_TEST
#include "main.cpp"
#include <cassert>
#include <cstdlib>
#include <iostream>

static Observation blank_board(){
 Observation o;o.turn=0;o.type.assign(441,1);o.owner.assign(441,0);o.army.assign(441,0);
 int g=10*21+10;o.type[g]=4;o.owner[g]=1;o.army[g]=80;o.my_land=1;o.my_army=80;o.opp_land=0;o.opp_army=0;return o;
}
int main(){
 setenv("V35_EDGE_PICKER_THRESHOLD","16",1);setenv("V36_EDGE_PICKER_MIN_EFFICIENCY","2.0",1);
 Agent a(0,21,21);auto o=blank_board();a.decide(o);
 assert(a.edge_picker_threshold()==16);
 assert(a.search_sector_backbone_count()==8);
 assert(a.search_reachable_sectors()==9);
 assert(a.search_touched_sectors()>=1);
 o.turn=560;o.my_army=120;o.opp_army=20;o.my_land=40;o.opp_land=20;
 auto plan=a.search_probe_plan_for_test(o);
 assert(plan[0]>=0);assert(plan[1]>=0);assert(plan[0]!=plan[1]);
 assert(a.search_probe_forced_for_test(o,plan[0]));
 std::cout<<"v36 sector search refactor scenarios passed\n";
}
