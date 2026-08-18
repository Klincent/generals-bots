#define V35_AGENT_TEST
#include "main.cpp"
#include <cassert>
#include <cstdlib>
#include <iostream>

static Observation picker_board(){
 Observation o;o.turn=100;o.type.assign(441,1);o.owner.assign(441,1);o.army.assign(441,1);o.type[220]=4;o.army[220]=5;
 for(int r:{2,5,8})o.army[r*21+20]=3;
 o.my_land=441;o.my_army=452;o.opp_land=0;o.opp_army=0;return o;
}
static int psrc(const Action&a){return a.row*21+a.col;}
static int pdst(const Action&a){if(a.kind)return -1;static int dr[4]={-1,1,0,0},dc[4]={0,0,-1,1};return (a.row+dr[a.dir])*21+a.col+dc[a.dir];}
static void recount(Observation&o){o.my_army=o.my_land=o.opp_army=o.opp_land=0;for(int z=0;z<441;++z){if(o.owner[z]==1){++o.my_land;o.my_army+=o.army[z];}else if(o.owner[z]==2){++o.opp_land;o.opp_army+=o.army[z];}}}
static void apply_picker(Observation&o,const Action&a){if(a.kind!=0){++o.turn;return;}int x=psrc(a),y=pdst(a),m=o.army[x]-1;o.army[x]=1;if(o.owner[y]==1)o.army[y]+=m;else if(o.owner[y]==2){if(m>o.army[y]){o.army[y]=m-o.army[y];o.owner[y]=1;}else{o.army[y]-=m;}}else{o.owner[y]=1;o.army[y]=std::max(1,m-o.army[y]);}recount(o);++o.turn;}
int main(){
 setenv("V36_EDGE_PICKER_MIN_EFFICIENCY","0",1);
 {setenv("V35_EDGE_PICKER_THRESHOLD","6",1);Agent a(0,21,21);auto o=picker_board();a.decide(o);assert(a.edge_picker_threshold()==6);assert(a.edge_picker_starts()==0);}
 {setenv("V35_EDGE_PICKER_THRESHOLD","4",1);Agent a(0,21,21);auto o=picker_board();for(int i=0;i<80&&a.edge_picker_completions()==0;++i){auto q=a.decide(o);apply_picker(o,q);}assert(a.edge_picker_threshold()==4);assert(a.edge_picker_starts()==1);assert(a.edge_picker_moves()>=10);assert(a.edge_picker_completions()==1);assert(a.edge_picker_delivered()>=6);assert(a.edge_picker_aborts()==0);}
 // An opportunistic attack from the picker cell must not steal the collector.
 {setenv("V35_EDGE_PICKER_THRESHOLD","4",1);Agent a(0,21,21);auto o=picker_board();auto first=a.decide(o);assert(first.kind==0);apply_picker(o,first);int pc=a.edge_picker_cell();assert(pc>=0);int inward=pc-1;o.owner[inward]=2;o.army[inward]=1;recount(o);auto q=a.decide(o);assert(a.edge_picker_active());assert(a.edge_picker_starts()==1);assert(psrc(q)==pc);assert(pdst(q)!=inward);assert(a.edge_picker_source_guard_rejects()>0);apply_picker(o,q);o.owner[inward]=1;o.army[inward]=1;recount(o);for(int i=0;i<80&&a.edge_picker_completions()==0;++i){auto z=a.decide(o);apply_picker(o,z);}assert(a.edge_picker_completions()==1);assert(a.edge_picker_aborts()==0);}
 // A real general emergency may pause other work; once it clears, the same picker resumes.
 {setenv("V35_EDGE_PICKER_THRESHOLD","4",1);Agent a(0,21,21);auto o=picker_board();auto first=a.decide(o);apply_picker(o,first);int pc=a.edge_picker_cell();int enemy=219;o.owner[enemy]=2;o.army[enemy]=8;o.army[218]=12;recount(o);auto emergency=a.decide(o);assert(emergency.kind==0);assert(psrc(emergency)!=pc);assert(a.edge_picker_active());assert(a.edge_picker_cell()==pc);apply_picker(o,emergency);o.owner[enemy]=1;o.army[enemy]=1;recount(o);auto resume=a.decide(o);assert(resume.kind==0);assert(psrc(resume)==pc);apply_picker(o,resume);for(int i=0;i<80&&a.edge_picker_completions()==0;++i){auto z=a.decide(o);apply_picker(o,z);}assert(a.edge_picker_completions()==1);assert(a.edge_picker_aborts()==0);}
 std::cout<<"v36 edge picker lifecycle scenarios passed\n";
}
