from pathlib import Path

p = Path('competition/agents/juraj_v35_cpp/main.cpp')
s = p.read_text()
old = "bool pressure=!belief_.confirmed()&&o.turn>=300&&o.army[x]>=10&&rem>=std::max(3,o.army[y]/2);bool finish_pressure=belief_.confirmed()&&o.turn>=220&&o.army[x]>=std::max(12,o.army[y]+6);if(safe||pressure||finish_pressure)c.push_back({safe?1:2,x,y,0,double((o.army[x]-o.army[y])*10+g_.degree(y)*3+(pressure||finish_pressure?120:0)),Reason::OPPONENT_EXPLOIT,false,ActionClass::OFFENSE,y,-1,PacketRole::ATTACK});"
new = "int cover=0;for(int dz=0;dz<4;++dz){int z=g_.neighbor(y,dz);if(z>=0&&z!=x&&o.owner[z]==2)cover=std::max(cover,o.army[z]);}bool pressure=!belief_.confirmed()&&o.turn>=320&&o.army[x]>=18&&rem>=std::max(8,o.army[y]+4)&&cover*4<rem*5;bool finish_pressure=belief_.confirmed()&&o.turn>=240&&o.army[x]>=std::max(16,o.army[y]+8)&&rem>=8&&cover*4<rem*5;if(safe||pressure||finish_pressure)c.push_back({safe?1:2,x,y,0,double((o.army[x]-o.army[y])*10+g_.degree(y)*3+(pressure||finish_pressure?90:0)),Reason::OPPONENT_EXPLOIT,false,ActionClass::OFFENSE,y,-1,PacketRole::ATTACK});"
if old not in s:
    raise SystemExit('missing V4.1 pressure pattern')
p.write_text(s.replace(old, new, 1))
print('patched V4.2: radical search preserved; unsafe pressure requires large surviving stack and bounded enemy cover')
