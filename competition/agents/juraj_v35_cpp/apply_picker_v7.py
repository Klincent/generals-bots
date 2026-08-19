#!/usr/bin/env python3
from pathlib import Path
p=Path(__file__).with_name('main.cpp')
s=p.read_text()
if 'picker_gate_mode_==5' in s:
    print('picker v7 already applied')
    raise SystemExit(0)
def rep(old,new):
    global s
    if old not in s: raise SystemExit('missing patch anchor: '+old[:180])
    s=s.replace(old,new,1)
rep('if(v>=0&&v<=3)picker_gate_mode_=v;', 'if(v>=0&&v<=5)picker_gate_mode_=v;')
anchor='if(mode==3){mature=o.turn>=280||o.my_land*100>=n_*30;not_behind=o.opp_land==0||(o.my_land+25>=o.opp_land&&o.my_land<=o.opp_land+10);growing=growth25>=.12;few_neutrals=useful_neutrals<=80;needs_concentration=top3_share<.15&&largest_owned<best_mass;meaningful_mass=best_mass>=std::max(16,o.my_army/32);economy_ok=production_!=ProductionState::SEVERE_DEFICIT&&!f1.must_fund&&!f2.must_fund;}bool allowed='
replacement='if(mode==3){mature=o.turn>=280||o.my_land*100>=n_*30;not_behind=o.opp_land==0||(o.my_land+25>=o.opp_land&&o.my_land<=o.opp_land+10);growing=growth25>=.12;few_neutrals=useful_neutrals<=80;needs_concentration=top3_share<.15&&largest_owned<best_mass;meaningful_mass=best_mass>=std::max(16,o.my_army/32);economy_ok=production_!=ProductionState::SEVERE_DEFICIT&&!f1.must_fund&&!f2.must_fund;}if(mode==5){mature=o.turn>=700;not_behind=o.opp_land>0&&o.my_land+30>=o.opp_land&&o.my_land<=o.opp_land;growing=growth25>=.12;few_neutrals=useful_neutrals<=80;needs_concentration=top3_share<.12&&largest_owned<best_mass;meaningful_mass=best_mass>=std::max(30,o.my_army/24);economy_ok=production_!=ProductionState::SEVERE_DEFICIT&&!f1.must_fund&&!f2.must_fund&&meaningful&&fronts_.active_count()>=8&&picker_sink>=0;}bool allowed='
rep(anchor,replacement)
rep('picker_gate_mode_==2?70:110', 'picker_gate_mode_==2?70:picker_gate_mode_==3?110:150')
p.write_text(s)
print('late comeback picker v7 applied')
