#!/usr/bin/env python3
from pathlib import Path

p = Path(__file__).with_name('main.cpp')
s = p.read_text()

def rep(old, new, label):
    global s
    n = s.count(old)
    if n != 1:
        raise SystemExit(f'{label}: expected exactly one match, found {n}')
    s = s.replace(old, new, 1)

rep(
" long picker_eligible_=0,picker_piggyback_moves_=0,picker_reject_economy_=0,picker_reject_behind_=0,picker_reject_growth_=0,picker_reject_neutrals_=0,picker_reject_concentration_=0,picker_reject_sink_=0;std::array<long,32>picker_gate_masks_{};",
" long picker_eligible_=0,picker_piggyback_moves_=0,picker_reject_economy_=0,picker_reject_behind_=0,picker_reject_growth_=0,picker_reject_neutrals_=0,picker_reject_concentration_=0,picker_reject_sink_=0;std::array<long,32>picker_gate_masks_{};int muster_threshold_=8;long muster_moves_=0,muster_harvest_moves_=0,muster_attack_moves_=0,muster_windows_=0,late_castle_fund_moves_=0;",
"fields")

rep(
"if(const char*e=std::getenv(\"V36_EDGE_PICKER_MIN_EFFICIENCY\")){double v=std::atof(e);if(v>=0.0&&v<=20.0)edge_picker_min_efficiency_=v;}std::fprintf",
"if(const char*e=std::getenv(\"V36_EDGE_PICKER_MIN_EFFICIENCY\")){double v=std::atof(e);if(v>=0.0&&v<=20.0)edge_picker_min_efficiency_=v;}if(const char*e=std::getenv(\"V35_MUSTER_THRESHOLD\")){int v=std::atoi(e);if(v>=4&&v<=50)muster_threshold_=v;}std::fprintf",
"init env")

needle = " int owned_next_to_general(const Observation&o,int from)const{if(from<0||general_<0||from==general_)return -1;int stack=std::max(2,o.army[from]);auto search=[&](bool avoid_structures){std::vector<int>d(n_,-1);std::queue<int>q;d[general_]=0;q.push(general_);while(!q.empty()){int x=q.front();q.pop();for(int k=0;k<4;++k){int y=g_.neighbor(x,k);if(y<0||d[y]>=0||o.owner[y]!=1||!g_.passable[y])continue;if(y!=from&&y!=general_){if(avoid_structures&&(o.type[y]==3||y==castles_.c1||y==castles_.c2))continue;if(!picker_route_safe(o,y,stack))continue;}d[y]=d[x]+1;q.push(y);}}int best=-1,bd=INF;for(int k=0;k<4;++k){int y=g_.neighbor(from,k);if(y>=0&&d[y]>=0&&picker_route_safe(o,y,stack)&&d[y]<bd){best=y;bd=d[y];}}return best;};int y=search(true);return y>=0?y:search(false);}\n"
insert = needle + " int owned_next_toward(const Observation&o,int from,int target)const{if(from<0||target<0||from>=n_||target>=n_||from==target||o.owner[from]!=1||o.owner[target]!=1)return -1;std::vector<int>d(n_,-1);std::queue<int>q;d[target]=0;q.push(target);while(!q.empty()){int x=q.front();q.pop();for(int k=0;k<4;++k){int y=g_.neighbor(x,k);if(y<0||d[y]>=0||o.owner[y]!=1||!g_.passable[y])continue;if(y!=from&&y!=target&&(o.type[y]==3||y==castles_.c1||y==castles_.c2))continue;d[y]=d[x]+1;q.push(y);}}int best=-1,bd=INF;for(int k=0;k<4;++k){int y=g_.neighbor(from,k);if(y>=0&&o.owner[y]==1&&d[y]>=0&&d[y]<bd){best=y;bd=d[y];}}return best;}\n"
rep(needle, insert, "owned routing helper")

rep(
"if(o.type[y]==4&&o.owner[y]==2&&(o.turn>=800||safe_attack(o,x,y)))c.push_back({0,x,y,0,10000,Reason::TERMINAL_CAPTURE,false,ActionClass::HARD,y,-1,PacketRole::ATTACK});",
"if(o.type[y]==4&&o.owner[y]==2&&o.army[x]-1>o.army[y])c.push_back({0,x,y,0,10000,Reason::TERMINAL_CAPTURE,false,ActionClass::HARD,y,-1,PacketRole::ATTACK});",
"terminal capture")

castle_old = "  for(auto [site,f,index]:{std::tuple{castles_.c1,f1,0},std::tuple{castles_.c2,f2,1}})if(site>=0&&castle_state_[index]!=CastleState::BUILT&&(index==0||castle_state_[0]==CastleState::BUILT)){if(legal_build(o,site))c.push_back({1,site,site,2,100,Reason::CASTLE_DEADLINE,false,ActionClass::HARD,site,-1,index?PacketRole::CASTLE_C2:PacketRole::CASTLE_C1});else if(f.must_fund)for(int x=0;x<n_;++x)if(source(o,x)){int y=tactical_next(o,x,site);if(y>=0)c.push_back({1,x,y,0,double(o.army[x])/std::max(1,g_.dist[x][site]),Reason::CASTLE_DEADLINE,false,ActionClass::HARD,site,-1,index?PacketRole::CASTLE_C2:PacketRole::CASTLE_C1});}}\n"
castle_new = castle_old + "  bool late_c1_pending=castles_.c1>=0&&castle_state_[0]!=CastleState::BUILT&&o.turn>150;bool late_c2_pending=castles_.c2>=0&&castle_state_[1]!=CastleState::BUILT&&castle_state_[0]==CastleState::BUILT&&o.turn>250;bool late_castle_pending=late_c1_pending||late_c2_pending;if(!immediate&&late_castle_pending){for(auto [site,index,due]:{std::tuple{castles_.c1,0,late_c1_pending},std::tuple{castles_.c2,1,late_c2_pending}})if(due&&site>=0){auto role=index?PacketRole::CASTLE_C2:PacketRole::CASTLE_C1;if(o.owner[site]!=1){for(int d=0;d<4;++d){int x=g_.neighbor(site,d);if(!source(o,x)||x==general_)continue;bool can=o.owner[site]==0?(o.army[x]-1>o.army[site]):(o.owner[site]==2&&safe_attack(o,x,site));if(can)c.push_back({1,x,site,0,9800.+o.army[x],Reason::CASTLE_DEADLINE,false,ActionClass::HARD,site,-1,role});}}else if(legal_build(o,site))c.push_back({1,site,site,2,9900,Reason::CASTLE_DEADLINE,false,ActionClass::HARD,site,-1,role});else if(production_!=ProductionState::SEVERE_DEFICIT&&o.my_army>=live_castle_cost(o,site,w_)+30){std::vector<Candidate>fund;for(int x=0;x<n_;++x)if(source(o,x)&&x!=site&&x!=general_&&o.type[x]!=3&&reserve(o,x)==1){int y=tactical_next_logistics(o,x,site);if(y>=0&&o.owner[y]==1)fund.push_back({1,x,y,0,9700.+double(o.army[x])/std::max(1,g_.dist[x][site]),Reason::CASTLE_DEADLINE,false,ActionClass::HARD,site,-1,role});}if(!fund.empty()){c.push_back(schedule(fund));++late_castle_fund_moves_;}}}}\n"
rep(castle_old, castle_new, "late castle catchup")

active_old = "  else if(picker_.active&&o.army[picker_.cell]<=1){picker_.active=false;picker_wait_=0;++picker_aborts_;++picker_depleted_aborts_;}\n  if(picker_enabled_&&!picker_.active&&!immediate&&general_>=0){"
active_new = "  else if(picker_.active&&o.army[picker_.cell]<=1){picker_.active=false;picker_wait_=0;++picker_aborts_;++picker_depleted_aborts_;}\n  int enemy_general=belief_.confirmed()?belief_.confirmed_cell():-1;bool late_muster=picker_enabled_&&enemy_general>=0&&!immediate&&!late_castle_pending&&o.turn>=300&&production_!=ProductionState::SEVERE_DEFICIT&&(o.opp_army<=0||o.my_army>=o.opp_army+80||o.my_army*5>=o.opp_army*6);\n  if(picker_enabled_&&!picker_.active&&!immediate&&general_>=0&&!late_muster){"
rep(active_old, active_new, "late muster gate")

wall_end = "  if(picker_.active){int x=picker_.cell,y=-1,proj=(picker_.wall==0||picker_.wall==2)?general_%w_:general_/w_;if(picker_.phase==0){int cc=wall_coord(x,picker_.wall);if(cc!=proj&&picker_.dir!=0){int z=wall_cell_at(picker_.wall,cc+picker_.dir);if(z>=0&&picker_transit_safe(o,z))y=z;else picker_.phase=1;}else picker_.phase=1;}if(picker_.phase==1)y=owned_next_to_general(o,x);if(y>=0&&source(o,x)&&o.owner[y]==1){picker_.blocked_turns=0;c.push_back({2,x,y,0,3000.+o.army[x]*5.,Reason::EDGE_PICKER,false,ActionClass::LOGISTICS,general_,-1,PacketRole::EDGE_PICKER});}else if(x!=general_){++picker_.blocked_turns;++picker_blocked_ticks_;}}\n"
muster = wall_end + "  if(late_muster&&!picker_.active){++muster_windows_;int anchor=-1;long long anchor_score=-(1LL<<60);for(int x=0;x<n_;++x)if(source(o,x)&&x!=general_&&o.type[x]!=3&&x!=castles_.c1&&x!=castles_.c2){long long sc=1LL*o.army[x]*1000-g_.dist[x][enemy_general];if(sc>anchor_score){anchor_score=sc;anchor=x;}}if(anchor>=0){std::vector<Candidate>harvest;int donor_count=0,donor_mass=0;for(int x=0;x<n_;++x){if(x==anchor||x==general_||o.owner[x]!=1||o.type[x]==3||x==castles_.c1||x==castles_.c2||o.army[x]<muster_threshold_||reserve(o,x)!=1)continue;if(const Packet*p=packet_for(x))if(p->role==PacketRole::GENERAL_DEFENSE||p->role==PacketRole::CASTLE_C1||p->role==PacketRole::CASTLE_C2||p->role==PacketRole::COUNTERATTACK)continue;int y=owned_next_toward(o,x,anchor);if(y<0)continue;int surplus=o.army[x]-1;++donor_count;donor_mass+=surplus;harvest.push_back({2,x,y,0,5000.+surplus*20.-g_.dist[x][anchor],Reason::EDGE_PICKER,false,ActionClass::LOGISTICS,anchor,-1,PacketRole::ATTACK});}int eg_army=(enemy_general>=0&&o.owner[enemy_general]==2)?o.army[enemy_general]:0;int launch_need=std::max({90,eg_army*3+20,std::max(0,o.opp_army/2)});bool ready=o.army[anchor]>=launch_need||donor_count<=2||donor_mass<20;if(!ready&&!harvest.empty())c.push_back(schedule(harvest));else{int y=tactical_next(o,anchor,enemy_general);if(y>=0){auto cls=o.owner[y]==2?ActionClass::OFFENSE:ActionClass::LOGISTICS;c.push_back({2,anchor,y,0,6500.+o.army[anchor]*10.,Reason::EDGE_PICKER,false,cls,enemy_general,-1,PacketRole::ATTACK});}}}}\n"
rep(wall_end, muster, "muster collector")

act_old = "if(q.role==PacketRole::EDGE_PICKER){++picker_moves_;if(q.to==general_){picker_units_delivered_+=std::max(0,o.army[q.from]-1);picker_.active=false;picker_wait_=0;picker_.blocked_turns=0;++picker_completions_;}else{picker_.cell=q.to;picker_.blocked_turns=0;}}else if(picker_.active&&q.from==picker_.cell&&(q.reason==Reason::GENERAL_EMERGENCY||q.reason==Reason::TERMINAL_CAPTURE))"
act_new = "if(q.reason==Reason::EDGE_PICKER&&q.role==PacketRole::ATTACK){++muster_moves_;if(o.owner[q.to]==1)++muster_harvest_moves_;else ++muster_attack_moves_;}if(q.role==PacketRole::EDGE_PICKER){++picker_moves_;if(q.to==general_){picker_units_delivered_+=std::max(0,o.army[q.from]-1);picker_.active=false;picker_wait_=0;picker_.blocked_turns=0;++picker_completions_;}else{picker_.cell=q.to;picker_.blocked_turns=0;}}else if(picker_.active&&q.from==picker_.cell&&(q.reason==Reason::GENERAL_EMERGENCY||q.reason==Reason::TERMINAL_CAPTURE))"
rep(act_old, act_new, "muster action counters")

report_marker = "std::fprintf(stderr,\"[v35_castle_live] prevented_invalid_builds=%ld\\n\",live_cost_blocked_);"
report_new = report_marker + "std::fprintf(stderr,\"[v36_muster] threshold=%d windows=%ld moves=%ld harvest_moves=%ld attack_moves=%ld late_castle_fund_moves=%ld\\n\",muster_threshold_,muster_windows_,muster_moves_,muster_harvest_moves_,muster_attack_moves_,late_castle_fund_moves_);"
rep(report_marker, report_new, "muster report")

p.write_text(s)
print('picker-v9 patch applied')
