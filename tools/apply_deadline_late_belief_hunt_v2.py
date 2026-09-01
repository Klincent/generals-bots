from pathlib import Path

p = Path('competition/agents/juraj_v35_cpp/main.cpp')
s = p.read_text()
old = "const Front*front=fronts_.primary();int sink=belief_.confirmed()?belief_.confirmed_cell():(front?front->anchor:belief_.top());int picker_sink=belief_.confirmed()?belief_.confirmed_cell():(front?front->anchor:-1);"
new = "const Front*front=fronts_.primary();int belief_target=belief_.top();bool late_belief_hunt=!belief_.confirmed()&&belief_target>=0&&!immediate&&o.turn>=850&&production_!=ProductionState::SEVERE_DEFICIT&&o.my_land+5>=o.opp_land&&(o.opp_army<=0||o.my_army>=o.opp_army+30||o.my_army*10>=std::max(1,o.opp_army)*11);int sink=belief_.confirmed()?belief_.confirmed_cell():(late_belief_hunt?belief_target:(front?front->anchor:belief_target));int picker_sink=belief_.confirmed()?belief_.confirmed_cell():(late_belief_hunt?belief_target:(front?front->anchor:-1));"
if s.count(old) != 1:
    raise SystemExit(f'sink anchor count={s.count(old)}')
s = s.replace(old, new, 1)
old2 = "else if(!enemy_seen&&b.search>0)c.push_back({3,x,y,0,double(surplus)/std::max(1,g_.dist[x][target]),Reason::SEARCH_PROGRESS,false,ActionClass::SEARCH,target,-1,PacketRole::SEARCH});"
new2 = "else if((!enemy_seen||late_belief_hunt)&&b.search>0)c.push_back({3,x,y,0,double(surplus)/std::max(1,g_.dist[x][target]),Reason::SEARCH_PROGRESS,false,ActionClass::SEARCH,target,-1,PacketRole::SEARCH});"
if s.count(old2) != 1:
    raise SystemExit(f'search gate count={s.count(old2)}')
s = s.replace(old2, new2, 1)
old3 = "!enemy_seen?.20:.08"
new3 = "!enemy_seen?.20:(late_belief_hunt?.16:.08)"
if s.count(old3) != 1:
    raise SystemExit(f'search share anchor count={s.count(old3)}')
s = s.replace(old3, new3, 1)
p.write_text(s)
print('patched late belief-driven hunt after turn 850 with material advantage')
