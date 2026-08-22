from __future__ import annotations
import argparse
from pathlib import Path


def replace_once(s:str, old:str, new:str, label:str)->str:
    n=s.count(old)
    if n!=1:
        raise RuntimeError(f'{label}: expected exactly one match, got {n}')
    return s.replace(old,new,1)


def upgrade(main:Path)->None:
    s=main.read_text()
    # Idempotent repair path for an already-upgraded template. Keep the structural
    # default (single/largest/full/interior/block_first/balanced/margin) behaviorally
    # equivalent to the pre-Turbo muster while retaining new dual/triple behavior.
    if '[e4_structural]' in s:
        old='bool ready=o.army[anchor]>=per_need||late_finish||donor_count[ai]<=1||donor_mass[ai]<12;'
        new='bool ready=o.army[anchor]>=per_need||late_finish||(want==1?(donor_count[ai]<=2||donor_mass[ai]<20):(donor_count[ai]<=1||donor_mass[ai]<12));'
        if old in s:
            s=replace_once(s,old,new,'single muster backward-equivalence repair')
            main.write_text(s)
            print('repaired structural single-muster compatibility')
        return

    old='int tactical_next_logistics(const Observation&o,int x,int target)const{int best=-1,bd=INF,be=-1,bdeg=-1;for(int d=0;d<4;++d){int y=g_.neighbor(x,d);if(!safe_step(o,x,y))continue;int dd=g_.dist[y][target];int edge=std::min({y/w_,h_-1-y/w_,y%w_,w_-1-y%w_}),deg=g_.degree(y);if(dd<bd||(dd==bd&&(edge>be||(edge==be&&(deg>bdeg||(deg==bdeg&&(best<0||y<best))))))){best=y;bd=dd;be=edge;bdeg=deg;}}return best;}'
    new='int tactical_next_logistics(const Observation&o,int x,int target)const{if(cfg_.logistics_route_policy=="shortest")return tactical_next(o,x,target);int best=-1,bd=INF,be=-1,bdeg=-1;for(int d=0;d<4;++d){int y=g_.neighbor(x,d);if(!safe_step(o,x,y))continue;int dd=g_.dist[y][target];int edge=std::min({y/w_,h_-1-y/w_,y%w_,w_-1-y%w_}),deg=g_.degree(y);if(dd<bd||(dd==bd&&(edge>be||(edge==be&&(deg>bdeg||(deg==bdeg&&(best<0||y<best))))))){best=y;bd=dd;be=edge;bdeg=deg;}}return best;}'
    s=replace_once(s,old,new,'logistics route policy')

    old='for(auto*v:{&enemy,&neutral,&persistent,&rear,&consolidate,&explore})if(!v->empty()){++pass_stats_.replaced;return pick(*v);}'
    new='if(cfg_.fallback_policy=="aggressive"){for(auto*v:{&enemy,&persistent,&neutral,&rear,&consolidate,&explore})if(!v->empty()){++pass_stats_.replaced;return pick(*v);}}else if(cfg_.fallback_policy=="consolidate"){for(auto*v:{&consolidate,&persistent,&rear,&enemy,&neutral,&explore})if(!v->empty()){++pass_stats_.replaced;return pick(*v);}}else{for(auto*v:{&enemy,&neutral,&persistent,&rear,&consolidate,&explore})if(!v->empty()){++pass_stats_.replaced;return pick(*v);}}'
    s=replace_once(s,old,new,'fallback policy')

    old='if(!blocks.empty())c.push_back(schedule(blocks));else if(!reinforce.empty())c.push_back(schedule(reinforce));}'
    new='if(cfg_.defense_policy=="reinforce_first"){if(!reinforce.empty())c.push_back(schedule(reinforce));else if(!blocks.empty())c.push_back(schedule(blocks));}else{if(!blocks.empty())c.push_back(schedule(blocks));else if(!reinforce.empty())c.push_back(schedule(reinforce));}}'
    s=replace_once(s,old,new,'defense policy')

    old='double margin=mass-edge_picker_min_efficiency_*moves;if(best_start<0||std::tuple(-margin,-mass,moves,wall,start)<std::tuple(-best_margin,-best_mass,best_moves,best_wall,best_start)){best_wall=wall;best_start=start;best_dir=side<0?1:-1;best_mass=mass;best_moves=moves;best_margin=margin;}'
    new='double margin=mass-edge_picker_min_efficiency_*moves;double policy_score=margin;if(cfg_.picker_start_policy=="mass")policy_score=mass;else if(cfg_.picker_start_policy=="efficiency")policy_score=eff;else if(cfg_.picker_start_policy=="speed")policy_score=-moves;if(best_start<0||std::tuple(-policy_score,-mass,moves,wall,start)<std::tuple(-best_margin,-best_mass,best_moves,best_wall,best_start)){best_wall=wall;best_start=start;best_dir=side<0?1:-1;best_mass=mass;best_moves=moves;best_margin=policy_score;}'
    s=replace_once(s,old,new,'picker start policy')

    begin='  if(late_muster&&!picker_.active){'
    end='  for(int x=0;x<n_;++x)if(source(o,x)){if(picker_.active&&x==picker_.cell)continue;'
    i=s.find(begin)
    j=s.find(end,i+1)
    if i<0 or j<0 or j<=i:
        raise RuntimeError('late muster block markers missing')
    new_muster=r'''  if(late_muster&&!picker_.active){
   ++muster_windows_;
   struct MA{int x;long long score;};std::vector<MA>apool;
   for(int x=0;x<n_;++x)if(source(o,x)&&x!=general_&&o.type[x]!=3&&x!=castles_.c1&&x!=castles_.c2){long long sc=0;if(cfg_.muster_anchor_policy=="forward")sc=-1LL*g_.dist[x][enemy_general]*1000+1LL*o.army[x]*20;else if(cfg_.muster_anchor_policy=="central"){int edge=std::min({x/w_,h_-1-x/w_,x%w_,w_-1-x%w_});sc=1LL*edge*1000+1LL*o.army[x]*20-g_.dist[x][enemy_general];}else sc=1LL*o.army[x]*1000-g_.dist[x][enemy_general];apool.push_back({x,sc});}
   std::sort(apool.begin(),apool.end(),[](const MA&a,const MA&b){return std::tuple(-a.score,a.x)<std::tuple(-b.score,b.x);});int want=cfg_.muster_topology=="triple"?3:cfg_.muster_topology=="dual"?2:1;std::vector<int>anchors;for(const auto&a:apool){anchors.push_back(a.x);if((int)anchors.size()>=want)break;}
   if(!anchors.empty()){std::vector<std::vector<Candidate>>harvest(anchors.size());std::vector<int>donor_count(anchors.size()),donor_mass(anchors.size());bool split_transfer=cfg_.chunk_transfer_policy=="split";
    for(int x=0;x<n_;++x){if(x==general_||o.owner[x]!=1||o.type[x]==3||x==castles_.c1||x==castles_.c2||o.army[x]<muster_threshold_||reserve(o,x)!=1||std::find(anchors.begin(),anchors.end(),x)!=anchors.end())continue;if(const Packet*p=packet_for(x))if(p->role==PacketRole::GENERAL_DEFENSE||p->role==PacketRole::CASTLE_C1||p->role==PacketRole::CASTLE_C2||p->role==PacketRole::COUNTERATTACK)continue;int ai=0;if(anchors.size()>1){long long best=(1LL<<60);for(int k=0;k<(int)anchors.size();++k){long long d=g_.dist[x][anchors[k]];long long balance=1LL*donor_mass[k]/10;long long q=d*100+balance;if(q<best){best=q;ai=k;}}}int y=owned_next_toward(o,x,anchors[ai]);if(y<0)continue;int surplus=o.army[x]-1;++donor_count[ai];donor_mass[ai]+=surplus;harvest[ai].push_back({1,x,y,0,5000.+surplus*20.-g_.dist[x][anchors[ai]],Reason::EDGE_PICKER,split_transfer,ActionClass::LOGISTICS,anchors[ai],-1,PacketRole::ATTACK});}
    int eg_army=(enemy_general>=0&&o.owner[enemy_general]==2)?o.army[enemy_general]:0;int global_need=std::max({cfg_.muster_launch_base,int(eg_army*cfg_.muster_enemy_mult)+cfg_.muster_enemy_bonus,std::max(0,o.opp_army/std::max(1,cfg_.muster_opp_divisor))});int global_late_need=std::max(cfg_.late_finish_base,int(eg_army*cfg_.late_finish_enemy_mult)+cfg_.late_finish_enemy_bonus);std::vector<Candidate>attack_now,harvest_now;
    for(int ai=0;ai<(int)anchors.size();++ai){int anchor=anchors[ai];int per_need=want==1?global_need:std::max(35,(global_need+want-1)/want+10);int late_need=want==1?global_late_need:std::max(30,(global_late_need+want-1)/want+5);bool late_finish=o.turn>=cfg_.late_finish_turn&&o.army[anchor]>=late_need;bool ready=o.army[anchor]>=per_need||late_finish||(want==1?(donor_count[ai]<=2||donor_mass[ai]<20):(donor_count[ai]<=1||donor_mass[ai]<12));if(ready){int y=tactical_next(o,anchor,enemy_general);if(y>=0){auto cls=o.owner[y]==2?ActionClass::OFFENSE:ActionClass::LOGISTICS;attack_now.push_back({1,anchor,y,0,6500.+o.army[anchor]*10.-ai,Reason::EDGE_PICKER,false,cls,enemy_general,-1,PacketRole::ATTACK});}}else for(auto&q:harvest[ai])harvest_now.push_back(q);}
    if(!attack_now.empty())c.push_back(schedule(attack_now));else if(!harvest_now.empty())c.push_back(schedule(harvest_now));
   }
  }
'''
    s=s[:i]+new_muster+s[j:]

    marker='std::fprintf(stderr,"[v35_timing] p50=%.3f p95=%.3f p99=%.3f max=%.3f\\n",pct(.5),pct(.95),pct(.99),times_.back());'
    report='std::fprintf(stderr,"[e4_structural] muster_topology=%s anchor=%s transfer=%s logistics=%s defense=%s fallback=%s picker_start=%s\\n",cfg_.muster_topology.c_str(),cfg_.muster_anchor_policy.c_str(),cfg_.chunk_transfer_policy.c_str(),cfg_.logistics_route_policy.c_str(),cfg_.defense_policy.c_str(),cfg_.fallback_policy.c_str(),cfg_.picker_start_policy.c_str());'+marker
    s=replace_once(s,marker,report,'structural telemetry')
    main.write_text(s)


def main_cli():
    p=argparse.ArgumentParser();p.add_argument('main_cpp',type=Path);a=p.parse_args();upgrade(a.main_cpp)

if __name__=='__main__': main_cli()
