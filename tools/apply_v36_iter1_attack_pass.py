#!/usr/bin/env python3
from pathlib import Path

root = Path(__file__).resolve().parents[1]
main = root / 'competition/agents/juraj_v35_cpp/main.cpp'
test = root / 'competition/agents/juraj_v35_cpp/test_agent.cpp'

def repl(path, old, new, label):
    s = path.read_text()
    if new in s:
        print(f'{label}: already applied')
        return
    if old not in s:
        raise SystemExit(f'{label}: source pattern not found')
    path.write_text(s.replace(old, new, 1))
    print(f'{label}: applied')

# Keep exploration alive after seeing ordinary enemy territory; stop only once the
# enemy general is actually confirmed. This removes a major source of late PASSes.
repl(
    main,
    'else if(!enemy_seen&&b.search>0)c.push_back({3,x,y,0,double(surplus)/std::max(1,g_.dist[x][target]),Reason::SEARCH_PROGRESS,false,ActionClass::SEARCH,target,-1,PacketRole::SEARCH});',
    'else if(!belief_.confirmed()&&b.search>0)c.push_back({3,x,y,0,double(surplus)/std::max(1,g_.dist[x][target]),Reason::SEARCH_PROGRESS,false,ActionClass::SEARCH,target,-1,PacketRole::SEARCH});',
    'search persists until general confirmation',
)

# Once the enemy general is known, generate a persistent forward OFFENSE action
# from every surplus stack instead of waiting for a currently active front.
repl(
    main,
    'if(confirmed_war&&b.war>0)c.push_back({2,x,y,0,double(surplus)/std::max(1,g_.dist[x][target]),Reason::WAR_MOBILIZATION,false,ActionClass::LOGISTICS,target,front?front->id:-1,PacketRole::FRONT});else if(rear&&b.free+b.search>0)',
    'if(belief_.confirmed()&&!immediate)c.push_back({2,x,y,0,2000.+double(surplus)/std::max(1,g_.dist[x][target]),Reason::WAR_MOBILIZATION,false,ActionClass::OFFENSE,target,-1,PacketRole::ATTACK});else if(confirmed_war&&b.war>0)c.push_back({2,x,y,0,double(surplus)/std::max(1,g_.dist[x][target]),Reason::WAR_MOBILIZATION,false,ActionClass::LOGISTICS,target,front?front->id:-1,PacketRole::FRONT});else if(rear&&b.free+b.search>0)',
    'persistent confirmed-general attack',
)

# Give offense enough scheduler share to make a confirmed-general route persistent,
# without changing budgets or declaring a fake active front.
repl(
    main,
    'std::array<double,5>share{{0,confirmed_war?.30:.12,',
    'std::array<double,5>share{{0,(confirmed_war||belief_.confirmed())?.30:.12,',
    'confirmed-general offense share',
)

# Final fallback: when no strategic candidate exists, move an owned surplus stack
# one step toward our general. This is intentionally last in the fallback order and
# therefore cannot steal expansion/search/attack/picker work.
repl(
    main,
    'std::vector<Candidate>enemy,neutral,persistent,rear,consolidate,explore;bool movable=false,legal=false,safe=false,blocked=false;',
    'std::vector<Candidate>enemy,neutral,persistent,rear,consolidate,explore,centralize;bool movable=false,legal=false,safe=false,blocked=false;',
    'fallback centralize bucket',
)
repl(
    main,
    'else if(o.army[y]>o.army[x]&&g_.degree(y)>=g_.degree(x)){q.utility=o.army[y]-o.army[x];consolidate.push_back(q);}}else if(o.owner[y]<0)',
    'else if(o.army[y]>o.army[x]&&g_.degree(y)>=g_.degree(x)){q.utility=o.army[y]-o.army[x];consolidate.push_back(q);}else if(general_>=0&&x!=general_&&g_.dist[y][general_]<g_.dist[x][general_]){q.utility=50.+o.army[x]-g_.dist[y][general_];q.target=general_;q.reason=Reason::REAR_EVACUATION;q.role=PacketRole::FREE_SURPLUS_RELOCATION;centralize.push_back(q);}}else if(o.owner[y]<0)',
    'fallback centralize candidate',
)
repl(
    main,
    'for(auto*v:{&enemy,&neutral,&persistent,&rear,&consolidate,&explore})if(!v->empty())',
    'for(auto*v:{&enemy,&neutral,&persistent,&rear,&consolidate,&explore,&centralize})if(!v->empty())',
    'fallback centralize priority',
)

# Regression: exact enemy-general knowledge must immediately create forward progress.
old = ' // Confirmed general remains exact despite later fog.\n {Agent a(0,21,21);auto o=board();o.type[230]=4;o.owner[230]=2;o.army[230]=3;o.owner[229]=1;o.army[229]=1;a.decide(o);assert(a.enemy_general_confirmed()&&a.enemy_general_cell()==230);o.turn++;o.type[230]=-1;o.owner[230]=-1;a.decide(o);assert(a.enemy_general_cell()==230);}\n std::cout<<"v35 agent recovery scenarios passed\\n";'
new = ' // Confirmed general remains exact despite later fog.\n {Agent a(0,21,21);auto o=board();o.type[230]=4;o.owner[230]=2;o.army[230]=3;o.owner[229]=1;o.army[229]=1;a.decide(o);assert(a.enemy_general_confirmed()&&a.enemy_general_cell()==230);o.turn++;o.type[230]=-1;o.owner[230]=-1;a.decide(o);assert(a.enemy_general_cell()==230);}\n // Confirmed general creates deterministic forward pressure even without a live front.\n {Agent a(0,21,21);auto o=board();for(int x=0;x<441;++x)if(x!=220){o.owner[x]=1;o.army[x]=1;}o.type[230]=4;o.owner[230]=2;o.army[230]=3;o.army[220]=20;o.my_land=440;o.my_army=459;o.opp_land=1;o.opp_army=3;auto q=a.decide(o);assert(q.kind==0);int s=src(q),d=dst(q);auto md=[](int x){return std::abs(x/21-230/21)+std::abs(x%21-230%21);};assert(md(d)<md(s));}\n std::cout<<"v35 agent recovery scenarios passed\\n";'
repl(test, old, new, 'confirmed-general forward-progress regression')

print('V3.6 iter1 attack/pass patch complete')
