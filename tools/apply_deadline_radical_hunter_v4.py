from pathlib import Path

p = Path('competition/agents/juraj_v35_cpp/main.cpp')
s = p.read_text()

repls = [
(
"else if(safe_attack(o,x,y))c.push_back({1,x,y,0,double((o.army[x]-o.army[y])*10+g_.degree(y)*3),Reason::OPPONENT_EXPLOIT,false,ActionClass::OFFENSE,y,-1,PacketRole::ATTACK});",
"else if(o.owner[y]==2&&o.army[x]-1>o.army[y]){int rem=o.army[x]-1-o.army[y];bool safe=safe_attack(o,x,y);bool pressure=!belief_.confirmed()&&o.turn>=300&&o.army[x]>=10&&rem>=std::max(3,o.army[y]/2);bool finish_pressure=belief_.confirmed()&&o.turn>=220&&o.army[x]>=std::max(12,o.army[y]+6);if(safe||pressure||finish_pressure)c.push_back({safe?1:2,x,y,0,double((o.army[x]-o.army[y])*10+g_.degree(y)*3+(pressure||finish_pressure?120:0)),Reason::OPPONENT_EXPLOIT,false,ActionClass::OFFENSE,y,-1,PacketRole::ATTACK});}"
),
(
"int enemy_general=belief_.confirmed()?belief_.confirmed_cell():-1;bool late_muster=picker_enabled_&&enemy_general>=0&&!immediate&&!late_castle_pending&&o.turn>=300&&production_!=ProductionState::SEVERE_DEFICIT&&(o.opp_army<=0||o.my_army>=o.opp_army+80||o.my_army*5>=o.opp_army*6);",
"int enemy_general=belief_.confirmed()?belief_.confirmed_cell():-1;bool late_muster=picker_enabled_&&enemy_general>=0&&!immediate&&!late_castle_pending&&o.turn>=220&&production_!=ProductionState::SEVERE_DEFICIT&&(o.opp_army<=0||o.my_army>=o.opp_army+35||o.my_army*10>=o.opp_army*9||o.my_land>=o.opp_land+8);"
),
(
"int eg_army=(enemy_general>=0&&o.owner[enemy_general]==2)?o.army[enemy_general]:0;int launch_need=std::max({90,eg_army*3+20,std::max(0,o.opp_army/2)});bool late_finish=o.turn>=900&&o.army[anchor]>=std::max(70,eg_army*2+15);",
"int eg_army=(enemy_general>=0&&o.owner[enemy_general]==2)?o.army[enemy_general]:0;int launch_need=std::max({65,eg_army*2+12,std::max(0,o.opp_army*2/5)});bool late_finish=o.turn>=650&&o.army[anchor]>=std::max(48,eg_army*3/2+12);"
),
(
"else if(!enemy_seen&&b.search>0)c.push_back({3,x,y,0,double(surplus)/std::max(1,g_.dist[x][target]),Reason::SEARCH_PROGRESS,false,ActionClass::SEARCH,target,-1,PacketRole::SEARCH});",
"else if(!belief_.confirmed()&&b.search>0)c.push_back({2,x,y,0,80.+double(surplus)*4./std::max(1,g_.dist[x][target]),Reason::SEARCH_PROGRESS,false,ActionClass::SEARCH,target,-1,PacketRole::SEARCH});"
),
(
"std::array<double,5>share{{0,confirmed_war?.30:.12,production_==ProductionState::SEVERE_DEFICIT?.62:production_==ProductionState::SOFT_DEFICIT?.45:.35,!enemy_seen?.20:.08,confirmed_war?.22:.15}};",
"std::array<double,5>share{{0,confirmed_war?.38:.18,production_==ProductionState::SEVERE_DEFICIT?.62:production_==ProductionState::SOFT_DEFICIT?.45:.30,!belief_.confirmed()?.34:.05,confirmed_war?.16:.14}};"
),
]

for old, new in repls:
    if old not in s:
        raise SystemExit('missing expected V3 pattern: ' + old[:100])
    s = s.replace(old, new, 1)

needle = "  if(late_muster&&!picker_.active){"
insert = """  int fog_hunt_target=!belief_.confirmed()?belief_.top():-1;bool radical_fog_hunt=fog_hunt_target>=0&&!immediate&&!late_castle_pending&&production_!=ProductionState::SEVERE_DEFICIT&&o.turn>=220&&(enemy_seen||o.turn>=420);\n  if(radical_fog_hunt){std::vector<Candidate>hunt;for(int x=0;x<n_;++x)if(source(o,x)&&x!=general_&&o.type[x]!=3&&x!=castles_.c1&&x!=castles_.c2&&(!picker_.active||x!=picker_.cell)&&reserve(o,x)==1){int surplus=o.army[x]-1;if(surplus<5)continue;int y=tactical_next(o,x,fog_hunt_target);if(y<0)continue;double u=3600.+surplus*25.-g_.dist[x][fog_hunt_target]*6.;hunt.push_back({2,x,y,0,u,Reason::SEARCH_PROGRESS,false,ActionClass::SEARCH,fog_hunt_target,-1,PacketRole::SEARCH});}if(!hunt.empty())c.push_back(schedule(hunt));}\n"""
if needle not in s:
    raise SystemExit('missing late_muster insertion point')
s = s.replace(needle, insert + needle, 1)

p.write_text(s)
print('patched V4 radical hunter: post-contact search, fog hunt, pressure attacks, earlier muster; production/castles/picker preserved')
