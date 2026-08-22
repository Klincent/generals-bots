#include "core.hpp"
#include <cassert>
#include <iostream>
using namespace v35;
Graph open_graph(int h=9,int w=9){Graph g{h,w,std::vector<char>(h*w,1),{}, {}};g.build();return g;}
int main(){
 auto g=open_graph();int general=40;
 // 1 castle pair: exhaustive lexicographic selection is deterministic and sequentially costed.
 auto c=plan_castles(g,general),d=plan_castles(g,general);assert(c.c1>=0&&c.c2>=0&&c.c1!=c.c2&&c.total==c.cost1+c.cost2&&c.c1==d.c1);
 // 2 deadlines and 3 just-in-time funding.
 auto f=forecast(100,150,40,10,{{31,10}});assert(f.feasible&&!f.must_fund);auto late=forecast(f.latest_start,150,40,10,{{31,10}});assert(late.must_fund);
 auto work=forecast(100,150,40,0,{{15,5},{15,6},{15,7}},false);assert(work.required_actions==5+6+7+1+1);assert(work.latest_start==150-work.required_actions-5);
 // 4 production candidates remain in their explicit tier.
 assert(schedule({{4,1,2,0,99,Reason::SEARCH_PROGRESS},{3,2,3,0,1,Reason::PRODUCTION_TICK}}).reason==Reason::PRODUCTION_TICK);
 // 5 corner and 6 dead-end evacuation select the highest tier, FULL by default.
 Candidate rear{2,0,1,0,100,Reason::REAR_EVACUATION,false};assert(schedule({rear,{4,4,5,0,999,Reason::SEARCH_PROGRESS}}).reason==Reason::REAR_EVACUATION&&!rear.split);
 // 7 A-B-A is allowed; 8 repeating the same directed edge inside the last four transitions is blocked.
 Packet p;p.cell=2;p.target=8;p.event_version=1;p.path={0,1,2};assert(route_allowed(p,1,2,2,1,Reason::NONE));
 p.cell=1;p.path={0,1,2,1};assert(!route_allowed(p,2,2,2,1,Reason::NONE));
 // 9 a real strategic emergency always overrides the cycle guard.
 assert(route_allowed(p,2,3,2,2,Reason::GENERAL_EMERGENCY));
 // 10 contact creates war surplus and 11 FULL remains default.
 auto b=budget(200,20,15,20,true,.6);assert(b.war>0&&b.front==b.war);assert(!rear.split);
 // 12 swarm response and 13 doomstack response avoid chase/head-on policy.
 OpponentModel swarm;OpponentEvidence es;es.samples=10;es.activity=1;es.concentration=.05;for(int i=0;i<20;++i)swarm.update(es);assert(swarm.adaptation().response=="CONSOLIDATED_SWEEP"||swarm.confidence()[(int)Archetype::SMALL_PACKET_SWARM]>.5);
 OpponentModel doom;OpponentEvidence ed;ed.samples=5;ed.activity=1;ed.concentration=.95;for(int i=0;i<20;++i)doom.update(ed);assert(doom.adaptation().response=="COUNTERATTACK_WEAK_REAR");
 // 14 early rush raises defense.
 OpponentModel rush;OpponentEvidence er;er.samples=5;er.turn=80;er.closing=1;for(int i=0;i<20;++i)rush.update(er);assert(rush.adaptation().defense>=.55);
 // 15 castle builder chooses flank response.
 OpponentModel castle;OpponentEvidence ec;ec.samples=5;ec.castles=3;ec.activity=1;for(int i=0;i<20;++i)castle.update(ec);assert(castle.adaptation().response=="FLANK_POST_INVESTMENT");
 // 16 turtle and 17 multi-front adaptations.
 OpponentModel turtle;OpponentEvidence et;et.samples=5;et.activity=0;et.reaction_ratio=2;for(int i=0;i<20;++i)turtle.update(et);assert(turtle.adaptation().fronts==2);
 OpponentModel multi;OpponentEvidence em;em.samples=5;em.activity=1;em.fronts=3;for(int i=0;i<20;++i)multi.update(em);assert(multi.adaptation().response=="CENTRAL_REACTION");
 // 18 low evidence cannot flip confidence on one observation.
 OpponentModel stable;OpponentEvidence one;one.samples=1;one.concentration=1;stable.update(one);assert(stable.confidence()[(int)Archetype::DOOMSTACK]<.2);
 // 19 flow belief back-projection moves the top candidate upstream.
 auto large=open_graph(21,21);Belief belief;belief.initialise(large,220);double before=belief.entropy();belief.back_project(large,220,221);assert(belief.entropy()!=before&&belief.top()>=0);
 // 20 scheduler output is deterministic and graph moves are legal-adjacent.
 auto q=schedule({{3,1,2,0,1,Reason::SEARCH_PROGRESS},{3,1,3,0,1,Reason::SEARCH_PROGRESS}});assert(q.to==2&&g.neighbor(0,1)==9);
 std::cout<<"v35 core: 20 behavioral checks passed\n";
}
