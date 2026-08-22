from __future__ import annotations
import argparse
from pathlib import Path

HEADER = r'''#pragma once
#include <algorithm>
#include <cstdlib>
#include <cstring>

static inline int evo4_int(const char* n,int d,int lo,int hi){const char*e=std::getenv(n);if(!e)return d;long v=std::strtol(e,nullptr,10);return std::max(lo,std::min(hi,(int)v));}
static inline double evo4_double(const char* n,double d,double lo,double hi){const char*e=std::getenv(n);if(!e)return d;double v=std::strtod(e,nullptr);return std::max(lo,std::min(hi,v));}
static inline bool evo4_bool(const char* n,bool d){const char*e=std::getenv(n);if(!e)return d;return std::strcmp(e,"0")!=0&&std::strcmp(e,"false")!=0&&std::strcmp(e,"FALSE")!=0;}

struct GenomeConfig {
 bool doomguard_enabled=true,picker_enabled=true;
 int edge_picker_threshold=16,muster_threshold=8,general_reserve_base=5,general_reserve_opp_divisor=12,adjacent_reserve_base=2;
 double picker_min_efficiency=2.0,production_recover_slope=.1;
 int production_recover_gap=10,production_severe_gap=18,production_soft_gap=8,castle1_target_turn=150,castle2_target_turn=250;
 double war_share_contact=.30,war_share_peace=.12,expansion_share_severe=.62,expansion_share_soft=.45,expansion_share_healthy=.35;
 int precontact_expansion_until=-1; double expansion_share_precontact=.35,search_share_unseen=.20,search_share_seen=.08,free_share_war=.22,free_share_peace=.15;
 int expansion_wait_limit=4,muster_start_turn=300,muster_army_margin=80,muster_ratio_num=5,muster_ratio_den=6,muster_launch_base=90;
 double muster_enemy_mult=3.0; int muster_enemy_bonus=20,muster_opp_divisor=2,late_finish_turn=900,late_finish_base=70;
 double late_finish_enemy_mult=2.0; int late_finish_enemy_bonus=15,picker_mature_turn=150,picker_mature_land_pct=35,picker_not_behind_num=5,picker_not_behind_den=4;
 double picker_growth25=.08,picker_growth50=.06; int picker_growth_land_pct=45; double picker_top3_share_max=.55; int late_castle_army_margin=30;
 void load(){
  doomguard_enabled=evo4_bool("EVO4_DOOMGUARD_ENABLED",doomguard_enabled); picker_enabled=evo4_bool("EVO4_PICKER_ENABLED",picker_enabled);
  edge_picker_threshold=evo4_int("EVO4_EDGE_PICKER_THRESHOLD",edge_picker_threshold,0,60); picker_min_efficiency=evo4_double("EVO4_PICKER_MIN_EFFICIENCY",picker_min_efficiency,.5,8.0); muster_threshold=evo4_int("EVO4_MUSTER_THRESHOLD",muster_threshold,4,30);
  general_reserve_base=evo4_int("EVO4_GENERAL_RESERVE_BASE",general_reserve_base,2,20); general_reserve_opp_divisor=evo4_int("EVO4_GENERAL_RESERVE_OPP_DIVISOR",general_reserve_opp_divisor,4,30); adjacent_reserve_base=evo4_int("EVO4_ADJACENT_RESERVE_BASE",adjacent_reserve_base,1,10);
  production_recover_gap=evo4_int("EVO4_PRODUCTION_RECOVER_GAP",production_recover_gap,2,20); production_recover_slope=evo4_double("EVO4_PRODUCTION_RECOVER_SLOPE",production_recover_slope,0,.5); production_severe_gap=evo4_int("EVO4_PRODUCTION_SEVERE_GAP",production_severe_gap,8,40); production_soft_gap=evo4_int("EVO4_PRODUCTION_SOFT_GAP",production_soft_gap,2,20);
  castle1_target_turn=evo4_int("EVO4_CASTLE1_TARGET_TURN",castle1_target_turn,90,260); castle2_target_turn=evo4_int("EVO4_CASTLE2_TARGET_TURN",castle2_target_turn,160,420);
  war_share_contact=evo4_double("EVO4_WAR_SHARE_CONTACT",war_share_contact,.10,.60); war_share_peace=evo4_double("EVO4_WAR_SHARE_PEACE",war_share_peace,.02,.35);
  expansion_share_severe=evo4_double("EVO4_EXPANSION_SHARE_SEVERE",expansion_share_severe,.35,.85); expansion_share_soft=evo4_double("EVO4_EXPANSION_SHARE_SOFT",expansion_share_soft,.25,.70); expansion_share_healthy=evo4_double("EVO4_EXPANSION_SHARE_HEALTHY",expansion_share_healthy,.15,.60);
  precontact_expansion_until=evo4_int("EVO4_PRECONTACT_EXPANSION_UNTIL",precontact_expansion_until,-1,500); expansion_share_precontact=evo4_double("EVO4_EXPANSION_SHARE_PRECONTACT",expansion_share_precontact,.15,.65);
  search_share_unseen=evo4_double("EVO4_SEARCH_SHARE_UNSEEN",search_share_unseen,.05,.50); search_share_seen=evo4_double("EVO4_SEARCH_SHARE_SEEN",search_share_seen,.01,.30); free_share_war=evo4_double("EVO4_FREE_SHARE_WAR",free_share_war,.05,.45); free_share_peace=evo4_double("EVO4_FREE_SHARE_PEACE",free_share_peace,.03,.40);
  expansion_wait_limit=evo4_int("EVO4_EXPANSION_WAIT_LIMIT",expansion_wait_limit,1,12); muster_start_turn=evo4_int("EVO4_MUSTER_START_TURN",muster_start_turn,180,650); muster_army_margin=evo4_int("EVO4_MUSTER_ARMY_MARGIN",muster_army_margin,20,180); muster_ratio_num=evo4_int("EVO4_MUSTER_RATIO_NUM",muster_ratio_num,2,10); muster_ratio_den=evo4_int("EVO4_MUSTER_RATIO_DEN",muster_ratio_den,2,12);
  muster_launch_base=evo4_int("EVO4_MUSTER_LAUNCH_BASE",muster_launch_base,45,180); muster_enemy_mult=evo4_double("EVO4_MUSTER_ENEMY_MULT",muster_enemy_mult,1.5,5); muster_enemy_bonus=evo4_int("EVO4_MUSTER_ENEMY_BONUS",muster_enemy_bonus,0,60); muster_opp_divisor=evo4_int("EVO4_MUSTER_OPP_DIVISOR",muster_opp_divisor,1,5);
  late_finish_turn=evo4_int("EVO4_LATE_FINISH_TURN",late_finish_turn,650,1100); late_finish_base=evo4_int("EVO4_LATE_FINISH_BASE",late_finish_base,35,140); late_finish_enemy_mult=evo4_double("EVO4_LATE_FINISH_ENEMY_MULT",late_finish_enemy_mult,1,4); late_finish_enemy_bonus=evo4_int("EVO4_LATE_FINISH_ENEMY_BONUS",late_finish_enemy_bonus,0,50);
  picker_mature_turn=evo4_int("EVO4_PICKER_MATURE_TURN",picker_mature_turn,80,350); picker_mature_land_pct=evo4_int("EVO4_PICKER_MATURE_LAND_PCT",picker_mature_land_pct,20,60); picker_not_behind_num=evo4_int("EVO4_PICKER_NOT_BEHIND_NUM",picker_not_behind_num,2,10); picker_not_behind_den=evo4_int("EVO4_PICKER_NOT_BEHIND_DEN",picker_not_behind_den,2,10);
  picker_growth25=evo4_double("EVO4_PICKER_GROWTH25",picker_growth25,0,.25); picker_growth50=evo4_double("EVO4_PICKER_GROWTH50",picker_growth50,0,.20); picker_growth_land_pct=evo4_int("EVO4_PICKER_GROWTH_LAND_PCT",picker_growth_land_pct,25,70); picker_top3_share_max=evo4_double("EVO4_PICKER_TOP3_SHARE_MAX",picker_top3_share_max,.30,.85); late_castle_army_margin=evo4_int("EVO4_LATE_CASTLE_ARMY_MARGIN",late_castle_army_margin,10,90);
 }
};
'''

def once(s: str, old: str, new: str, label: str) -> str:
    n=s.count(old)
    if n != 1: raise RuntimeError(f'{label}: expected one marker, found {n}')
    return s.replace(old,new,1)

def transform(main_path: Path):
    s=main_path.read_text()
    if '#include "evolution4_genome.hpp"' in s:
        return
    s=once(s,'#include "core.hpp"\n','#include "core.hpp"\n#include "evolution4_genome.hpp"\n','include')
    s=once(s,' Graph g_;CastleChoice castles_;',' GenomeConfig cfg_; Graph g_;CastleChoice castles_;','config member')
    old='if(const char*e=std::getenv("V35_DOOMGUARD_ENABLED"))doomguard_enabled_=std::atoi(e)!=0;if(const char*e=std::getenv("V35_PICKER_ENABLED"))picker_enabled_=std::strcmp(e,"0")!=0;if(const char*e=std::getenv("V35_EDGE_PICKER_THRESHOLD")){int v=std::atoi(e);if(v>=0&&v<=100)edge_picker_threshold_=v;}if(const char*e=std::getenv("V36_EDGE_PICKER_MIN_EFFICIENCY")){double v=std::atof(e);if(v>=0.0&&v<=20.0)edge_picker_min_efficiency_=v;}if(const char*e=std::getenv("V35_MUSTER_THRESHOLD")){int v=std::atoi(e);if(v>=4&&v<=50)muster_threshold_=v;}'
    new='cfg_.load();doomguard_enabled_=cfg_.doomguard_enabled;picker_enabled_=cfg_.picker_enabled;edge_picker_threshold_=cfg_.edge_picker_threshold;edge_picker_min_efficiency_=cfg_.picker_min_efficiency;muster_threshold_=cfg_.muster_threshold;'
    s=once(s,old,new,'legacy env block')
    s=once(s,'int reserve(const Observation&o,int x)const{if(x==general_)return std::max(5,o.opp_army/12);for(int d=0;d<4;++d){int y=g_.neighbor(x,d);if(y>=0&&o.owner[y]==2)return std::max(2,o.army[y]+1);}return 1;}',
           'int reserve(const Observation&o,int x)const{if(x==general_)return std::max(cfg_.general_reserve_base,o.opp_army/std::max(1,cfg_.general_reserve_opp_divisor));for(int d=0;d<4;++d){int y=g_.neighbor(x,d);if(y>=0&&o.owner[y]==2)return std::max(cfg_.adjacent_reserve_base,o.army[y]+1);}return 1;}','reserve')
    s=once(s,'if(!immediate&&available[(int)ActionClass::EXPANSION]&&expansion_wait_>=4)','if(!immediate&&available[(int)ActionClass::EXPANSION]&&expansion_wait_>=cfg_.expansion_wait_limit)','expansion wait')
    s=once(s,'if(production_==ProductionState::SEVERE_DEFICIT)production_=gap<10&&slope(land_hist_,10)>.1?ProductionState::SOFT_DEFICIT:production_;else if(gap>18)production_=ProductionState::SEVERE_DEFICIT;else if(gap>8)production_=ProductionState::SOFT_DEFICIT;',
           'if(production_==ProductionState::SEVERE_DEFICIT)production_=gap<cfg_.production_recover_gap&&slope(land_hist_,10)>cfg_.production_recover_slope?ProductionState::SOFT_DEFICIT:production_;else if(gap>cfg_.production_severe_gap)production_=ProductionState::SEVERE_DEFICIT;else if(gap>cfg_.production_soft_gap)production_=ProductionState::SOFT_DEFICIT;','production')
    s=once(s,'forecast(o.turn,150,cost1','forecast(o.turn,cfg_.castle1_target_turn,cost1','castle1 forecast')
    s=once(s,'forecast(o.turn,250,cost2','forecast(o.turn,cfg_.castle2_target_turn,cost2','castle2 forecast')
    s=once(s,'if(o.turn>150&&castle_build_[0]<0)','if(o.turn>cfg_.castle1_target_turn&&castle_build_[0]<0)','castle1 miss')
    s=once(s,'else if(o.turn>250&&castle_build_[1]<0)','else if(o.turn>cfg_.castle2_target_turn&&castle_build_[1]<0)','castle2 miss')
    s=once(s,'bool late_c1_pending=castles_.c1>=0&&castle_state_[0]!=CastleState::BUILT&&o.turn>150;bool late_c2_pending=castles_.c2>=0&&castle_state_[1]!=CastleState::BUILT&&castle_state_[0]==CastleState::BUILT&&o.turn>250;',
           'bool late_c1_pending=castles_.c1>=0&&castle_state_[0]!=CastleState::BUILT&&o.turn>cfg_.castle1_target_turn;bool late_c2_pending=castles_.c2>=0&&castle_state_[1]!=CastleState::BUILT&&castle_state_[0]==CastleState::BUILT&&o.turn>cfg_.castle2_target_turn;','late castle turns')
    s=once(s,'o.my_army>=live_castle_cost(o,site,w_)+30','o.my_army>=live_castle_cost(o,site,w_)+cfg_.late_castle_army_margin','castle margin')
    s=once(s,'bool late_muster=picker_enabled_&&enemy_general>=0&&!immediate&&!late_castle_pending&&o.turn>=300&&production_!=ProductionState::SEVERE_DEFICIT&&(o.opp_army<=0||o.my_army>=o.opp_army+80||o.my_army*5>=o.opp_army*6);',
           'bool late_muster=picker_enabled_&&enemy_general>=0&&!immediate&&!late_castle_pending&&o.turn>=cfg_.muster_start_turn&&production_!=ProductionState::SEVERE_DEFICIT&&(o.opp_army<=0||o.my_army>=o.opp_army+cfg_.muster_army_margin||o.my_army*cfg_.muster_ratio_num>=o.opp_army*cfg_.muster_ratio_den);','late muster gate')
    s=once(s,'int launch_need=std::max({90,eg_army*3+20,std::max(0,o.opp_army/2)});bool late_finish=o.turn>=900&&o.army[anchor]>=std::max(70,eg_army*2+15);',
           'int launch_need=std::max({cfg_.muster_launch_base,int(eg_army*cfg_.muster_enemy_mult)+cfg_.muster_enemy_bonus,std::max(0,o.opp_army/std::max(1,cfg_.muster_opp_divisor))});bool late_finish=o.turn>=cfg_.late_finish_turn&&o.army[anchor]>=std::max(cfg_.late_finish_base,int(eg_army*cfg_.late_finish_enemy_mult)+cfg_.late_finish_enemy_bonus);','muster launch')
    s=once(s,'bool mature=o.turn>=150||o.my_land*100>=n_*35;bool not_behind=o.opp_land==0||o.my_land*5>=o.opp_land*4;bool growing=growth25>=.08||growth50>=.06||o.my_land*100>=n_*45;bool few_neutrals=useful_neutrals<=3;bool needs_concentration=top3_share<.55&&largest_owned<best_mass;',
           'bool mature=o.turn>=cfg_.picker_mature_turn||o.my_land*100>=n_*cfg_.picker_mature_land_pct;bool not_behind=o.opp_land==0||o.my_land*cfg_.picker_not_behind_num>=o.opp_land*cfg_.picker_not_behind_den;bool growing=growth25>=cfg_.picker_growth25||growth50>=cfg_.picker_growth50||o.my_land*100>=n_*cfg_.picker_growth_land_pct;bool few_neutrals=useful_neutrals<=3;bool needs_concentration=top3_share<cfg_.picker_top3_share_max&&largest_owned<best_mass;','picker gates')
    old_share='std::array<double,5>share{{0,confirmed_war?.30:.12,production_==ProductionState::SEVERE_DEFICIT?.62:production_==ProductionState::SOFT_DEFICIT?.45:.35,!enemy_seen?.20:.08,confirmed_war?.22:.15}};'
    new_share='double healthy_share=(!enemy_seen&&cfg_.precontact_expansion_until>=0&&o.turn<=cfg_.precontact_expansion_until)?cfg_.expansion_share_precontact:cfg_.expansion_share_healthy;std::array<double,5>share{{0,confirmed_war?cfg_.war_share_contact:cfg_.war_share_peace,production_==ProductionState::SEVERE_DEFICIT?cfg_.expansion_share_severe:production_==ProductionState::SOFT_DEFICIT?cfg_.expansion_share_soft:healthy_share,!enemy_seen?cfg_.search_share_unseen:cfg_.search_share_seen,confirmed_war?cfg_.free_share_war:cfg_.free_share_peace}};'
    s=once(s,old_share,new_share,'strategic shares')
    main_path.write_text(s)
    (main_path.parent/'evolution4_genome.hpp').write_text(HEADER)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('main_cpp',type=Path); args=ap.parse_args(); transform(args.main_cpp)
if __name__=='__main__': main()
