#define V35_AGENT_TEST
#include "main.cpp"
#include <cassert>
#include <cstdlib>
#include <iostream>

static Observation board(){
 Observation o;o.turn=120;o.type.assign(441,1);o.owner.assign(441,1);o.army.assign(441,1);
 o.type[220]=4;o.army[220]=8;o.my_land=441;o.my_army=448;o.opp_land=0;o.opp_army=0;return o;
}
static void recalc(Observation&o){o.my_army=0;o.my_land=0;for(int z=0;z<441;++z)if(o.owner[z]==1){++o.my_land;o.my_army+=o.army[z];}}
int main(){
 setenv("V35_EDGE_PICKER_THRESHOLD","8",1);setenv("V36_EDGE_PICKER_MIN_EFFICIENCY","2.0",1);
 // Whole-wall mass must not falsely combine two separate sweep rays.
 {Agent a(0,21,21);auto o=board();for(int r:{4,7,13,16})o.army[r*21+20]=3;recalc(o);a.decide(o);assert(a.edge_picker_starts()==0);assert(!a.edge_picker_active());}
 // A large but very sparse/distant sweep is rejected by army-per-move economics.
 {Agent a(0,21,21);auto o=board();o.army[2*21+20]=12;recalc(o);a.decide(o);assert(a.edge_picker_starts()==0);assert(a.edge_picker_efficiency_rejects()>0);}
 // Dense valuable ray starts and lifecycle still runs it all the way to the general.
 {Agent a(0,21,21);auto o=board();for(int r:{2,3,4,5,6,7,8,9})o.army[r*21+20]=8;recalc(o);for(int i=0;i<100&&a.edge_picker_completions()==0;++i){auto q=a.decide(o);if(q.kind==0){static int dr[4]={-1,1,0,0},dc[4]={0,0,-1,1};int x=q.row*21+q.col,y=(q.row+dr[q.dir])*21+q.col+dc[q.dir],m=o.army[x]-1;o.army[x]=1;o.army[y]+=m;recalc(o);}++o.turn;}assert(a.edge_picker_starts()==1);assert(a.edge_picker_completions()==1);assert(a.edge_picker_aborts()==0);assert(a.edge_picker_delivered()>20);}
 std::cout<<"v36 picker economics scenarios passed\n";
}
