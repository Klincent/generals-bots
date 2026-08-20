from pathlib import Path

p=Path('competition/agents/juraj_v35_cpp/main.cpp')
s=p.read_text()
old="int doom_floor=std::max(18,std::max(1,o.opp_army)*15/100);bool doom_regular=largest>=0&&o.type[largest]!=3&&o.type[largest]!=4;bool doom_now=doomguard_enabled_&&doom_regular&&doom_eta_now<=12&&largest_army>=doom_floor&&own_peak*100<std::max(1,o.my_army)*45&&(moved_enemy(o,largest)||doom_eta_now<=8);"
new="int doom_floor=std::max(18,std::max(1,o.opp_army)*(doom_eta_now<=6?15:25)/100);bool doom_regular=largest>=0&&o.type[largest]!=3&&o.type[largest]!=4;bool doom_now=doomguard_enabled_&&doom_regular&&doom_eta_now<=12&&largest_army>=doom_floor&&own_peak*100<std::max(1,o.my_army)*45&&(moved_enemy(o,largest)||doom_eta_now<=8);"
if old not in s:
    raise SystemExit('expected DoomGuard condition not found')
s=s.replace(old,new,1)
old2="bool late_muster=picker_enabled_&&enemy_general>=0&&!immediate&&!late_castle_pending&&o.turn>=300&&production_!=ProductionState::SEVERE_DEFICIT&&(o.opp_army<=0||o.my_army>=o.opp_army+80||o.my_army*5>=o.opp_army*6);"
new2="bool late_muster=picker_enabled_&&enemy_general>=0&&!immediate&&!late_castle_pending&&o.turn>=300&&production_!=ProductionState::SEVERE_DEFICIT&&(o.turn>=1000||o.opp_army<=0||o.my_army>=o.opp_army+80||o.my_army*5>=o.opp_army*6);"
if old2 not in s:
    raise SystemExit('expected late muster condition not found')
s=s.replace(old2,new2,1)
p.write_text(s)
print('applied DoomGuard concentration gate plus late draw-breaker muster at turn >=1000')
