from pathlib import Path

root = Path(__file__).resolve().parents[1]
core = root / "competition/agents/juraj_v35_cpp/core.hpp"
main = root / "competition/agents/juraj_v35_cpp/main.cpp"
test = root / "competition/agents/juraj_v35_cpp/test_core.cpp"

def replace_once(path: Path, old: str, new: str, label: str):
    text = path.read_text()
    if old not in text:
        raise SystemExit(f"missing expected text for {label}")
    text = text.replace(old, new, 1)
    path.write_text(text)
    print(f"{label}: applied")

old_route = '''inline bool route_allowed(const Packet&p,int dest,int new_distance,int old_distance,int event_version,Reason reason){bool emergency=reason==Reason::GENERAL_EMERGENCY||reason==Reason::TERMINAL_CAPTURE;bool mobile=p.role==PacketRole::EXPANSION||p.role==PacketRole::SEARCH||p.role==PacketRole::FRONT||p.role==PacketRole::ATTACK||p.role==PacketRole::COUNTERATTACK;if(!emergency&&mobile&&std::find(p.path.begin(),p.path.end(),dest)!=p.path.end())return false;bool changed=event_version!=p.event_version&&reason!=Reason::NONE;if(!emergency&&!changed&&new_distance>old_distance)return false;if(!emergency&&!changed&&p.path.size()>=2&&dest==p.path[p.path.size()-2])return false;if(!emergency&&!changed&&p.path.size()>=3&&dest==p.path[p.path.size()-3])return false;if(!emergency&&!changed&&p.path.size()>=4&&dest==p.path[p.path.size()-4])return false;return true;}'''
new_route = '''inline bool route_allowed(const Packet&p,int dest,int new_distance,int old_distance,int event_version,Reason reason){bool emergency=reason==Reason::GENERAL_EMERGENCY||reason==Reason::TERMINAL_CAPTURE;if(!emergency){int seen=0;for(auto it=p.path.rbegin();it!=p.path.rend()&&seen<4;++it,++seen)if(*it==dest)return false;}bool changed=event_version!=p.event_version&&reason!=Reason::NONE;if(!emergency&&!changed&&new_distance>old_distance)return false;return true;}'''
replace_once(core, old_route, new_route, "short packet history only")

replace_once(main,
    'p.path.push_back(p.cell);while(p.path.size()>32)p.path.pop_front();',
    'p.path.push_back(p.cell);while(p.path.size()>5)p.path.pop_front();',
    'packet history bounded to five cells')

old_hist = '''bool history_cycle(const Candidate&q)const{if(q.from<0||q.to<0)return false;int seen=0;for(auto it=actions_.rbegin();it!=actions_.rend()&&seen<4;++it,++seen)if((it->from==q.to&&it->to==q.from)||(it->from==q.from&&it->to==q.to))return true;return false;}'''
new_hist = '''bool history_cycle(const Candidate&q)const{if(q.from<0||q.to<0)return false;if(q.reason==Reason::GENERAL_EMERGENCY||q.reason==Reason::TERMINAL_CAPTURE)return false;if(const Packet*p=packet_for(q.from)){int seen=0;for(auto it=p->path.rbegin();it!=p->path.rend()&&seen<4;++it,++seen)if(*it==q.to)return true;}if(!actions_.empty()&&actions_.back().from==q.to&&actions_.back().to==q.from)return true;return false;}'''
replace_once(main, old_hist, new_hist, "cycle guard uses only recent packet history")

old_tests = ''' // 7 A-B-A and 8 A-B-C-B loops are hard rejected.\n Packet p;p.cell=2;p.target=8;p.event_version=1;p.path={0,1,2};assert(!route_allowed(p,1,2,2,1,Reason::NONE));p.path={0,1,2,3};assert(!route_allowed(p,1,2,2,1,Reason::NONE));\n // 9 noncritical event changes do NOT reopen visited cells.\n p.role=PacketRole::SEARCH;assert(!route_allowed(p,1,2,2,2,Reason::SEARCH_PROGRESS));\n // 10 a real general emergency may still override the tabu.\n assert(route_allowed(p,2,3,2,2,Reason::GENERAL_EMERGENCY));'''
new_tests = ''' // 7 A-B-A and 8 A-B-C-B loops are hard rejected by short history.\n Packet p;p.cell=2;p.target=8;p.event_version=1;p.path={0,1,2};assert(!route_allowed(p,1,2,2,1,Reason::NONE));p.path={0,1,2,3};assert(!route_allowed(p,1,2,2,1,Reason::NONE));\n // 9 noncritical event changes do NOT reopen one of the last four cells.\n p.role=PacketRole::SEARCH;assert(!route_allowed(p,1,2,2,2,Reason::SEARCH_PROGRESS));\n // 10 older revisits are allowed again: there is no lifetime/permanent tabu.\n p.path={0,1,2,3,4};assert(route_allowed(p,0,1,2,1,Reason::NONE));\n // 11 a real general emergency may still override the short-cycle guard.\n assert(route_allowed(p,3,3,2,2,Reason::GENERAL_EMERGENCY));'''
replace_once(test, old_tests, new_tests, "core regression for short-only revisit prevention")

replace_once(test,
    'std::cout<<"v35 core: 21 behavioral checks passed\\n";',
    'std::cout<<"v35 core: 22 behavioral checks passed\\n";',
    'core test count')

print("V3.6 short-cycle-only patch complete")
