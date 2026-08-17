#define V35_AGENT_TEST
#include "main.cpp"
#include <algorithm>
#include <cassert>
#include <iostream>
static int src(const Action&a){return a.row*21+a.col;}static int dst(const Action&a){if(a.kind)return -1;static int dr[4]={-1,1,0,0},dc[4]={0,0,-1,1};return (a.row+dr[a.dir])*21+a.col+dc[a.dir];}
static void recalc(Observation&o){o.my_land=0;o.my_army=0;for(int z=0;z<441;++z)if(o.owner[z]==1){++o.my_land;o.my_army+=o.army[z];}}
static void apply(Observation&o,const Action&a){if(a.kind!=0){++o.turn;return;}int x=src(a),y=dst(a),have=o.army[x],moving=a.split?std::max(1,have/2):std::max(0,have-1);if(moving<=0){++o.turn;return;}o.army[x]-=moving;if(o.owner[y]==1)o.army[y]+=moving;else{int defend=std::max(0,o.army[y]);o.owner[y]=1;o.army[y]=std::max(1,moving-defend);if(o.type[y]<0)o.type[y]=1;}recalc(o);++o.turn;}
static Observation stalled(){Observation o;o.turn=61;o.type.assign(441,-1);o.owner.assign(441,-1);o.army.assign(441,0);int g=2*21+18;o.type[g]=4;o.owner[g]=1;o.army[g]=29;for(int z:{2*21+17,2*21+19,1*21+17,1*21+18,1*21+19,3*21+18}){o.type[z]=1;o.owner[z]=1;o.army[z]=1;}o.opp_land=29;o.opp_army=50;recalc(o);assert(o.my_land==7&&o.my_army==35);return o;}
int main(){Agent a(0,21,21);auto o=stalled();int initial=o.my_land,prev_from=-1,prev_to=-1,moves=0;for(int i=0;i<8&&o.my_land==initial;++i){auto q=a.decide(o);assert(q.kind==0);int f=src(q),t=dst(q);if(prev_from>=0)assert(!(f==prev_to&&t==prev_from));prev_from=f;prev_to=t;++moves;apply(o,q);}assert(moves>0);assert(o.my_land>initial);std::cout<<"v36 low-land breakout and anti-zigzag scenarios passed\n";}
