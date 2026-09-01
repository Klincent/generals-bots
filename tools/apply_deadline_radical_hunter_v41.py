from pathlib import Path

p = Path('competition/agents/juraj_v35_cpp/main.cpp')
s = p.read_text()
old = "bool ready=o.army[anchor]>=launch_need||late_finish||donor_count<=2||donor_mass<20;"
new = "bool ready=late_finish||donor_count<=2||donor_mass<20||(o.turn>=650&&o.army[anchor]>=launch_need);"
if old not in s:
    raise SystemExit('missing V4 ready pattern')
p.write_text(s.replace(old, new, 1))
print('patched V4.1: early muster harvests donors before launch; radical search/pressure unchanged')
