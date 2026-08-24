#pragma once
#include <algorithm>
#include <cstdlib>
#include <cstring>
#include <string>

static inline int evo4_int(const char* n,int d,int lo,int hi){const char*e=std::getenv(n);if(!e)return d;long v=std::strtol(e,nullptr,10);return std::max(lo,std::min(hi,(int)v));}
static inline double evo4_double(const char* n,double d,double lo,double hi){const char*e=std::getenv(n);if(!e)return d;double v=std::strtod(e,nullptr);return std::max(lo,std::min(hi,v));}
static inline bool evo4_bool(const char* n,bool d){const char*e=std::getenv(n);if(!e)return d;return std::strcmp(e,"0")!=0&&std::strcmp(e,"false")!=0&&std::strcmp(e,"FALSE")!=0;}
static inline std::string evo4_string(const char* n,const char* d){const char*e=std::getenv(n);return e?std::string(e):std::string(d);}

struct GenomeConfig {
 bool doomguard_enabled=false,picker_enabled=true;
 int edge_picker_threshold=14,muster_threshold=7,general_reserve_base=7,general_reserve_opp_divisor=12,adjacent_reserve_base=1;
 double picker_min_efficiency=2,production_recover_slope=0.103714329168;
 int production_recover_gap=8,production_severe_gap=14,production_soft_gap=12,castle1_target_turn=150,castle2_target_turn=250;
 double war_share_contact=0.3,war_share_peace=0.111691057309,expansion_share_severe=0.611021735,expansion_share_soft=0.509215308076,expansion_share_healthy=0.237151161475;
 int precontact_expansion_until=275; double expansion_share_precontact=0.4,search_share_unseen=0.24067012355,search_share_seen=0.0994757623763,free_share_war=0.240527947191,free_share_peace=0.15;
 int expansion_wait_limit=5,muster_start_turn=300,muster_army_margin=80,muster_ratio_num=10,muster_ratio_den=11,muster_launch_base=90;
 double muster_enemy_mult=3; int muster_enemy_bonus=10,muster_opp_divisor=3,late_finish_turn=850,late_finish_base=70;
 double late_finish_enemy_mult=1.87106079983; int late_finish_enemy_bonus=20,picker_mature_turn=190,picker_mature_land_pct=45,picker_not_behind_num=5,picker_not_behind_den=2;
 double picker_growth25=0.08,picker_growth50=0.06; int picker_growth_land_pct=50; double picker_top3_share_max=0.619095421366; int late_castle_army_margin=40;
 std::string muster_topology="triple",muster_anchor_policy="largest",chunk_transfer_policy="full";
 std::string logistics_route_policy="interior",defense_policy="block_first",fallback_policy="balanced",picker_start_policy="margin";
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
  muster_topology=evo4_string("EVO4_MUSTER_TOPOLOGY",muster_topology.c_str()); muster_anchor_policy=evo4_string("EVO4_MUSTER_ANCHOR_POLICY",muster_anchor_policy.c_str()); chunk_transfer_policy=evo4_string("EVO4_CHUNK_TRANSFER_POLICY",chunk_transfer_policy.c_str());
  logistics_route_policy=evo4_string("EVO4_LOGISTICS_ROUTE_POLICY",logistics_route_policy.c_str()); defense_policy=evo4_string("EVO4_DEFENSE_POLICY",defense_policy.c_str()); fallback_policy=evo4_string("EVO4_FALLBACK_POLICY",fallback_policy.c_str()); picker_start_policy=evo4_string("EVO4_PICKER_START_POLICY",picker_start_policy.c_str());
 }
};
