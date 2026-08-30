#pragma once
#include <algorithm>
#include <cstdio>
#include <cstdlib>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

struct Evo5NodeRuntime {
 std::unordered_set<std::string> modules;
 std::vector<std::pair<std::string,std::string>> transitions;
};

class Evo5Behavior {
 enum class TacticalMode {EXPAND,DEFEND,MUSTER,ATTACK};
 bool enabled_=false,contact_=false,enemy_seen_=false,threat_=false,anti_rush_=false;
 std::string entry_,state_;
 TacticalMode mode_=TacticalMode::EXPAND;
 std::unordered_map<std::string,Evo5NodeRuntime> nodes_;
 long transitions_=0,filtered_=0,tuned_=0,anti_rush_entries_=0,mode_switches_=0;
 static std::vector<std::string> split(const std::string&s,char d){std::vector<std::string>o;size_t p=0;while(p<=s.size()){size_t q=s.find(d,p);o.push_back(s.substr(p,q==std::string::npos?s.size()-p:q-p));if(q==std::string::npos)break;p=q+1;}return o;}
 static const char* mode_name(TacticalMode m){switch(m){case TacticalMode::EXPAND:return "EXPAND";case TacticalMode::DEFEND:return "DEFEND";case TacticalMode::MUSTER:return "MUSTER";default:return "ATTACK";}}
 bool condition(const std::string&c,bool contact,bool enemy_seen,bool ahead,bool behind,bool late,bool threat)const{return c=="always"||(c=="contact"&&contact)||(c=="no_contact"&&!contact)||(c=="ahead"&&ahead)||(c=="behind"&&behind)||(c=="late"&&late)||(c=="threat"&&threat)||(c=="enemy_seen"&&enemy_seen);}
 bool has(const char*m)const{auto it=nodes_.find(state_);return it!=nodes_.end()&&it->second.modules.count(m);}
 bool any(std::initializer_list<const char*>ms)const{for(auto*m:ms)if(has(m))return true;return false;}
 void set_mode(TacticalMode m){if(mode_!=m){mode_=m;++mode_switches_;}}
 public:
 void load(){
  const char*mode=std::getenv("EVO5_GRAPH_MODE");const char*spec=std::getenv("EVO5_GRAPH_RUNTIME");const char*entry=std::getenv("EVO5_GRAPH_ENTRY");
  enabled_=mode&&std::string(mode)=="evolved"&&spec&&*spec;
  if(!enabled_)return;
  entry_=entry&&*entry?entry:"OPENING";state_=entry_;
  for(const auto&raw:split(spec,'|')){auto f=split(raw,'~');if(f.size()<2||f[0].empty())continue;Evo5NodeRuntime n;for(const auto&m:split(f[1],','))if(!m.empty())n.modules.insert(m);if(f.size()>=3)for(const auto&t:split(f[2],',')){auto p=t.find('>');if(p!=std::string::npos)n.transitions.push_back({t.substr(0,p),t.substr(p+1)});}nodes_[f[0]]=std::move(n);}
  if(!nodes_.count(state_)&&!nodes_.empty())state_=nodes_.begin()->first;
 }
 void update(int turn,bool contact,bool enemy_seen,bool ahead,bool behind,bool threat,int my_land,int opp_land,int my_army,int opp_army){
  if(!enabled_)return;
  contact_=contact;enemy_seen_=enemy_seen;threat_=threat;
  const bool rush_signal=threat || (turn<330 && contact && opp_army>my_army*115/100) || (turn<260 && opp_land>my_land+8);
  const bool rush_release=!threat && (!contact || my_army*100>=opp_army*105) && my_land+3>=opp_land;
  if(rush_signal&&!anti_rush_){anti_rush_=true;++anti_rush_entries_;}
  else if(anti_rush_&&rush_release)anti_rush_=false;
  TacticalMode wanted=TacticalMode::EXPAND;
  if(anti_rush_||threat||behind)wanted=TacticalMode::DEFEND;
  else if(contact && (ahead || my_army*100>=opp_army*112))wanted=TacticalMode::ATTACK;
  else if(contact || enemy_seen || turn>=185)wanted=TacticalMode::MUSTER;
  set_mode(wanted);
  auto it=nodes_.find(state_);if(it==nodes_.end())return;
  bool late=turn>=650;
  for(const auto&t:it->second.transitions)if(condition(t.first,contact,enemy_seen,ahead,behind,late,threat)&&nodes_.count(t.second)){if(t.second!=state_){state_=t.second;++transitions_;}break;}
 }
 bool allow(const v35::Candidate&q){
  if(!enabled_)return true;
  if(q.reason==v35::Reason::TERMINAL_CAPTURE||q.reason==v35::Reason::GENERAL_EMERGENCY)return true;
  bool ok=true;
  if(q.kind==2||q.reason==v35::Reason::CASTLE_DEADLINE)ok=has("BUILD_CASTLE");
  else if(q.reason==v35::Reason::EDGE_PICKER&&q.role==v35::PacketRole::ATTACK)ok=has("MUSTER")||any({"ATTACK","HUNT_GENERAL","FINISH"});
  else if(q.role==v35::PacketRole::EDGE_PICKER)ok=has("PICK")||has("LOGISTICS")||mode_==TacticalMode::MUSTER;
  else if(q.action_class==v35::ActionClass::EXPANSION)ok=has("EXPAND")||mode_==TacticalMode::EXPAND;
  else if(q.action_class==v35::ActionClass::SEARCH)ok=has("SCOUT")||has("HUNT_GENERAL")||mode_==TacticalMode::ATTACK;
  else if(q.reason==v35::Reason::REAR_EVACUATION)ok=any({"RECOVER","LOGISTICS","CONSOLIDATE","MUSTER"})||mode_==TacticalMode::MUSTER;
  else if(q.role==v35::PacketRole::GENERAL_DEFENSE||q.role==v35::PacketRole::REACTION)ok=any({"DEFEND_GENERAL","INTERCEPT"})||mode_==TacticalMode::DEFEND;
  else if(q.action_class==v35::ActionClass::OFFENSE||q.role==v35::PacketRole::ATTACK||q.role==v35::PacketRole::COUNTERATTACK)ok=any({"ATTACK","HUNT_GENERAL","FINISH","MUSTER"})||mode_==TacticalMode::ATTACK;
  else if(q.action_class==v35::ActionClass::LOGISTICS)ok=any({"LOGISTICS","CONSOLIDATE","RECOVER","PICK","MUSTER"})||mode_==TacticalMode::MUSTER;
  if(!ok)++filtered_;
  return ok;
 }
 void tune(v35::Candidate&q,int turn){
  if(!enabled_)return;
  bool changed=false;
  auto boost=[&](int tier,double utility){int nt=std::min(q.tier,tier);if(nt!=q.tier){q.tier=nt;changed=true;}if(utility!=0){q.utility+=utility;changed=true;}};
  auto delay=[&](int tiers,double utility){q.tier=std::min(9,q.tier+tiers);q.utility-=utility;changed=true;};
  if(q.reason==v35::Reason::TERMINAL_CAPTURE||q.reason==v35::Reason::GENERAL_EMERGENCY){boost(0,250);if(changed)++tuned_;return;}
  if(mode_==TacticalMode::DEFEND){
   if(q.role==v35::PacketRole::GENERAL_DEFENSE||q.role==v35::PacketRole::REACTION||q.role==v35::PacketRole::COUNTERATTACK)boost(1,anti_rush_?180:120);
   else if(q.reason==v35::Reason::REAR_EVACUATION)boost(2,85);
   else if(q.action_class==v35::ActionClass::EXPANSION||q.action_class==v35::ActionClass::SEARCH)delay(2,50);
   else if(q.role==v35::PacketRole::ATTACK&&!threat_)delay(1,25);
  }else if(mode_==TacticalMode::MUSTER){
   if(q.reason==v35::Reason::REAR_EVACUATION||q.role==v35::PacketRole::FREE_SURPLUS_RELOCATION)boost(2,105);
   else if(q.role==v35::PacketRole::EDGE_PICKER)boost(2,95);
   else if(q.action_class==v35::ActionClass::LOGISTICS)boost(3,55);
   else if(q.action_class==v35::ActionClass::EXPANSION&&turn>=210)delay(1,25);
   else if(q.role==v35::PacketRole::ATTACK&&contact_)boost(3,35);
  }else if(mode_==TacticalMode::ATTACK){
   if(q.role==v35::PacketRole::ATTACK||q.role==v35::PacketRole::COUNTERATTACK||q.action_class==v35::ActionClass::OFFENSE)boost(1,140);
   else if(q.action_class==v35::ActionClass::SEARCH&&enemy_seen_)boost(2,85);
   else if(q.reason==v35::Reason::REAR_EVACUATION||q.role==v35::PacketRole::FREE_SURPLUS_RELOCATION)boost(2,75);
   else if(q.action_class==v35::ActionClass::EXPANSION)delay(2,55);
  }else{
   if(q.action_class==v35::ActionClass::EXPANSION)boost(2,70);
   else if(q.role==v35::PacketRole::EDGE_PICKER&&turn<180)delay(1,20);
  }
  if(changed)++tuned_;
 }
 void report()const{std::fprintf(stderr,"[e5_behavior_v2] enabled=%d state=%s mode=%s anti_rush=%d nodes=%zu transitions=%ld mode_switches=%ld anti_rush_entries=%ld filtered=%ld tuned=%ld\n",enabled_?1:0,state_.c_str(),mode_name(mode_),anti_rush_?1:0,nodes_.size(),transitions_,mode_switches_,anti_rush_entries_,filtered_,tuned_);}
};
