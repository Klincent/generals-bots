#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <deque>
#include <limits>
#include <numeric>
#include <optional>
#include <queue>
#include <string>
#include <tuple>
#include <vector>

namespace v35 {
constexpr int INF=1000000;
enum class PacketRole {GENERAL_DEFENSE,REACTION,CASTLE_C1,CASTLE_C2,EXPANSION,SEARCH,FRONT,ATTACK,COUNTERATTACK,FREE_SURPLUS_RELOCATION};
enum class Reason {NONE,TERMINAL_CAPTURE,GENERAL_EMERGENCY,CASTLE_DEADLINE,PRODUCTION_TICK,WAR_MOBILIZATION,REAR_EVACUATION,SEARCH_PROGRESS,TOPOLOGY_CHANGED,OPPONENT_EXPLOIT};
enum class ProductionState {HEALTHY,SOFT_DEFICIT,SEVERE_DEFICIT};
enum class Archetype {EXPANSION_RUSHER,PRODUCTION_ECONOMY,CASTLE_BUILDER,DOOMSTACK,SMALL_PACKET_SWARM,GENERAL_RUSH,TURTLE,MULTI_FRONT,HOARDER,DEATHTOUCH_PREP,COUNT};
struct Graph {int h=0,w=0;std::vector<char> passable;std::vector<std::vector<int>> dist,next;
 int neighbor(int x,int d)const{static constexpr int dr[4]={-1,1,0,0},dc[4]={0,0,-1,1};int r=x/w+dr[d],c=x%w+dc[d];return r>=0&&r<h&&c>=0&&c<w?r*w+c:-1;}
 void build(){int n=h*w;dist.assign(n,std::vector<int>(n,INF));next.assign(n,std::vector<int>(n,-1));for(int s=0;s<n;++s)if(passable[s]){std::queue<int>q;q.push(s);dist[s][s]=0;while(!q.empty()){int x=q.front();q.pop();for(int d=0;d<4;++d){int y=neighbor(x,d);if(y>=0&&passable[y]&&dist[s][y]==INF){dist[s][y]=dist[s][x]+1;next[s][y]=x==s?y:next[s][x];q.push(y);}}}}}
 int degree(int x)const{int z=0;for(int d=0;d<4;++d){int y=neighbor(x,d);z+=y>=0&&passable[y];}return z;}
};
struct CastleChoice {int c1=-1,c2=-1,c3=-1,cost1=0,cost2=0,total=INF;};
inline int castle_cost(const Graph&g,int general,int x,const std::vector<int>&structures){int md=std::abs(x/g.w-general/g.w)+std::abs(x%g.w-general%g.w);int c=35+std::max(0,14-2*md);for(int s:structures){int d=std::abs(x/g.w-s/g.w)+std::abs(x%g.w-s%g.w);c+=std::max(0,14-2*d);}return c;}
inline CastleChoice plan_castles(const Graph&g,int general){CastleChoice best;int n=g.h*g.w;auto eligible=[&](int x,int deadline){return x!=general&&g.passable[x]&&g.dist[general][x]>=5&&g.dist[general][x]<INF&&g.dist[general][x]+35<=deadline&&g.degree(x)>1;};for(int a=0;a<n;++a)if(eligible(a,150))for(int b=0;b<n;++b)if(b!=a&&eligible(b,250)){int ca=castle_cost(g,general,a,{}),cb=castle_cost(g,general,b,{a});auto key=std::tuple(ca+cb,std::max(g.dist[general][a],g.dist[general][b]),-(g.degree(a)+g.degree(b)),a,b);auto old=std::tuple(best.total,best.c1<0?INF:std::max(g.dist[general][best.c1],g.dist[general][best.c2]),best.c1<0?0:-(g.degree(best.c1)+g.degree(best.c2)),best.c1,best.c2);if(key<old)best={a,b,-1,ca,cb,ca+cb};}for(int x=0;x<n;++x)if(eligible(x,350)&&x!=best.c1&&x!=best.c2){best.c3=x;break;}return best;}
struct FundingForecast {int required=0,turns=0,capacity=0,latest_start=0;bool feasible=false,must_fund=false;};
inline FundingForecast forecast(int turn,int deadline,int cost,int site_army,const std::vector<std::pair<int,int>>&feeders){FundingForecast f;f.required=std::max(0,cost-site_army);f.turns=std::max(0,deadline-turn);int max_eta=0;for(auto [army,eta]:feeders)if(eta<=f.turns){f.capacity+=std::max(0,army-1);max_eta=std::max(max_eta,eta);}f.feasible=f.capacity>=f.required;f.latest_start=deadline-max_eta-std::max(0,(f.required+9)/10);f.must_fund=turn>=f.latest_start&&f.required>0;return f;}
struct Packet {int cell=-1,army=0,target=-1,assigned_turn=0,event_version=0,idle=0;PacketRole role=PacketRole::EXPANSION;std::deque<int> path;};
inline bool route_allowed(const Packet&p,int dest,int new_distance,int old_distance,int event_version,Reason reason){bool changed=event_version!=p.event_version&&reason!=Reason::NONE;if(!changed&&new_distance>old_distance)return false;if(!changed&&p.path.size()>=2&&dest==p.path[p.path.size()-2])return false;if(!changed&&p.path.size()>=3&&dest==p.path[p.path.size()-3])return false;if(!changed&&p.path.size()>=4&&dest==p.path[p.path.size()-4])return false;return true;}
struct Budget {int general_defense=0,reaction=0,c1=0,c2=0,expansion=0,search=0,front=0,free=0,war=0;};
inline Budget budget(int total,int general_army,int c1,int c2,bool contact,double aggression){Budget b;b.general_defense=std::max(5,general_army/2);b.reaction=contact?std::max(8,total/10):std::max(3,total/20);b.c1=c1;b.c2=c2;int left=std::max(0,total-b.general_defense-b.reaction-c1-c2);b.expansion=left*(contact?15:35)/100;b.search=left*(contact?10:25)/100;b.war=contact?int(left*std::clamp(aggression,.35,.85)):0;b.front=b.war;b.free=std::max(0,left-b.expansion-b.search-b.front);return b;}
struct OpponentEvidence {double land_velocity=0,army_velocity=0,concentration=0,median_packet=0,fronts=0,closing=0,castles=0,activity=0,reaction_ratio=0,retreat=0;int turn=0,samples=0;};
struct Adaptation {double attack=.45,search=.25,defense=.2,expansion=.3;int fronts=1;std::string response="NORMAL_PLAN";};
class OpponentModel {std::array<double,(int)Archetype::COUNT> p_{};public:OpponentModel(){p_.fill(.05);}const auto& confidence()const{return p_;}void update(const OpponentEvidence&e){std::array<double,10> raw{{e.land_velocity*.12+(1-e.concentration)*.4,e.land_velocity*.08+e.army_velocity*.06,e.castles*.45,e.concentration,e.activity*.15+(1-e.concentration)*.5,(e.turn<250?e.closing*.8:0),(1-e.activity)*.55+e.reaction_ratio*.2,std::min(1.,e.fronts/3.),(1-e.activity)*.6+e.army_velocity*.04,e.turn>700?std::min(1.,(e.turn-700)/100.+e.concentration*.3):0}};double alpha=e.samples>=3?.18:.05;for(int i=0;i<10;++i){double target=std::clamp(raw[i],0.,1.);p_[i]=std::clamp(p_[i]*(1-alpha)+target*alpha,0.,1.);}}
 Adaptation adaptation()const{Adaptation a;auto hi=[&](Archetype x){return p_[(int)x]>.55;};if(hi(Archetype::GENERAL_RUSH)){a.defense=.55;a.response="INTERCEPT_RUSH";}if(hi(Archetype::DOOMSTACK)){a.attack=.6;a.response="COUNTERATTACK_WEAK_REAR";}if(hi(Archetype::SMALL_PACKET_SWARM)){a.defense=.28;a.response="CONSOLIDATED_SWEEP";}if(hi(Archetype::EXPANSION_RUSHER)){a.attack=.62;a.response="CUT_WEAK_CHAINS";}if(hi(Archetype::PRODUCTION_ECONOMY)){a.search=.55;a.attack=.6;a.response="ECONOMY_URGENCY";}if(hi(Archetype::CASTLE_BUILDER)){a.fronts=2;a.response="FLANK_POST_INVESTMENT";}if(hi(Archetype::TURTLE)){a.expansion=.55;a.fronts=2;a.response="MULTI_AXIS_PRESSURE";}if(hi(Archetype::MULTI_FRONT)){a.defense=.4;a.response="CENTRAL_REACTION";}if(hi(Archetype::HOARDER)){a.expansion=.6;a.search=.45;a.response="MAP_EXPLOIT";}if(hi(Archetype::DEATHTOUCH_PREP)){a.defense=.7;a.response="DISRUPT_STAGING";}return a;}};
class Belief {std::vector<double> p_;public:void initialise(const Graph&g,int general){p_.assign(g.h*g.w,0);for(int x=0;x<g.h*g.w;++x)if(g.passable[x]&&g.dist[general][x]>=17)p_[x]=1;normalize();}void eliminate(int x){if(x>=0&&x<(int)p_.size())p_[x]=0;normalize();}void back_project(const Graph&g,int from,int to){int dr=to/g.w-from/g.w,dc=to%g.w-from%g.w;for(int x=0;x<(int)p_.size();++x)if(p_[x]>0){int vr=from/g.w-x/g.w,vc=from%g.w-x%g.w;if(vr*dr+vc*dc>0)p_[x]*=1.35;}normalize();}int top()const{return p_.empty()?-1:int(std::max_element(p_.begin(),p_.end())-p_.begin());}double entropy()const{double e=0;for(double q:p_)if(q>0)e-=q*std::log(q);return e;}private:void normalize(){double s=std::accumulate(p_.begin(),p_.end(),0.);if(s>0)for(double&q:p_)q/=s;}};
struct Candidate {int tier=5,from=-1,to=-1,kind=0;double utility=0;Reason reason=Reason::NONE;bool split=false;};
inline Candidate schedule(std::vector<Candidate> c){if(c.empty())return {};std::sort(c.begin(),c.end(),[](const Candidate&a,const Candidate&b){return std::tuple(a.tier,-a.utility,a.from,a.to)<std::tuple(b.tier,-b.utility,b.from,b.to);});return c.front();}
}
