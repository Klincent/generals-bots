from pathlib import Path

p = Path('competition/agents/juraj_v35_cpp/main.cpp')
s = p.read_text()
old = "int enemy_general=belief_.confirmed()?belief_.confirmed_cell():-1;bool late_muster=picker_enabled_&&enemy_general>=0&&!immediate&&!late_castle_pending&&o.turn>=300&&production_!=ProductionState::SEVERE_DEFICIT&&(o.opp_army<=0||o.my_army>=o.opp_army+80||o.my_army*5>=o.opp_army*6);"
new = old + "\n  int late_hunt_target=belief_.confirmed()?-1:belief_.top();bool late_scout=late_hunt_target>=0&&o.turn>=600&&!immediate&&!confirmed_war&&!late_castle_pending&&production_!=ProductionState::SEVERE_DEFICIT&&o.my_land+5>=o.opp_land&&o.my_army*10>=std::max(1,o.opp_army)*9;\n  if(late_scout){for(int x=0;x<n_;++x)if(source(o,x)&&x!=general_&&o.type[x]!=3&&x!=castles_.c1&&x!=castles_.c2&&reserve(o,x)==1&&o.army[x]>=6&&o.army[x]<=40){int y=tactical_next(o,x,late_hunt_target);if(y>=0&&o.owner[y]!=2){double u=2200.-std::abs(o.army[x]-12)*8.-g_.dist[x][late_hunt_target];c.push_back({3,x,y,0,u,Reason::SEARCH_PROGRESS,false,ActionClass::SEARCH,late_hunt_target,-1,PacketRole::SEARCH});}}}"
if s.count(old) != 1:
    raise SystemExit(f'late_muster anchor count={s.count(old)}')
s = s.replace(old, new, 1)
old_share = '!enemy_seen?.20:.08'
new_share = '!enemy_seen?.20:(late_scout?.18:.08)'
if s.count(old_share) != 1:
    raise SystemExit(f'search share anchor count={s.count(old_share)}')
s = s.replace(old_share, new_share, 1)
p.write_text(s)
print('patched conservative late fog scouting toward belief top after turn 600')
