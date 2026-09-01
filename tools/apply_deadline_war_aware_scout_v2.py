from pathlib import Path

p = Path('competition/agents/juraj_v35_cpp/main.cpp')
s = p.read_text()
old = "int enemy_general=belief_.confirmed()?belief_.confirmed_cell():-1;bool late_muster=picker_enabled_&&enemy_general>=0&&!immediate&&!late_castle_pending&&o.turn>=300&&production_!=ProductionState::SEVERE_DEFICIT&&(o.opp_army<=0||o.my_army>=o.opp_army+80||o.my_army*5>=o.opp_army*6);"
new = old + "\n  int war_scout_target=belief_.confirmed()?-1:belief_.top();bool war_aware_scout=war_scout_target>=0&&o.turn>=650&&!immediate&&!late_castle_pending&&production_!=ProductionState::SEVERE_DEFICIT&&o.my_land+10>=o.opp_land&&(o.opp_army<=0||o.my_army*10>=std::max(1,o.opp_army)*9);\n  if(war_aware_scout){std::vector<Candidate>scouts;for(int x=0;x<n_;++x)if(source(o,x)&&x!=general_&&o.type[x]!=3&&x!=castles_.c1&&x!=castles_.c2&&reserve(o,x)==1&&o.army[x]>=8&&o.army[x]<=60){int y=tactical_next(o,x,war_scout_target);if(y>=0&&o.owner[y]!=2&&g_.dist[y][war_scout_target]<g_.dist[x][war_scout_target]){double u=3200.+o.army[x]*6.-g_.dist[x][war_scout_target]*3.;scouts.push_back({2,x,y,0,u,Reason::SEARCH_PROGRESS,false,ActionClass::SEARCH,war_scout_target,-1,PacketRole::SEARCH});}}if(!scouts.empty())c.push_back(schedule(scouts));}"
if s.count(old) != 1:
    raise SystemExit(f'late_muster anchor count={s.count(old)}')
s = s.replace(old, new, 1)
old_share = '!enemy_seen?.20:.08'
new_share = '!enemy_seen?.20:(war_aware_scout?.22:.08)'
if s.count(old_share) != 1:
    raise SystemExit(f'search share anchor count={s.count(old_share)}')
s = s.replace(old_share, new_share, 1)
p.write_text(s)
print('patched war-aware scouting toward belief top even with active fronts')
