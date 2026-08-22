from __future__ import annotations
import argparse
from pathlib import Path


def repl(s:str,old:str,new:str,label:str)->str:
    n=s.count(old)
    if n!=1:
        raise RuntimeError(f'{label}: expected one match, got {n}')
    return s.replace(old,new,1)


def upgrade(main:Path)->None:
    s=main.read_text()
    if '[e4_nested_v2]' in s:
        print('nested structural C++ already applied'); return
    if '[e4_structural]' not in s:
        raise RuntimeError('base Turbo structural phenotype missing')

    old='int tactical_next_logistics(const Observation&o,int x,int target)const{if(cfg_.logistics_route_policy=="shortest")return tactical_next(o,x,target);int best=-1,bd=INF,be=-1,bdeg=-1;for(int d=0;d<4;++d){int y=g_.neighbor(x,d);if(!safe_step(o,x,y))continue;int dd=g_.dist[y][target];int edge=std::min({y/w_,h_-1-y/w_,y%w_,w_-1-y%w_}),deg=g_.degree(y);if(dd<bd||(dd==bd&&(edge>be||(edge==be&&(deg>bdeg||(deg==bdeg&&(best<0||y<best))))))){best=y;bd=dd;be=edge;bdeg=deg;}}return best;}'
    new='int tactical_next_logistics(const Observation&o,int x,int target)const{if(cfg_.logistics_route_policy=="shortest")return tactical_next(o,x,target);int best=-1,bd=INF,be=-1,bdeg=-1,br=INF;for(int d=0;d<4;++d){int y=g_.neighbor(x,d);if(!safe_step(o,x,y))continue;int dd=g_.dist[y][target];int edge=std::min({y/w_,h_-1-y/w_,y%w_,w_-1-y%w_}),deg=g_.degree(y),risk=0;for(int k=0;k<4;++k){int z=g_.neighbor(y,k);if(z>=0&&o.owner[z]==2)risk=std::max(risk,o.army[z]);}bool better=cfg_.logistics_route_policy=="safest"?(risk<br||(risk==br&&(dd<bd||(dd==bd&&(edge>be||(edge==be&&(deg>bdeg||(deg==bdeg&&(best<0||y<best))))))))):(dd<bd||(dd==bd&&(edge>be||(edge==be&&(deg>bdeg||(deg==bdeg&&(best<0||y<best)))))));if(better){best=y;bd=dd;be=edge;bdeg=deg;br=risk;}}return best;}'
    s=repl(s,old,new,'safest logistics')

    old='if(cfg_.fallback_policy=="aggressive"){for(auto*v:{&enemy,&persistent,&neutral,&rear,&consolidate,&explore})if(!v->empty()){++pass_stats_.replaced;return pick(*v);}}else if(cfg_.fallback_policy=="consolidate"){for(auto*v:{&consolidate,&persistent,&rear,&enemy,&neutral,&explore})if(!v->empty()){++pass_stats_.replaced;return pick(*v);}}else{for(auto*v:{&enemy,&neutral,&persistent,&rear,&consolidate,&explore})if(!v->empty()){++pass_stats_.replaced;return pick(*v);}}'
    new='if(cfg_.fallback_policy=="aggressive"){for(auto*v:{&enemy,&persistent,&neutral,&rear,&consolidate,&explore})if(!v->empty()){++pass_stats_.replaced;return pick(*v);}}else if(cfg_.fallback_policy=="consolidate"){for(auto*v:{&consolidate,&persistent,&rear,&enemy,&neutral,&explore})if(!v->empty()){++pass_stats_.replaced;return pick(*v);}}else if(cfg_.fallback_policy=="exploration"){for(auto*v:{&explore,&neutral,&persistent,&rear,&consolidate,&enemy})if(!v->empty()){++pass_stats_.replaced;return pick(*v);}}else if(cfg_.fallback_policy=="defensive"){for(auto*v:{&persistent,&rear,&consolidate,&enemy,&neutral,&explore})if(!v->empty()){++pass_stats_.replaced;return pick(*v);}}else if(cfg_.fallback_policy=="opportunity"){std::vector<Candidate>best;for(auto*v:{&enemy,&neutral,&persistent,&rear,&consolidate,&explore})if(!v->empty())best.push_back(pick(*v));if(!best.empty()){++pass_stats_.replaced;return pick(best);}}else{for(auto*v:{&enemy,&neutral,&persistent,&rear,&consolidate,&explore})if(!v->empty()){++pass_stats_.replaced;return pick(*v);}}'
    s=repl(s,old,new,'fallback catalogue')

    old='if(cfg_.defense_policy=="reinforce_first"){if(!reinforce.empty())c.push_back(schedule(reinforce));else if(!blocks.empty())c.push_back(schedule(blocks));}else{if(!blocks.empty())c.push_back(schedule(blocks));else if(!reinforce.empty())c.push_back(schedule(reinforce));}}'
    new='bool rf=cfg_.defense_policy=="reinforce_first"||(cfg_.defense_policy=="adaptive"&&primary_eta<=2);if(rf){if(!reinforce.empty())c.push_back(schedule(reinforce));else if(!blocks.empty())c.push_back(schedule(blocks));}else{if(!blocks.empty())c.push_back(schedule(blocks));else if(!reinforce.empty())c.push_back(schedule(reinforce));}}'
    s=repl(s,old,new,'adaptive defense')

    old='if(cfg_.muster_anchor_policy=="forward")sc=-1LL*g_.dist[x][enemy_general]*1000+1LL*o.army[x]*20;else if(cfg_.muster_anchor_policy=="central"){int edge=std::min({x/w_,h_-1-x/w_,x%w_,w_-1-x%w_});sc=1LL*edge*1000+1LL*o.army[x]*20-g_.dist[x][enemy_general];}else sc=1LL*o.army[x]*1000-g_.dist[x][enemy_general];'
    new='if(cfg_.muster_anchor_policy=="forward")sc=-1LL*g_.dist[x][enemy_general]*1000+1LL*o.army[x]*20;else if(cfg_.muster_anchor_policy=="central"){int edge=std::min({x/w_,h_-1-x/w_,x%w_,w_-1-x%w_});sc=1LL*edge*1000+1LL*o.army[x]*20-g_.dist[x][enemy_general];}else if(cfg_.muster_anchor_policy=="production")sc=1LL*g_.degree(x)*1500+1LL*o.army[x]*50-10LL*g_.dist[x][enemy_general];else sc=1LL*o.army[x]*1000-g_.dist[x][enemy_general];'
    s=repl(s,old,new,'production anchor')

    old='int want=cfg_.muster_topology=="triple"?3:cfg_.muster_topology=="dual"?2:1;'
    new='int want=cfg_.muster_topology=="triple"?3:cfg_.muster_topology=="dual"?2:1;if(cfg_.muster_topology=="adaptive")want=o.my_army>=300?3:o.my_army>=160?2:1;'
    s=repl(s,old,new,'adaptive topology')

    old='bool split_transfer=cfg_.chunk_transfer_policy=="split";'
    new='bool split_transfer=cfg_.chunk_transfer_policy=="split";'
    if old not in s: raise RuntimeError('transfer policy marker missing')

    old='harvest[ai].push_back({1,x,y,0,5000.+surplus*20.-g_.dist[x][anchors[ai]],Reason::EDGE_PICKER,split_transfer,ActionClass::LOGISTICS,anchors[ai],-1,PacketRole::ATTACK});'
    new='bool do_split=split_transfer||(cfg_.chunk_transfer_policy=="adaptive"&&surplus>2*muster_threshold_);harvest[ai].push_back({1,x,y,0,5000.+surplus*20.-g_.dist[x][anchors[ai]],Reason::EDGE_PICKER,do_split,ActionClass::LOGISTICS,anchors[ai],-1,PacketRole::ATTACK});'
    s=repl(s,old,new,'adaptive chunk transfer')

    marker='std::fprintf(stderr,"[e4_structural] muster_topology=%s anchor=%s transfer=%s logistics=%s defense=%s fallback=%s picker_start=%s\\n",cfg_.muster_topology.c_str(),cfg_.muster_anchor_policy.c_str(),cfg_.chunk_transfer_policy.c_str(),cfg_.logistics_route_policy.c_str(),cfg_.defense_policy.c_str(),cfg_.fallback_policy.c_str(),cfg_.picker_start_policy.c_str());'
    s=repl(s,marker,marker+'std::fprintf(stderr,"[e4_nested_v2] enabled=1\\n");','nested telemetry marker')
    main.write_text(s)
    print('nested structural C++ applied')


def main_cli():
    p=argparse.ArgumentParser();p.add_argument('main_cpp',type=Path);a=p.parse_args();upgrade(a.main_cpp)

if __name__=='__main__': main_cli()
