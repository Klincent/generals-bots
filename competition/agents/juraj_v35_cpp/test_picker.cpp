#define V35_AGENT_TEST
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
