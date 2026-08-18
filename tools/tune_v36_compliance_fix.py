#!/usr/bin/env python3
# Runtime tuning layered after the compliance patch; also aligns lifecycle tests.
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
for rel in ('competition/agents/juraj_v35_cpp/test_picker.cpp','competition/agents/juraj_v35_cpp/test_picker_economics.cpp'):
    p=root/rel; t=p.read_text()
    if 'o.turn=120' in t:
        p.write_text(t.replace('o.turn=120','o.turn=100',1)); print(rel+': test turn 100 applied')
    elif 'o.turn=100' in t: print(rel+': test turn 100 already applied')
    else: raise SystemExit(rel+': test turn pattern not found')
print('compliance tuning complete')
