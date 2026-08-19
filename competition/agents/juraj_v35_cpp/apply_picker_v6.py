#!/usr/bin/env python3
from pathlib import Path
p=Path(__file__).with_name('main.cpp')
s=p.read_text()
if 'picker_gate_mode_==4' in s:
    print('picker v6 already applied')
    raise SystemExit(0)
def rep(old,new):
    global s
    if old not in s:
        raise SystemExit('missing patch anchor: '+old[:180])
    s=s.replace(old,new,1)
rep('struct EdgePickerState {bool active=false;int wall=-1,cell=-1,dir=0,phase=0,wall_goal=-1,start_turn=-1,start_army=0,blocked_turns=0,moves_used=0;};','struct EdgePickerState {bool active=false;int wall=-1,cell=-1,dir=0,phase=0,wall_goal=-1,sink=-1,start_turn=-1,start_army=0,blocked_turns=0,moves_used=0;};')
rep('if(v>=0&&v<=3)picker_gate_mode_=v;', 'if(v>=0&&v<=4)picker_gate_mode_=v;')
old='int owned_next_to_general(const Observation&o,int from)const{if(from<0||general_<0||from==general_)return -1;int stack=std::max(2,o.army[from]);auto search=[&](bool avoid_structures){std::vector<int>d(n_,-1);std::queue<int>q;d[general_]=0;q.push(general_);while(!q.empty()){int x=q.front();q.pop();for(int k=0;k<4;++k){int y=g_.neighbor(x,k);if(y<0||d[y]>=0||o.owner[y]!=1||!g_.passable[y])continue;if(y!=from&&y!=general_){if(avoid_structures&&(o.type[y]==3||y==castles_.c1||y==castles_.c2))continue;if(!picker_route_safe(o,y,stack))continue;}d[y]=d[x]+1;q.push(y);}}int best=-1,bd=INF;for(int k=0;k<4;++k){int y=g_.neighbor(from,k);if(y>=0&&d[y]>=0&&picker_route_safe(o,y,stack)&&d[y]<bd){best=y;bd=d[y];}}return best;};int y=search(true);return y>=0?y:search(false);}'
new=old+'\n int owned_next_to_target(const Observation&o,int from,int target)const{if(from<0||target<0||target>=n_)return -1;int stack=std::max(2,o.army[from]),best=-1,bd=g_.dist[from][target],be=-1,bdeg=-1;for(int k=0;k<4;++k){int y=g_.neighbor(from,k);if(y<0||o.owner[y]!=1||!g_.passable[y]||!picker_route_safe(o,y,stack))continue;if(o.type[y]==3||y==castles_.c1||y==castles_.c2)continue;int dd=g_.dist[y][target],edge=edge_depth(y),deg=g_.degree(y);if(dd<bd&&(best<0||std::tuple(dd,-edge,-deg,y)<std::tuple(g_.dist[best][target],-be,-bdeg,best))){best=y;be=edge;bdeg=deg;}}return best;}'
rep(old,new)
rep('for(int wall=0;wall<4;++wall)if(wall_irrelevant(wall,picker_sink)){int proj=(wall==0||wall==2)?general_%w_:general_/w_,limit=(wall==0||wall==2)?w_:h_;', 'for(int wall=0;wall<4;++wall)if(wall_irrelevant(wall,picker_sink)){int target_proj=picker_sink>=0?picker_sink:general_,proj=(wall==0||wall==2)?target_proj%w_:target_proj/w_,limit=(wall==0||wall==2)?w_:h_;')
anchor='if(mode==3){mature=o.turn>=280||o.my_land*100>=n_*30;not_behind=o.opp_land==0||(o.my_land+25>=o.opp_land&&o.my_land<=o.opp_land+10);growing=growth25>=.12;few_neutrals=useful_neutrals<=80;needs_concentration=top3_share<.15&&largest_owned<best_mass;meaningful_mass=best_mass>=std::max(16,o.my_army/32);economy_ok=production_!=ProductionState::SEVERE_DEFICIT&&!f1.must_fund&&!f2.must_fund;}bool allowed='
replacement='if(mode==3){mature=o.turn>=280||o.my_land*100>=n_*30;not_behind=o.opp_land==0||(o.my_land+25>=o.opp_land&&o.my_land<=o.opp_land+10);growing=growth25>=.12;few_neutrals=useful_neutrals<=80;needs_concentration=top3_share<.15&&largest_owned<best_mass;meaningful_mass=best_mass>=std::max(16,o.my_army/32);economy_ok=production_!=ProductionState::SEVERE_DEFICIT&&!f1.must_fund&&!f2.must_fund;}if(mode==4){mature=o.turn>=300;not_behind=o.opp_land==0||(o.my_land+20>=o.opp_land&&o.my_land<=o.opp_land);growing=growth25>=.12;few_neutrals=useful_neutrals<=80;needs_concentration=top3_share<.15&&largest_owned<best_mass;meaningful_mass=best_mass>=std::max(24,o.my_army/28);economy_ok=production_!=ProductionState::SEVERE_DEFICIT&&!f1.must_fund&&!f2.must_fund&&meaningful&&fronts_.active_count()>=8&&picker_sink>=0;}bool allowed='
rep(anchor,replacement)
rep('picker_={true,best_wall,best_start,best_dir,0,best_goal,o.turn,o.army[best_start],0,0};','picker_={true,best_wall,best_start,best_dir,0,best_goal,picker_sink,o.turn,o.army[best_start],0,0};')
rep('if(picker_.phase==1)y=owned_next_to_general(o,x);', 'if(picker_.phase==1)y=picker_gate_mode_==4?owned_next_to_target(o,x,picker_.sink):owned_next_to_general(o,x);')
rep('Reason::EDGE_PICKER,false,ActionClass::LOGISTICS,general_,-1,PacketRole::EDGE_PICKER', 'Reason::EDGE_PICKER,false,ActionClass::LOGISTICS,(picker_gate_mode_==4&&picker_.sink>=0)?picker_.sink:general_,-1,PacketRole::EDGE_PICKER')
rep('bool handoff=edge_depth(q.to)>=3||picker_.moves_used>=8;', 'bool handoff=edge_depth(q.to)>=3||(picker_gate_mode_==4&&picker_.sink>=0&&g_.dist[q.to][picker_.sink]<=4)||picker_.moves_used>=(picker_gate_mode_==4?6:8);')
rep('picker_gate_mode_==2?70:110', 'picker_gate_mode_==2?70:picker_gate_mode_==3?110:150')
p.write_text(s)
print('pressure-fed picker v6 applied')
