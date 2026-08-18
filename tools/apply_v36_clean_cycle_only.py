from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / 'competition/agents/juraj_v35_cpp/core.hpp'
MAIN = ROOT / 'competition/agents/juraj_v35_cpp/main.cpp'
TEST = ROOT / 'competition/agents/juraj_v35_cpp/test_core.cpp'

def replace_once(text, old, new, label):
    if text.count(old) != 1:
        raise SystemExit(f'{label}: expected exactly one match, found {text.count(old)}')
    print(f'{label}: applied')
    return text.replace(old, new, 1)

core = CORE.read_text()
old_route = 'inline bool route_allowed(const Packet&p,int dest,int new_distance,int old_distance,int event_version,Reason reason){bool changed=event_version!=p.event_version&&reason!=Reason::NONE;if(!changed&&new_distance>old_distance)return false;if(!changed&&p.path.size()>=2&&dest==p.path[p.path.size()-2])return false;if(!changed&&p.path.size()>=3&&dest==p.path[p.path.size()-3])return false;if(!changed&&p.path.size()>=4&&dest==p.path[p.path.size()-4])return false;return true;}'
new_route = 'inline bool route_allowed(const Packet&p,int dest,int new_distance,int old_distance,int event_version,Reason reason){bool changed=event_version!=p.event_version&&reason!=Reason::NONE;int seen_edges=0;for(int i=(int)p.path.size()-1;i>=1&&seen_edges<4;--i,++seen_edges)if(p.path[i-1]==p.cell&&p.path[i]==dest)return false;bool recent_return=false;int seen_cells=0;for(auto it=p.path.rbegin();it!=p.path.rend()&&seen_cells<4;++it,++seen_cells)if(*it==dest){recent_return=true;break;}if(!changed&&new_distance>old_distance&&!recent_return)return false;return true;}'
core = replace_once(core, old_route, new_route, 'core directed-edge guard')
CORE.write_text(core)

main = MAIN.read_text()
main = replace_once(main, 'while(p.path.size()>12)p.path.pop_front();', 'while(p.path.size()>5)p.path.pop_front();', 'packet history = 4 moves')
old_hist = 'bool history_cycle(const Candidate&q)const{if(q.from<0||q.to<0)return false;for(auto it=actions_.rbegin();it!=actions_.rend();++it){if(it->event!=event_)break;if(it->from==q.to&&it->to==q.from)return true;}return false;}'
new_hist = 'bool history_cycle(const Candidate&q)const{if(q.from<0||q.to<0)return false;int seen=0;for(auto it=actions_.rbegin();it!=actions_.rend()&&seen<4;++it,++seen)if(it->from==q.from&&it->to==q.to)return true;return false;}'
main = replace_once(main, old_hist, new_hist, 'global directed-edge 4-move guard')
main = replace_once(main, 'while(actions_.size()>12)actions_.pop_front();', 'while(actions_.size()>4)actions_.pop_front();', 'global history = 4 moves')
MAIN.write_text(main)

test = TEST.read_text()
old_tests = ''' // 7 A-B-A and 8 A-B-C-B loops are hard rejected.\n Packet p;p.cell=2;p.target=8;p.event_version=1;p.path={0,1,2};assert(!route_allowed(p,1,2,2,1,Reason::NONE));p.path={0,1,2,3};assert(!route_allowed(p,1,2,2,1,Reason::NONE));\n // 9 a real strategic event permits reversal.\n assert(route_allowed(p,2,3,2,2,Reason::GENERAL_EMERGENCY));'''
new_tests = ''' // 7 A-B-A is allowed: a one-step backtrack can be necessary in a dead end.\n Packet p;p.target=8;p.event_version=1;p.cell=1;p.path={0,1};assert(route_allowed(p,0,3,2,1,Reason::NONE));\n // 8 A-B-A-B is blocked because directed edge A->B repeats inside four-move history.\n p.cell=0;p.path={0,1,0};assert(!route_allowed(p,1,2,3,1,Reason::NONE));\n // 9 A-B-C-B is allowed, but 10 the following B->C is blocked as a repeated directed edge.\n p.cell=2;p.path={0,1,2};assert(route_allowed(p,1,3,2,1,Reason::NONE));p.cell=1;p.path={0,1,2,1};assert(!route_allowed(p,2,2,3,1,Reason::NONE));\n // 11 A-B-C-D-A is allowed, but 12 the following A->B repeats a still-recent directed edge.\n p.cell=3;p.path={0,1,2,3};assert(route_allowed(p,0,3,2,1,Reason::NONE));p.cell=0;p.path={0,1,2,3,0};assert(!route_allowed(p,1,2,3,1,Reason::NONE));\n // 13 unrelated movement away from target is still rejected; 14 a strategic event still permits it.\n p.cell=3;p.path={0,1,2,3};assert(!route_allowed(p,4,3,2,1,Reason::NONE));assert(route_allowed(p,4,3,2,2,Reason::GENERAL_EMERGENCY));'''
test = replace_once(test, old_tests, new_tests, 'core exact cycle semantics')
test = replace_once(test, 'std::cout<<"v35 core: 20 behavioral checks passed\\n";', 'std::cout<<"v35 core: 25 behavioral checks passed\\n";', 'core test count')
TEST.write_text(test)
print('clean cycle-only patch complete')
