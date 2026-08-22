#define V35_AGENT_TEST
#include "main.cpp"
#include <cassert>
#include <iostream>
static Observation base(){Observation o;o.turn=0;o.type.assign(441,1);o.owner.assign(441,0);o.army.assign(441,0);o.type[220]=4;o.owner[220]=1;o.army[220]=90;o.my_land=1;o.my_army=90;return o;}
static int src(const Action&a){return a.row*21+a.col;}static int dst(const Action&a){if(a.kind)return -1;static int dr[4]={-1,1,0,0},dc[4]={0,0,-1,1};return (a.row+dr[a.dir])*21+a.col+dc[a.dir];}
int main(){
 {Agent a(0,21,21);auto o=base();a.decide(o);int c1=a.planned_castle(0),c2=a.planned_castle(1);assert(c1>=0&&c2>=0&&c1!=c2);assert(a.search_sector_backbone_count()==8);assert(a.search_reachable_sectors()==9);o.turn=120;for(int x=0;x<441;++x)if(x!=220){o.owner[x]=(x%3==0)?1:0;o.army[x]=o.owner[x]?2:0;}o.owner[220]=1;o.army[220]=30;a.decide(o);assert(a.planned_castle(0)==c1&&a.planned_castle(1)==c2);}
 {Packet p;p.target=20;p.event_version=0;p.path={10,11};p.cell=11;assert(route_allowed(p,10,1,1,0,Reason::SEARCH_PROGRESS));p.path={10,11,10};p.cell=10;assert(!route_allowed(p,11,1,1,0,Reason::SEARCH_PROGRESS));p.path={10,11,12,13,10};p.cell=10;assert(!route_allowed(p,11,1,1,0,Reason::SEARCH_PROGRESS));assert(route_allowed(p,11,1,1,0,Reason::GENERAL_EMERGENCY));}
 {Agent a(0,21,21);auto o=base();int t=100,s=101;o.type[t]=3;o.owner[t]=1;o.army[t]=1;o.owner[s]=1;o.army[s]=20;o.my_land=3;o.my_army=111;a.decide(o);o.turn=1;o.owner[t]=2;o.army[t]=2;o.opp_land=1;o.opp_army=2;o.my_land=2;o.my_army=110;auto q=a.decide(o);assert(q.kind==0&&src(q)==s&&dst(q)==t);}
 std::cout<<"selective e50123 invariants passed\n";
}
