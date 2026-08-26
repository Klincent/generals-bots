from __future__ import annotations
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
MAIN=ROOT/'competition/agents/juraj_v35_cpp/main.cpp'
MARK='[e5_behavior]'

def once(s:str,old:str,new:str,label:str)->str:
    if new in s: return s
    n=s.count(old)
    if n!=1: raise RuntimeError(f'Evolution5 C++ transform {label}: expected 1 match, got {n}')
    return s.replace(old,new,1)

def apply(path:Path=MAIN):
    s=path.read_text()
    if '#include "evolution5_behavior.hpp"' not in s:
        s=once(s,'#include "evolution4_genome.hpp"\n','#include "evolution4_genome.hpp"\n#include "evolution5_behavior.hpp"\n','include')
    s=once(s,'GenomeConfig cfg_; Graph g_;','GenomeConfig cfg_; Evo5Behavior e5_; Graph g_;','member')
    s=once(s,'cfg_.load();doomguard_enabled_=cfg_.doomguard_enabled;','cfg_.load();e5_.load();doomguard_enabled_=cfg_.doomguard_enabled;','load')
    old='std::vector<Candidate>filtered;for(auto&q:c){bool reject=history_cycle(q)||!packet_route_ok(q);'
    new='bool e5_ahead=o.my_land>=o.opp_land&&o.my_army>=o.opp_army;bool e5_behind=production_==ProductionState::SEVERE_DEFICIT||o.my_army*100<std::max(1,o.opp_army)*80;e5_.update(o.turn,meaningful||confirmed_war,enemy_seen,e5_ahead,e5_behind,immediate||doomguard_active_);std::vector<Candidate>filtered;for(auto&q:c){if(!e5_.allow(q))continue;bool reject=history_cycle(q)||!packet_route_ok(q);'
    s=once(s,old,new,'candidate-filter')
    old='if(q.from<0){++pass_stats_.no_strategic_candidate;q=productive_fallback(o,sink);}if(q.kind==2&&!legal_build(o,q.from))'
    new='if(q.from<0){++pass_stats_.no_strategic_candidate;q=productive_fallback(o,sink);if(q.from>=0&&!e5_.allow(q))q={};}if(q.kind==2&&!legal_build(o,q.from))'
    s=once(s,old,new,'fallback-filter')
    if 'e5_.report();std::fprintf(stderr,"[v35_timing]' not in s:
        s=once(s,'std::fprintf(stderr,"[v35_timing]','e5_.report();std::fprintf(stderr,"[v35_timing]','telemetry')
    path.write_text(s)
    if '#include "evolution5_behavior.hpp"' not in s or 'e5_.update(' not in s or 'e5_.allow(q)' not in s: raise RuntimeError('Evolution5 C++ transform incomplete')
    print('Evolution5 behavior-graph C++ runtime activated')

if __name__=='__main__': apply()
