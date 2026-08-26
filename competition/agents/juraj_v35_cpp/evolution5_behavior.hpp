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
 bool enabled_=false;
 std::string entry_,state_;
 std::unordered_map<std::string,Evo5NodeRuntime> nodes_;
 long transitions_=0,filtered_=0;
 static std::vector<std::string> split(const std::string&s,char d){std::vector<std::string>o;size_t p=0;while(p<=s.size()){size_t q=s.find(d,p);o.push_back(s.substr(p,q==std::string::npos?s.size()-p:q-p));if(q==std::string::npos)break;p=q+1;}return o;}
 bool condition(const std::string&c,bool contact,bool enemy_seen,bool ahead,bool behind,bool late,bool threat)const{return c=="always"||(c=="contact"&&contact)||(c=="no_contact"&&!contact)||(c=="ahead"&&ahead)||(c=="behind"&&behind)||(c=="late"&&late)||(c=="threat"&&threat)||(c=="enemy_seen"&&enemy_seen);}
 bool has(const char*m)const{auto it=nodes_.find(state_);return it!=nodes_.end()&&it->second.modules.count(m);}
 bool any(std::initializer_list<const char*>ms)const{for(auto*m:ms)if(has(m))return true;return false;}
 public:
 void load(){
  const char*mode=std::getenv("EVO5_GRAPH_MODE");const char*spec=std::getenv("EVO5_GRAPH_RUNTIME");const char*entry=std::getenv("EVO5_GRAPH_ENTRY");
  enabled_=mode&&std::string(mode)=="evolved"&&spec&&*spec;if(!enabled_)return;entry_=entry&&*entry?entry:"OPENING";state_=entry_;
  for(const auto&raw:split(spec,'|')){auto f=split(raw,'~');if(f.size()<2||f[0].empty())continue;Evo5NodeRuntime n;for(const auto&m:split(f[1],','))if(!m.empty())n.modules.insert(m);if(f.size()>=3)for(const auto&t:split(f[2],',')){auto p=t.find('>');if(p!=std::string::npos)n.transitions.push_back({t.substr(0,p),t.substr(p+1)});}nodes_[f[0]]=std::move(n);}
  if(!nodes_.count(state_)&&!nodes_.empty())state_=nodes_.begin()->first;
 }
 void update(int turn,bool contact,bool enemy_seen,bool ahead,bool behind,bool threat){
  if(!enabled_)return;auto it=nodes_.find(state_);if(it==nodes_.end())return;bool late=turn>=650;
  for(const auto&t:it->second.transitions)if(condition(t.first,contact,enemy_seen,ahead,behind,late,threat)&&nodes_.count(t.second)){if(t.second!=state_){state_=t.second;++transitions_;}break;}
 }
 bool allow(const v35::Candidate&q){
  if(!enabled_)return true;
  if(q.reason==v35::Reason::TERMINAL_CAPTURE||q.reason==v35::Reason::GENERAL_EMERGENCY)return true;
  bool ok=true;
  if(q.kind==2||q.reason==v35::Reason::CASTLE_DEADLINE)ok=has("BUILD_CASTLE");
  else if(q.reason==v35::Reason::EDGE_PICKER&&q.role==v35::PacketRole::ATTACK)ok=has("MUSTER")||any({"ATTACK","HUNT_GENERAL","FINISH"});
  else if(q.role==v35::PacketRole::EDGE_PICKER)ok=has("PICK")||has("LOGISTICS");
  else if(q.action_class==v35::ActionClass::EXPANSION)ok=has("EXPAND");
  else if(q.action_class==v35::ActionClass::SEARCH)ok=has("SCOUT")||has("HUNT_GENERAL");
  else if(q.reason==v35::Reason::REAR_EVACUATION)ok=any({"RECOVER","LOGISTICS","CONSOLIDATE"});
  else if(q.role==v35::PacketRole::GENERAL_DEFENSE||q.role==v35::PacketRole::REACTION)ok=any({"DEFEND_GENERAL","INTERCEPT"});
  else if(q.action_class==v35::ActionClass::OFFENSE||q.role==v35::PacketRole::ATTACK||q.role==v35::PacketRole::COUNTERATTACK)ok=any({"ATTACK","HUNT_GENERAL","FINISH","MUSTER"});
  else if(q.action_class==v35::ActionClass::LOGISTICS)ok=any({"LOGISTICS","CONSOLIDATE","RECOVER","PICK","MUSTER"});
  if(!ok)++filtered_;return ok;
 }
 void report()const{std::fprintf(stderr,"[e5_behavior] enabled=%d state=%s nodes=%zu transitions=%ld filtered=%ld\n",enabled_?1:0,state_.c_str(),nodes_.size(),transitions_,filtered_);}
};
