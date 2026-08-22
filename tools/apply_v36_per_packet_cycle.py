from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CORE=ROOT/'competition/agents/juraj_v35_cpp/core.hpp'
MAIN=ROOT/'competition/agents/juraj_v35_cpp/main.cpp'
TEST=ROOT/'competition/agents/juraj_v35_cpp/test_core.cpp'

def one(s,a,b,label):
    if s.count(a)!=1: raise SystemExit(f'{label}: expected 1 match, got {s.count(a)}')
    print(label+': applied')
    return s.replace(a,b,1)

s=CORE.read_text()
old='inline bool route_allowed(const Packet&p,int dest,int new_distance,int old_distance,int event_version,Reason reason){bool changed=event_version!=p.event_version&&reason!=Reason::NONE;if(!changed&&new_distance>old_distance)return false;if(!changed&&p.path.size()>=2&&dest==p.path[p.path.size()-2])return false;if(!changed&&p.path.size()>=3&&dest==p.path[p.path.size()-3])return false;if(!changed&&p.path.size()>=4&&dest==p.path[p.path.size()-4])return false;return true;}'
new='inline bool route_allowed(const Packet&p,int dest,int new_distance,int old_distance,int event_version,Reason reason){bool emergency=reason==Reason::GENERAL_EMERGENCY||reason==Reason::TERMINAL_CAPTURE;if(emergency)return true;int seen_edges=0;for(int i=(int)p.path.size()-1;i>=1&&seen_edges<4;--i,++seen_edges)if(p.path[i-1]==p.cell&&p.path[i]==dest)return false;bool recent_return=false;int seen_cells=0;for(auto it=p.path.rbegin();it!=p.path.rend()&&seen_cells<4;++it,++seen_cells)if(*it==dest){recent_return=true;break;}bool changed=event_version!=p.event_version&&reason!=Reason::NONE;if(!changed&&new_distance>old_distance&&!recent_return)return false;return true;}'
s=one(s,old,new,'per-packet directed-edge guard')
CORE.write_text(s)

s=MAIN.read_text()
s=one(s,'while(p.path.size()>12)p.path.pop_front();','while(p.path.size()>5)p.path.pop_front();','packet history four moves')
oldh='bool history_cycle(const Candidate&q)const{if(q.from<0||q.to<0)return false;for(auto it=actions_.rbegin();it!=actions_.rend();++it){if(it->event!=event_)break;if(it->from==q.to&&it->to==q.from)return true;}return false;}'
newh='bool history_cycle(const Candidate&q)const{(void)q;return false;}'
s=one(s,oldh,newh,'remove global cross-packet cycle guard')
MAIN.write_text(s)

s=TEST.read_text()
oldt=''' // 7 A-B-A and 8 A-B-C-B loops are hard rejected.\n Packet p;p.cell=2;p.target=8;p.event_version=1;p.path={0,1,2};assert(!route_allowed(p,1,2,2,1,Reason::NONE));p.path={0,1,2,3};assert(!route_allowed(p,1,2,2,1,Reason::NONE));\n // 9 a real strategic event permits reversal.\n assert(route_allowed(p,2,3,2,2,Reason::GENERAL_EMERGENCY));'''
newt=''' // 7 A-B-A is allowed for the same packet.\n Packet p;p.target=8;p.event_version=1;p.cell=1;p.path={0,1};assert(route_allowed(p,0,3,2,1,Reason::NONE));\n // 8 A-B-A-B is blocked for that packet.\n p.cell=0;p.path={0,1,0};assert(!route_allowed(p,1,2,3,1,Reason::NONE));\n // 9 A-B-C-B is allowed; 10 the next B-C is blocked.\n p.cell=2;p.path={0,1,2};assert(route_allowed(p,1,3,2,1,Reason::NONE));p.cell=1;p.path={0,1,2,1};assert(!route_allowed(p,2,2,3,1,Reason::NONE));\n // 11 A-B-C-D-A is allowed; 12 next A-B is blocked while recent.\n p.cell=3;p.path={0,1,2,3};assert(route_allowed(p,0,3,2,1,Reason::NONE));p.cell=0;p.path={0,1,2,3,0};assert(!route_allowed(p,1,2,3,1,Reason::NONE));\n // 13 emergency can override the short packet history.\n assert(route_allowed(p,1,2,3,2,Reason::GENERAL_EMERGENCY));'''
s=one(s,oldt,newt,'exact per-packet semantics')
s=one(s,'std::cout<<"v35 core: 20 behavioral checks passed\\n";','std::cout<<"v35 core: 24 behavioral checks passed\\n";','test count')
TEST.write_text(s)
print('per-packet cycle patch complete')