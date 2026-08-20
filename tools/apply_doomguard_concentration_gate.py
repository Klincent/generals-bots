from pathlib import Path

p=Path('competition/agents/juraj_v35_cpp/main.cpp')
s=p.read_text()
old="int doom_floor=std::max(18,std::max(1,o.opp_army)*15/100);bool doom_regular=largest>=0&&o.type[largest]!=3&&o.type[largest]!=4;bool doom_now=doomguard_enabled_&&doom_regular&&doom_eta_now<=12&&largest_army>=doom_floor&&own_peak*100<std::max(1,o.my_army)*45&&(moved_enemy(o,largest)||doom_eta_now<=8);"
new="int doom_floor=std::max(18,std::max(1,o.opp_army)*(doom_eta_now<=6?15:25)/100);bool doom_regular=largest>=0&&o.type[largest]!=3&&o.type[largest]!=4;bool doom_now=doomguard_enabled_&&doom_regular&&doom_eta_now<=12&&largest_army>=doom_floor&&own_peak*100<std::max(1,o.my_army)*45&&(moved_enemy(o,largest)||doom_eta_now<=8);"
if old not in s:
    raise SystemExit('expected DoomGuard condition not found')
s=s.replace(old,new,1)
old2="int launch_need=std::max({90,eg_army*3+20,std::max(0,o.opp_army/2)});bool ready=o.army[anchor]>=launch_need||donor_count<=2||donor_mass<20;"
new2="int launch_need=std::max({90,eg_army*3+20,std::max(0,o.opp_army/2)});bool late_finish=o.turn>=900&&o.army[anchor]>=std::max(70,eg_army*2+15);bool ready=o.army[anchor]>=launch_need||late_finish||donor_count<=2||donor_mass<20;"
if old2 not in s:
    raise SystemExit('expected late muster launch condition not found')
s=s.replace(old2,new2,1)
p.write_text(s)
print('applied DoomGuard concentration gate plus turn>=900 late-finisher launch threshold')
