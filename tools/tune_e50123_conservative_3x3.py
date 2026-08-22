#!/usr/bin/env python3
from pathlib import Path
import re
p=Path('competition/agents/juraj_v35_cpp/main.cpp')
s=p.read_text()

def sub_func(sig,next_sig,new_body):
    global s
    pat=re.escape(sig)+r'.*?(?=\n '+re.escape(next_sig)+r')'
    m=re.search(pat,s,flags=re.S)
    if not m:
        if new_body in s:
            print(sig,'already tuned'); return
        raise SystemExit('missing function: '+sig)
    s=s[:m.start()]+new_body+s[m.end():]
    print('tuned',sig)

choose='''std::array<int,2> choose_probe_sectors(const Observation&o)const{std::array<int,2>out{{-1,-1}};if(belief_.confirmed()||general_<0||o.turn<100)return out;int reachable=search_reachable_count(),touched=sector_touched_count();if(reachable<=1||touched>=reachable)return out;int desired=o.turn>=600?reachable:(o.turn>=450?std::min(reachable,8):(o.turn>=300?std::min(reachable,6):(o.turn>=180?std::min(reachable,4):0)));if(touched>=desired)return out;std::vector<std::pair<double,int>>score;for(int sec=0;sec<9;++sec){if(sec==general_sector_||sector_target_[sec]<0||sector_first_touch_[sec]>=0)continue;int stale=sector_last_progress_[sec]<0?o.turn:o.turn-sector_last_progress_[sec];double v=10000.+std::min(stale,300)*2.0+g_.dist[general_][sector_target_[sec]];score.push_back({v,sec});}std::sort(score.begin(),score.end(),[](auto a,auto b){return std::tuple(-a.first,a.second)<std::tuple(-b.first,b.second);});if(!score.empty())out[0]=score[0].second;return out;}'''
sub_func('std::array<int,2> choose_probe_sectors(const Observation&o)const{','bool sector_probe_forced',choose)
forced='''bool sector_probe_forced(const Observation&o,int sec)const{if(sec<0||sector_first_touch_[sec]>=0)return false;int reachable=search_reachable_count(),touched=sector_touched_count();int desired=o.turn>=600?reachable:(o.turn>=450?std::min(reachable,8):(o.turn>=300?std::min(reachable,6):(o.turn>=180?std::min(reachable,4):0)));return touched<desired;}'''
sub_func('bool sector_probe_forced(const Observation&o,int s)const{','Candidate sector_probe_candidate',forced)
# Restore e501's SEARCH share after contact and make ALL hard tier<=1 actions preempt both search and picker.
old='''bool critical_available=std::any_of(filtered.begin(),filtered.end(),critical);bool coverage_force_available=std::any_of(filtered.begin(),filtered.end(),[](const Candidate&z){return z.role==PacketRole::SEARCH&&z.reason==Reason::SEARCH_PROGRESS&&z.tier==2;});double logistics_share=picker_.active?.24:(confirmed_war?.22:.15);std::array<double,5>share{{0,confirmed_war?.30:.12,production_==ProductionState::SEVERE_DEFICIT?.62:production_==ProductionState::SOFT_DEFICIT?.45:.35,!belief_.confirmed()?(enemy_seen?.14:.20):.05,logistics_share}};double total=share[1]+share[2]+share[3]+share[4];for(int i=1;i<5;++i)share[i]/=total;Candidate q;if(picker_.active&&critical_available){std::vector<Candidate>hv;for(auto&z:filtered)if(critical(z))hv.push_back(z);q=schedule(hv);}else if(coverage_force_available&&((picker_.active&&o.turn%6==0)||(!picker_.active&&o.turn%4==0))){std::vector<Candidate>sv;for(auto&z:filtered)if(z.role==PacketRole::SEARCH&&z.reason==Reason::SEARCH_PROGRESS&&z.tier==2)sv.push_back(z);q=schedule(sv);}else if(picker_.active&&picker_available){std::vector<Candidate>pv;for(auto&z:filtered)if(z.role==PacketRole::EDGE_PICKER)pv.push_back(z);q=schedule(pv);}else q=strategic_pick(filtered,share,immediate);'''
new='''bool critical_available=std::any_of(filtered.begin(),filtered.end(),critical);bool hard_available=std::any_of(filtered.begin(),filtered.end(),[](const Candidate&z){return z.tier<=1;});bool coverage_force_available=std::any_of(filtered.begin(),filtered.end(),[](const Candidate&z){return z.role==PacketRole::SEARCH&&z.reason==Reason::SEARCH_PROGRESS&&z.tier==2;});std::array<double,5>share{{0,confirmed_war?.30:.12,production_==ProductionState::SEVERE_DEFICIT?.62:production_==ProductionState::SOFT_DEFICIT?.45:.35,!enemy_seen?.20:.08,confirmed_war?.22:.15}};double total=share[1]+share[2]+share[3]+share[4];for(int i=1;i<5;++i)share[i]/=total;Candidate q;if(hard_available){std::vector<Candidate>hv;for(auto&z:filtered)if(z.tier<=1)hv.push_back(z);q=schedule(hv);}else if(coverage_force_available&&o.turn%10==0){std::vector<Candidate>sv;for(auto&z:filtered)if(z.role==PacketRole::SEARCH&&z.reason==Reason::SEARCH_PROGRESS&&z.tier==2)sv.push_back(z);q=schedule(sv);}else if(picker_.active&&picker_available){std::vector<Candidate>pv;for(auto&z:filtered)if(z.role==PacketRole::EDGE_PICKER)pv.push_back(z);q=schedule(pv);}else q=strategic_pick(filtered,share,immediate);'''
if old in s:
    s=s.replace(old,new,1); print('scheduler/search share tuned')
elif new in s:
    print('scheduler/search share already tuned')
else:
    raise SystemExit('scheduler anchor not found')
p.write_text(s)
