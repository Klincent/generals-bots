from pathlib import Path

p = Path('competition/agents/juraj_v35_cpp/main.cpp')
s = p.read_text()
old = "int enemy_general=belief_.confirmed()?belief_.confirmed_cell():-1;bool late_muster=picker_enabled_&&enemy_general>=0&&!immediate&&!late_castle_pending&&o.turn>=300&&production_!=ProductionState::SEVERE_DEFICIT&&(o.opp_army<=0||o.my_army>=o.opp_army+80||o.my_army*5>=o.opp_army*6);"
new = "int enemy_general=belief_.confirmed()?belief_.confirmed_cell():-1;bool late_muster_adv=(o.opp_army<=0||o.my_army>=o.opp_army+80||o.my_army*5>=o.opp_army*6||(o.turn>=700&&o.my_army*10>=std::max(1,o.opp_army)*9));bool late_muster=picker_enabled_&&enemy_general>=0&&!immediate&&!late_castle_pending&&o.turn>=300&&production_!=ProductionState::SEVERE_DEFICIT&&late_muster_adv;"
if s.count(old) != 1:
    raise SystemExit(f'late_muster anchor count={s.count(old)}')
s = s.replace(old, new, 1)
old2 = "int eg_army=(enemy_general>=0&&o.owner[enemy_general]==2)?o.army[enemy_general]:0;int launch_need=std::max({90,eg_army*3+20,std::max(0,o.opp_army/2)});bool late_finish=o.turn>=900&&o.army[anchor]>=std::max(70,eg_army*2+15);bool ready=o.army[anchor]>=launch_need||late_finish||donor_count<=2||donor_mass<20;"
new2 = "int eg_army=(enemy_general>=0&&o.owner[enemy_general]==2)?o.army[enemy_general]:0;int launch_need=o.turn>=1050?std::max({35,eg_army+10,std::max(0,o.opp_army/6)}):o.turn>=900?std::max({50,eg_army*2+10,std::max(0,o.opp_army/4)}):o.turn>=700?std::max({70,eg_army*2+15,std::max(0,o.opp_army/3)}):std::max({90,eg_army*3+20,std::max(0,o.opp_army/2)});bool late_finish=o.turn>=900&&o.army[anchor]>=std::max(55,eg_army*2+10);bool ready=o.army[anchor]>=launch_need||late_finish||donor_count<=2||donor_mass<20;"
if s.count(old2) != 1:
    raise SystemExit(f'launch anchor count={s.count(old2)}')
s = s.replace(old2, new2, 1)
p.write_text(s)
print('patched progressive confirmed-general finisher thresholds')
