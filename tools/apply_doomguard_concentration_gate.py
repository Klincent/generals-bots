from pathlib import Path

p=Path('competition/agents/juraj_v35_cpp/main.cpp')
s=p.read_text()
old="int doom_floor=std::max(18,std::max(1,o.opp_army)*15/100);bool doom_regular=largest>=0&&o.type[largest]!=3&&o.type[largest]!=4;bool doom_now=doomguard_enabled_&&doom_regular&&doom_eta_now<=12&&largest_army>=doom_floor&&own_peak*100<std::max(1,o.my_army)*45&&(moved_enemy(o,largest)||doom_eta_now<=8);"
new="int doom_floor=std::max(18,std::max(1,o.opp_army)*(doom_eta_now<=6?15:25)/100);bool doom_regular=largest>=0&&o.type[largest]!=3&&o.type[largest]!=4;bool doom_now=doomguard_enabled_&&doom_regular&&doom_eta_now<=12&&largest_army>=doom_floor&&own_peak*100<std::max(1,o.my_army)*45&&(moved_enemy(o,largest)||doom_eta_now<=8);"
if old not in s:
    raise SystemExit('expected DoomGuard condition not found')
p.write_text(s.replace(old,new,1))
print('applied DoomGuard concentration gate: 25% beyond ETA6, 15% at ETA<=6')
