#!/usr/bin/env python3
from pathlib import Path
p=Path(__file__).with_name('main.cpp')
s=p.read_text()
if 'picker_gate_mode_==3' in s:
    print('picker v5 already applied')
    raise SystemExit(0)
def rep(old,new):
    global s
    if old not in s:
        raise SystemExit('missing patch anchor: '+old[:180])
    s=s.replace(old,new,1)
rep('if(v>=0&&v<=2)picker_gate_mode_=v;', 'if(v>=0&&v<=3)picker_gate_mode_=v;')
anchor='bool useful_sink=picker_sink>=0;bool allowed=mature&&not_behind&&growing&&few_neutrals&&needs_concentration&&meaningful_mass&&economy_ok;'
replacement='bool useful_sink=picker_sink>=0;if(mode==3){mature=o.turn>=280||o.my_land*100>=n_*30;not_behind=o.opp_land==0||(o.my_land+25>=o.opp_land&&o.my_land<=o.opp_land+10);growing=growth25>=.12;few_neutrals=useful_neutrals<=80;needs_concentration=top3_share<.15&&largest_owned<best_mass;meaningful_mass=best_mass>=std::max(16,o.my_army/32);economy_ok=production_!=ProductionState::SEVERE_DEFICIT&&!f1.must_fund&&!f2.must_fund;}bool allowed=mature&&not_behind&&growing&&few_neutrals&&needs_concentration&&meaningful_mass&&economy_ok;'
rep(anchor,replacement)
rep('picker_cooldown_until_=std::max(picker_cooldown_until_,o.turn+(picker_gate_mode_==0?120:picker_gate_mode_==1?90:70));', 'picker_cooldown_until_=std::max(picker_cooldown_until_,o.turn+(picker_gate_mode_==0?120:picker_gate_mode_==1?90:picker_gate_mode_==2?70:110));')
p.write_text(s)
print('picker v5 momentum gate applied')
