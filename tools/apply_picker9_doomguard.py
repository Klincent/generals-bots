from pathlib import Path

p = Path('competition/agents/juraj_v35_cpp/main.cpp')
s = p.read_text()

def replace_once(old: str, new: str, label: str) -> None:
    global s
    if old not in s:
        raise SystemExit(f'{label}: anchor not found')
    s = s.replace(old, new, 1)

replace_once(
    ' std::array<int,2> live_cost_{{35,35}};std::array<int,2> castle_start_{{-1,-1}},castle_build_{{-1,-1}},castle_latest_{{-1,-1}},castle_actions_{{0,0}};std::string castle_miss_="none";',
    ' bool doomguard_enabled_=true,doomguard_active_=false;int doom_enemy_=-1,doom_eta_=INF,doom_muster_=-1,doom_reachable_last_=0;long doom_starts_=0,doom_releases_=0,doom_windows_=0,doom_moves_=0,doom_unreachable_=0;\n std::array<int,2> live_cost_{{35,35}};std::array<int,2> castle_start_{{-1,-1}},castle_build_{{-1,-1}},castle_latest_{{-1,-1}},castle_actions_{{0,0}};std::string castle_miss_="none";',
    'doomguard state',
)

replace_once(
    'owned_castle_history_.assign(n_,0);for(int x=0;x<n_;++x)if(o.owner[x]==1&&o.type[x]==3)owned_castle_history_[x]=1;if(const char*e=std::getenv("V35_PICKER_ENABLED"))',
    'owned_castle_history_.assign(n_,0);for(int x=0;x<n_;++x)if(o.owner[x]==1&&o.type[x]==3)owned_castle_history_[x]=1;if(const char*e=std::getenv("V35_DOOMGUARD_ENABLED"))doomguard_enabled_=std::atoi(e)!=0;if(const char*e=std::getenv("V35_PICKER_ENABLED"))',
    'doomguard env gate',
)

replace_once(
    'opponent_.update(ev);auto adapt=opponent_.adaptation();',
    '''opponent_.update(ev);auto adapt=opponent_.adaptation();
  int own_peak=0;for(int x=0;x<n_;++x)if(o.owner[x]==1)own_peak=std::max(own_peak,o.army[x]);int doom_eta_now=(largest>=0&&general_>=0)?g_.dist[largest][general_]:INF;int doom_floor=std::max(18,std::max(1,o.opp_army)*15/100);bool doom_regular=largest>=0&&o.type[largest]!=3&&o.type[largest]!=4;bool doom_now=doomguard_enabled_&&doom_regular&&doom_eta_now<=12&&largest_army>=doom_floor&&own_peak*100<std::max(1,o.my_army)*45&&(moved_enemy(o,largest)||doom_eta_now<=8);if(doom_now&&!doomguard_active_)++doom_starts_;if(!doom_now&&doomguard_active_)++doom_releases_;doomguard_active_=doom_now;doom_enemy_=doom_now?largest:-1;doom_eta_=doom_now?doom_eta_now:INF;doom_muster_=general_;if(doom_now&&general_>=0){int m=general_,steps=doom_eta_now>=9?3:doom_eta_now>=6?2:1;for(int i=0;i<steps;++i){int z=g_.next[m][largest];if(z<0||z==largest||o.owner[z]!=1||o.type[z]==3)break;m=z;}doom_muster_=m;++doom_windows_;}''',
    'doomguard detector',
)

anchor = '  for(int t=0;t<n_;++t)if(owned_castle_history_[t]&&o.type[t]==3&&o.owner[t]==2)'
if anchor not in s:
    raise SystemExit('doomguard candidate anchor not found')
block = r'''  if(doomguard_active_&&doom_enemy_>=0&&doom_muster_>=0){struct DF{int x,y,dx,surplus;double eff;};std::vector<DF>feeds;for(int x=0;x<n_;++x)if(source(o,x)&&x!=general_&&x!=doom_muster_){if(doom_eta_>5&&(o.type[x]==3||x==castles_.c1||x==castles_.c2))continue;bool hot=false;for(int d=0;d<4;++d){int z=g_.neighbor(x,d);if(z>=0&&o.owner[z]==2){hot=true;break;}}if(hot&&doom_eta_>5)continue;int surplus=o.army[x]-reserve(o,x);if(surplus<=0||(o.army[x]<3&&doom_eta_>6))continue;int dx=g_.dist[x][doom_muster_];if(dx<=0||dx>=INF||dx+1>=doom_eta_)continue;int y=-1,bd=dx,bdeg=-1;for(int d=0;d<4;++d){int z=g_.neighbor(x,d);if(z<0||o.owner[z]!=1||!safe_step(o,x,z))continue;int dd=g_.dist[z][doom_muster_],deg=g_.degree(z);if(dd<bd||(dd==bd&&deg>bdeg)){y=z;bd=dd;bdeg=deg;}}if(y>=0)feeds.push_back({x,y,dx,surplus,double(surplus)/std::max(1,dx)});}std::sort(feeds.begin(),feeds.end(),[](const DF&a,const DF&b){return std::tuple(-a.eff,a.dx,-a.surplus,a.x)<std::tuple(-b.eff,b.dx,-b.surplus,b.x);});int action_budget=std::max(1,doom_eta_-2),reachable=(o.owner[doom_muster_]==1?o.army[doom_muster_]:0);std::vector<Candidate>muster;for(const auto&f:feeds){if(f.dx>action_budget)continue;action_budget-=f.dx;reachable+=f.surplus;double u=8100.+240.*f.eff+2.*o.army[f.x]-5.*f.dx;muster.push_back({1,f.x,f.y,0,u,Reason::GENERAL_EMERGENCY,false,ActionClass::HARD,doom_muster_,-1,PacketRole::GENERAL_DEFENSE});}doom_reachable_last_=reachable;int useful=std::max(12,largest_army*60/100);if(reachable>=useful||doom_eta_<=6){if(!muster.empty())c.push_back(schedule(muster));}else ++doom_unreachable_;}
'''
s = s.replace(anchor, block + anchor, 1)

replace_once(
    'if(a.kind==0){',
    'if(a.kind==0){if(doomguard_active_&&q.reason==Reason::GENERAL_EMERGENCY&&q.role==PacketRole::GENERAL_DEFENSE&&q.target==doom_muster_)++doom_moves_;',
    'doomguard selected-move telemetry',
)

replace_once(
    'std::fprintf(stderr,"[v35_timing] p50=',
    'std::fprintf(stderr,"[v35_doomguard] enabled=%d starts=%ld releases=%ld windows=%ld moves=%ld unreachable=%ld active=%d enemy=%d eta=%d muster=%d reachable=%d\\n",doomguard_enabled_?1:0,doom_starts_,doom_releases_,doom_windows_,doom_moves_,doom_unreachable_,doomguard_active_?1:0,doom_enemy_,doom_eta_,doom_muster_,doom_reachable_last_);std::fprintf(stderr,"[v35_timing] p50=',
    'doomguard report',
)

p.write_text(s)
print('applied DoomGuard to picker9', p)
