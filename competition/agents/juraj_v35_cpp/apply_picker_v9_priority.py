#!/usr/bin/env python3
from pathlib import Path
p=Path(__file__).with_name('main.cpp')
s=p.read_text()
changes=[
('harvest.push_back({2,x,y,0,5000.','harvest.push_back({1,x,y,0,5000.'),
('c.push_back({2,anchor,y,0,6500.','c.push_back({1,anchor,y,0,6500.'),
]
for old,new in changes:
    if old in s:
        s=s.replace(old,new,1)
    elif new not in s:
        raise SystemExit(f'missing expected muster priority pattern: {old}')
p.write_text(s)
print('picker-v9 priority patch applied')
