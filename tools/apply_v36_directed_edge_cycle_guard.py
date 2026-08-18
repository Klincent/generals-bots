from pathlib import Path

root = Path(__file__).resolve().parents[1]
core = root / "competition/agents/juraj_v35_cpp/core.hpp"
main = root / "competition/agents/juraj_v35_cpp/main.cpp"
test = root / "competition/agents/juraj_v35_cpp/test_core.cpp"
stall = root / "competition/agents/juraj_v35_cpp/test_stall_hardening.cpp"


def replace_once(path: Path, old: str, new: str, label: str):
    text = path.read_text()
    if old not in text:
        raise SystemExit(f"missing expected text for {label}")
    text = text.replace(old, new, 1)
    path.write_text(text)
    print(f"{label}: applied")


old_route = '''inline bool route_allowed(const Packet&p,int dest,int new_distance,int old_distance,int event_version,Reason reason){bool emergency=reason==Reason::GENERAL_EMERGENCY||reason==Reason::TERMINAL_CAPTURE;bool mobile=p.role==PacketRole::EXPANSION||p.role==PacketRole::SEARCH||p.role==PacketRole::FRONT||p.role==PacketRole::ATTACK||p.role==PacketRole::COUNTERATTACK;if(!emergency&&mobile&&std::find(p.path.begin(),p.path.end(),dest)!=p.path.end())return false;bool changed=event_version!=p.event_version&&reason!=Reason::NONE;if(!emergency&&!changed&&new_distance>old_distance)return false;if(!emergency&&!changed&&p.path.size()>=2&&dest==p.path[p.path.size()-2])return false;if(!emergency&&!changed&&p.path.size()>=3&&dest==p.path[p.path.size()-3])return false;if(!emergency&&!changed&&p.path.size()>=4&&dest==p.path[p.path.size()-4])return false;return true;}'''
new_route = '''inline bool route_allowed(const Packet&p,int dest,int new_distance,int old_distance,int event_version,Reason reason){bool emergency=reason==Reason::GENERAL_EMERGENCY||reason==Reason::TERMINAL_CAPTURE;if(emergency)return true;int seen_edges=0;for(int i=(int)p.path.size()-1;i>=1&&seen_edges<4;--i,++seen_edges)if(p.path[i-1]==p.cell&&p.path[i]==dest)return false;bool recent_return=false;int seen_cells=0;for(auto it=p.path.rbegin();it!=p.path.rend()&&seen_cells<4;++it,++seen_cells)if(*it==dest){recent_return=true;break;}bool changed=event_version!=p.event_version&&reason!=Reason::NONE;if(!changed&&new_distance>old_distance&&!recent_return)return false;return true;}'''
replace_once(core, old_route, new_route, "directed-edge repeat guard")

replace_once(main,
    'p.path.push_back(p.cell);while(p.path.size()>32)p.path.pop_front();',
    'p.path.push_back(p.cell);while(p.path.size()>5)p.path.pop_front();',
    'packet history bounded to four moves')

old_hist = '''bool history_cycle(const Candidate&q)const{if(q.from<0||q.to<0)return false;int seen=0;for(auto it=actions_.rbegin();it!=actions_.rend()&&seen<4;++it,++seen)if((it->from==q.to&&it->to==q.from)||(it->from==q.from&&it->to==q.to))return true;return false;}'''
new_hist = '''bool history_cycle(const Candidate&q)const{if(q.from<0||q.to<0)return false;if(q.reason==Reason::GENERAL_EMERGENCY||q.reason==Reason::TERMINAL_CAPTURE)return false;if(const Packet*p=packet_for(q.from)){int seen_edges=0;for(int i=(int)p->path.size()-1;i>=1&&seen_edges<4;--i,++seen_edges)if(p->path[i-1]==q.from&&p->path[i]==q.to)return true;}int seen=0;for(auto it=actions_.rbegin();it!=actions_.rend()&&seen<4;++it,++seen)if(it->from==q.from&&it->to==q.to)return true;return false;}'''
replace_once(main, old_hist, new_hist, "cycle guard blocks only repeated directed moves")

old_tests = ''' // 7 A-B-A and 8 A-B-C-B loops are hard rejected.\n Packet p;p.cell=2;p.target=8;p.event_version=1;p.path={0,1,2};assert(!route_allowed(p,1,2,2,1,Reason::NONE));p.path={0,1,2,3};assert(!route_allowed(p,1,2,2,1,Reason::NONE));\n // 9 noncritical event changes do NOT reopen visited cells.\n p.role=PacketRole::SEARCH;assert(!route_allowed(p,1,2,2,2,Reason::SEARCH_PROGRESS));\n // 10 a real general emergency may still override the tabu.\n assert(route_allowed(p,2,3,2,2,Reason::GENERAL_EMERGENCY));'''
new_tests = ''' // 7 A-B-A is allowed: one backtrack may be necessary to leave a dead end.\n Packet p;p.target=8;p.event_version=1;p.cell=1;p.path={0,1};assert(route_allowed(p,0,3,2,1,Reason::NONE));\n // 8 A-B-A-B is blocked: after returning to A, the same directed A->B edge may not repeat.\n p.cell=0;p.path={0,1,0};assert(!route_allowed(p,1,2,2,1,Reason::NONE));\n // 9 A-B-C-B is allowed, but 10 the next B->C is blocked (B-C-B-C).\n p.cell=2;p.path={0,1,2};assert(route_allowed(p,1,3,2,1,Reason::NONE));p.cell=1;p.path={0,1,2,1};assert(!route_allowed(p,2,2,2,1,Reason::NONE));\n // 11 A-B-C-D-A is allowed, but 12 then A->B must change direction (A-B-C-D-A-B is blocked).\n p.cell=3;p.path={0,1,2,3};assert(route_allowed(p,0,4,3,1,Reason::NONE));p.cell=0;p.path={0,1,2,3,0};assert(!route_allowed(p,1,2,2,1,Reason::NONE));\n // 13 once an edge falls outside the four-move history it can be used again.\n p.cell=0;p.path={1,2,3,4,0};assert(route_allowed(p,1,1,2,1,Reason::NONE));\n // 14 a real general emergency may override the short cycle guard.\n p.cell=0;p.path={0,1,0};assert(route_allowed(p,1,3,2,1,Reason::GENERAL_EMERGENCY));'''
replace_once(test, old_tests, new_tests, "core regressions for exact cycle semantics")
replace_once(test,
    'std::cout<<"v35 core: 21 behavioral checks passed\\n";',
    'std::cout<<"v35 core: 27 behavioral checks passed\\n";',
    'core test count')

old_stall = '''int main(){Agent a(0,21,21);auto o=stalled();int initial=o.my_land,prev_from=-1,prev_to=-1,moves=0;for(int i=0;i<8&&o.my_land==initial;++i){auto q=a.decide(o);assert(q.kind==0);int f=src(q),t=dst(q);if(prev_from>=0)assert(!(f==prev_to&&t==prev_from));prev_from=f;prev_to=t;++moves;apply(o,q);}assert(moves>0);assert(o.my_land>initial);std::cout<<"v36 low-land breakout and anti-zigzag scenarios passed\\n";}'''
new_stall = '''int main(){Agent a(0,21,21);auto o=stalled();int initial=o.my_land,moves=0;std::deque<std::pair<int,int>>recent;for(int i=0;i<8&&o.my_land==initial;++i){auto q=a.decide(o);assert(q.kind==0);int f=src(q),t=dst(q);for(auto e:recent)assert(!(e.first==f&&e.second==t));recent.push_back({f,t});while(recent.size()>4)recent.pop_front();++moves;apply(o,q);}assert(moves>0);assert(o.my_land>initial);std::cout<<"v36 low-land breakout and directed-edge cycle scenarios passed\\n";}'''
replace_once(stall, old_stall, new_stall, "stall regression allows one-step backtrack")

print("V3.6 directed-edge cycle guard patch complete")
