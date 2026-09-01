from pathlib import Path

p = Path('competition/agents/juraj_v35_cpp/main.cpp')
s = p.read_text()
repls = [
    (
        'else if(f.must_fund)for(int x=0;x<n_;++x)if(source(o,x)){',
        'else if(f.must_fund&&!confirmed_war)for(int x=0;x<n_;++x)if(source(o,x)){',
    ),
    (
        'else if(production_!=ProductionState::SEVERE_DEFICIT&&o.my_army>=live_castle_cost(o,site,w_)+30){',
        'else if(!confirmed_war&&production_!=ProductionState::SEVERE_DEFICIT&&o.my_army>=live_castle_cost(o,site,w_)+30){',
    ),
]
for old, new in repls:
    n = s.count(old)
    if n != 1:
        raise SystemExit(f'expected exactly one match, got {n}: {old[:80]}')
    s = s.replace(old, new, 1)
p.write_text(s)
print('patched castle funding: suppress remote funding while confirmed war is active')
