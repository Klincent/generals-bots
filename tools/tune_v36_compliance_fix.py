#!/usr/bin/env python3
from pathlib import Path
root=Path(__file__).resolve().parents[1]
core=root/'competition/agents/juraj_v35_cpp/core.hpp'
s=core.read_text()
old='return turn>=120&&turn>=cooldown_until&&land>=12&&(general_confirmed||contacted||touched>=need);'
new='return turn>=80&&turn>=cooldown_until&&land>=12&&(general_confirmed||contacted||touched>=need);'
if old in s:
    core.write_text(s.replace(old,new,1)); print('picker earliest turn 80: applied')
elif new in s: print('picker earliest turn 80: already applied')
else: raise SystemExit('picker start helper pattern not found')
print('compliance tuning complete')
