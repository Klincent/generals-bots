from pathlib import Path

p = Path('competition/agents/juraj_v35_cpp/main.cpp')
s = p.read_text()

def replace_once(old, new, label):
    global s
    if new in s:
        print(f'{label}: already applied')
        return
    n = s.count(old)
    if n != 1:
        raise SystemExit(f'{label}: expected exactly one old block, found {n}')
    s = s.replace(old, new, 1)
    print(f'{label}: applied')

old_fields = ''' EdgePickerState picker_;int edge_picker_threshold_=12,picker_wait_=0;double edge_picker_min_efficiency_=2.0;long picker_starts_=0,picker_completions_=0,picker_moves_=0,picker_aborts_=0,picker_units_delivered_=0,picker_blocked_ticks_=0,picker_lost_aborts_=0,picker_depleted_aborts_=0,picker_source_guard_rejects_=0,picker_critical_preempt_moves_=0,picker_start_mass_rejects_=0,picker_start_efficiency_rejects_=0,picker_planned_mass_sum_=0,picker_planned_moves_sum_=0;'''
new_fields = ''' EdgePickerState picker_;int edge_picker_threshold_=16,picker_wait_=0;double edge_picker_min_efficiency_=2.0;long picker_starts_=0,picker_completions_=0,picker_moves_=0,picker_aborts_=0,picker_units_delivered_=0,picker_blocked_ticks_=0,picker_lost_aborts_=0,picker_depleted_aborts_=0,picker_source_guard_rejects_=0,picker_critical_preempt_moves_=0,picker_start_mass_rejects_=0,picker_start_efficiency_rejects_=0,picker_planned_mass_sum_=0,picker_planned_moves_sum_=0;
 std::array<int,9> sector_target_{{-1,-1,-1,-1,-1,-1,-1,-1,-1}},sector_first_touch_{{-1,-1,-1,-1,-1,-1,-1,-1,-1}},sector_last_progress_{{-1,-1,-1,-1,-1,-1,-1,-1,-1}},sector_owned_max_{{0,0,0,0,0,0,0,0,0}},sector_passable_{{0,0,0,0,0,0,0,0,0}};std::array<std::vector<int>,9> sector_backbone_;int general_sector_=-1,sector_primary_=-1,sector_secondary_=-1;long sector_probe_moves_=0,sector_forced_moves_=0;'''
replace_once(old_fields, new_fields, 'best picker threshold + sector state')

old_tactical = ''' int tactical_next(const Observation&o,int x,int target)const{int best=-1,bd=INF;for(int d=0;d<4;++d){int y=g_.neighbor(x,d);if(safe_step(o,x,y)&&g_.dist[y][target]<bd)best=y,bd=g_.dist[y][target];}return best;}'''
new_tactical = old_tactical + r'''
 int sector_of(int x)const{if(x<0||x>=n_)return -1;int r=x/w_,c=x%w_;return std::min(2,3*r/std::max(1,h_))*3+std::min(2,3*c/std::max(1,w_));}
 void init_sector_exploration(){sector_target_.fill(-1);sector_first_touch_.fill(-1);sector_last_progress_.fill(-1);sector_owned_max_.fill(0);sector_passable_.fill(0);for(auto&v:sector_backbone_)v.clear();general_sector_=sector_of(general_);for(int x=0;x<n_;++x)if(g_.passable[x]){int s=sector_of(x);if(s>=0)++sector_passable_[s];}for(int s=0;s<9;++s){if(s==general_sector_)continue;int sr=s/3,sc=s%3,cr=std::min(h_-1,(2*sr+1)*h_/6),cc=std::min(w_-1,(2*sc+1)*w_/6),best=-1;std::tuple<int,int,int>bk{INF,INF,INF};for(int x=0;x<n_;++x)if(g_.passable[x]&&sector_of(x)==s&&general_>=0&&g_.dist[general_][x]<INF){auto k=std::tuple(std::abs(x/w_-cr)+std::abs(x%w_-cc),g_.dist[general_][x],x);if(k<bk)bk=k,best=x;}sector_target_[s]=best;if(best>=0){int cur=general_,guard=0;sector_backbone_[s].push_back(cur);while(cur!=best&&guard++<n_){int nx=g_.next[cur][best];if(nx<0||nx==cur)break;cur=nx;sector_backbone_[s].push_back(cur);}}}}
 void update_sector_coverage(const Observation&o){std::array<int,9>owned{};for(int x=0;x<n_;++x)if(o.owner[x]==1){int s=sector_of(x);if(s>=0)++owned[s];}for(int s=0;s<9;++s){if(owned[s]>0&&sector_first_touch_[s]<0)sector_first_touch_[s]=o.turn;if(owned[s]>sector_owned_max_[s]){sector_owned_max_[s]=owned[s];sector_last_progress_[s]=o.turn;}}}
 int search_reachable_count()const{int z=general_sector_>=0?1:0;for(int s=0;s<9;++s)if(s!=general_sector_&&sector_target_[s]>=0)++z;return z;}
 int sector_touched_count()const{int z=0;for(int s=0;s<9;++s)if((s==general_sector_||sector_target_[s]>=0)&&sector_first_touch_[s]>=0)++z;return z;}
 bool sector_swept(int s)const{if(s<0||s>=9||sector_passable_[s]<=0)return true;int need=std::max(3,std::min(8,sector_passable_[s]/8));return sector_owned_max_[s]>=need;}
 int sector_swept_count()const{int z=0;for(int s=0;s<9;++s)if((s==general_sector_||sector_target_[s]>=0)&&sector_swept(s))++z;return z;}
 int sector_goal(const Observation&o,int s)const{if(s<0||s>=9||sector_target_[s]<0)return -1;int best=-1;std::tuple<int,int,int,int>bk{1,1,INF,INF};for(int x=0;x<n_;++x)if(g_.passable[x]&&sector_of(x)==s&&g_.dist[general_][x]<INF&&o.owner[x]!=1){int enemy=o.owner[x]==2?0:1,deep=-g_.dist[general_][x],center=std::abs(x/w_-(2*(s/3)+1)*h_/6)+std::abs(x%w_-(2*(s%3)+1)*w_/6);auto k=std::tuple(enemy,deep,center,x);if(best<0||k<bk)bk=k,best=x;}return best>=0?best:sector_target_[s];}
 std::array<int,2> choose_probe_sectors(const Observation&o)const{std::array<int,2>out{{-1,-1}};if(belief_.confirmed()||general_<0||o.turn<80)return out;int reachable=search_reachable_count(),touched=sector_touched_count(),swept=sector_swept_count();if(reachable<=1||(touched>=reachable&&swept>=reachable))return out;int desired=o.turn>=550?reachable:(o.turn>=400?std::min(reachable,7):(o.turn>=250?std::min(reachable,5):0));bool lead=o.my_land>=o.opp_land&&o.my_army*10>=o.opp_army*9;int slots=(o.turn>=400&&lead)?2:1;std::vector<std::pair<double,int>>score;for(int s=0;s<9;++s){if(s==general_sector_||sector_target_[s]<0)continue;bool untouched=sector_first_touch_[s]<0,unswept=!sector_swept(s);int stale=sector_last_progress_[s]<0?o.turn:o.turn-sector_last_progress_[s];double v=(untouched?10000.:0)+(unswept?2500.:0)+std::min(stale,300)*4.0+g_.dist[general_][sector_target_[s]]*2.0;if(touched<desired&&untouched)v+=12000.;if(o.turn>=550&&unswept)v+=4000.;score.push_back({v,s});}std::sort(score.begin(),score.end(),[](auto a,auto b){return std::tuple(-a.first,a.second)<std::tuple(-b.first,b.second);});for(int k=0;k<slots&&k<(int)score.size();++k)out[k]=score[k].second;return out;}
 bool sector_probe_forced(const Observation&o,int s)const{if(s<0)return false;int reachable=search_reachable_count(),touched=sector_touched_count();if(o.turn>=550&&(touched<reachable||!sector_swept(s)))return true;if(o.turn>=400&&touched<std::min(reachable,7)&&sector_first_touch_[s]<0)return true;if(o.turn>=250&&touched<std::min(reachable,5)&&sector_first_touch_[s]<0)return true;return false;}
 Candidate sector_probe_candidate(const Observation&o,int s,bool forced,int avoid_from)const{int target=sector_goal(o,s);if(target<0)return {};auto make=[&](int x){if(x<0||x==avoid_from||!source(o,x)||x==general_||(picker_.active&&x==picker_.cell)||x==castles_.c1||x==castles_.c2)return Candidate{};int surplus=o.army[x]-reserve(o,x);if(surplus<(forced?2:4))return Candidate{};int y=tactical_next(o,x,target);if(y<0)return Candidate{};double u=(forced?4200.:1400.)+surplus*10.-g_.dist[x][target]*5.+(o.owner[y]!=1?120.:0);return Candidate{forced?2:3,x,y,0,u,Reason::SEARCH_PROGRESS,false,ActionClass::SEARCH,target,-1,PacketRole::SEARCH};};Candidate best;bool have=false;for(auto&kv:packets_){const Packet&p=kv.second;if(p.role!=PacketRole::SEARCH||sector_of(p.target)!=s)continue;Candidate q=make(p.cell);if(q.from>=0&&(!have||q.utility>best.utility))best=q,have=true;}if(have)return best;for(int x=0;x<n_;++x){Candidate q=make(x);if(q.from>=0&&(!have||q.utility>best.utility))best=q,have=true;}return have?best:Candidate{};}'''
replace_once(old_tactical, new_tactical, 'sector exploration helpers')

replace_once('''packet_at_.assign(n_,0);if(const char*e=std::getenv("V35_EDGE_PICKER_THRESHOLD")''', '''packet_at_.assign(n_,0);init_sector_exploration();if(const char*e=std::getenv("V35_EDGE_PICKER_THRESHOLD")''', 'turn-zero sector backbones')

if 'reconcile(o);update_sector_coverage(o);' not in s:
    n = s.count('reconcile(o);')
    if n != 1:
        raise SystemExit(f'coverage update: expected one reconcile(o); call, found {n}')
    s = s.replace('reconcile(o);', 'reconcile(o);update_sector_coverage(o);', 1)
    print('coverage update: applied')
else:
    print('coverage update: already applied')

needle_loop = '''  for(int x=0;x<n_;++x)if(source(o,x)){if(picker_.active&&x==picker_.cell)continue;'''
insert_loop = '''  auto probe_sectors=choose_probe_sectors(o);sector_primary_=probe_sectors[0];sector_secondary_=probe_sectors[1];int probe_avoid=-1;for(int k=0;k<2;++k){int sec=probe_sectors[k];if(sec<0||belief_.confirmed()||b.search<=0)continue;bool forced=sector_probe_forced(o,sec);Candidate pq=sector_probe_candidate(o,sec,forced,probe_avoid);if(pq.from>=0){c.push_back(pq);probe_avoid=pq.from;}}
''' + needle_loop
replace_once(needle_loop, insert_loop, 'persistent one/two-sector probe candidates')

replace_once('''!enemy_seen?.20:.08,logistics_share''', '''!belief_.confirmed()?(enemy_seen?.14:.20):.05,logistics_share''', 'keep exploration budget after contact')

replace_once('''bool critical_available=std::any_of(filtered.begin(),filtered.end(),critical);double logistics_share=''', '''bool critical_available=std::any_of(filtered.begin(),filtered.end(),critical);bool coverage_force_available=std::any_of(filtered.begin(),filtered.end(),[](const Candidate&z){return z.role==PacketRole::SEARCH&&z.reason==Reason::SEARCH_PROGRESS&&z.tier==2;});double logistics_share=''', 'coverage force availability')

replace_once('''}else if(picker_.active&&picker_available){''', '''}else if(coverage_force_available&&((picker_.active&&o.turn%6==0)||(!picker_.active&&o.turn%4==0))){std::vector<Candidate>sv;for(auto&z:filtered)if(z.role==PacketRole::SEARCH&&z.reason==Reason::SEARCH_PROGRESS&&z.tier==2)sv.push_back(z);q=schedule(sv);}else if(picker_.active&&picker_available){''', 'bounded hard coverage cadence')

replace_once('''}count_action(o,q,a);''', '''}if(a.kind==0&&q.role==PacketRole::SEARCH){++sector_probe_moves_;if(q.tier==2)++sector_forced_moves_;}count_action(o,q,a);''', 'sector probe telemetry counters')

old_timing = '''std::fprintf(stderr,"[v35_timing] p50=%.3f p95=%.3f p99=%.3f max=%.3f\\n",pct(.5),pct(.95),pct(.99),times_.back());'''
new_timing = '''std::fprintf(stderr,"[v36_search] reachable=%d touched=%d swept=%d primary=%d secondary=%d probe_moves=%ld forced_moves=%ld\\n",search_reachable_count(),sector_touched_count(),sector_swept_count(),sector_primary_,sector_secondary_,sector_probe_moves_,sector_forced_moves_);std::fprintf(stderr,"[v35_timing] p50=%.3f p95=%.3f p99=%.3f max=%.3f\\n",pct(.5),pct(.95),pct(.99),times_.back());'''
replace_once(old_timing, new_timing, 'sector exploration report')

old_public = '''int edge_picker_cell()const{return picker_.cell;}int edge_picker_threshold()const{return edge_picker_threshold_;}double edge_picker_min_efficiency()const{return edge_picker_min_efficiency_;}long edge_picker_mass_rejects()const{return picker_start_mass_rejects_;}long edge_picker_efficiency_rejects()const{return picker_start_efficiency_rejects_;}bool edge_picker_active()const{return picker_.active;}'''
new_public = old_public + '''int search_sector_backbone_count()const{int z=0;for(int s=0;s<9;++s)if(s!=general_sector_&&!sector_backbone_[s].empty())++z;return z;}int search_reachable_sectors()const{return search_reachable_count();}int search_touched_sectors()const{return sector_touched_count();}int search_swept_sectors()const{return sector_swept_count();}std::array<int,2> search_probe_plan_for_test(const Observation&o)const{return choose_probe_sectors(o);}bool search_probe_forced_for_test(const Observation&o,int s)const{return sector_probe_forced(o,s);}'''
replace_once(old_public, new_public, 'search test accessors')

p.write_text(s)

te = Path('competition/agents/juraj_v35_cpp/test_search_refactor.cpp')
te.write_text(r'''#define V35_AGENT_TEST
#include "main.cpp"
#include <cassert>
#include <cstdlib>
#include <iostream>

static Observation blank_board(){
 Observation o;o.turn=0;o.type.assign(441,1);o.owner.assign(441,0);o.army.assign(441,0);
 int g=10*21+10;o.type[g]=4;o.owner[g]=1;o.army[g]=80;o.my_land=1;o.my_army=80;o.opp_land=0;o.opp_army=0;return o;
}
int main(){
 setenv("V35_EDGE_PICKER_THRESHOLD","16",1);setenv("V36_EDGE_PICKER_MIN_EFFICIENCY","2.0",1);
 Agent a(0,21,21);auto o=blank_board();a.decide(o);
 assert(a.edge_picker_threshold()==16);
 assert(a.search_sector_backbone_count()==8);
 assert(a.search_reachable_sectors()==9);
 assert(a.search_touched_sectors()>=1);
 o.turn=560;o.my_army=120;o.opp_army=20;o.my_land=40;o.opp_land=20;
 auto plan=a.search_probe_plan_for_test(o);
 assert(plan[0]>=0);assert(plan[1]>=0);assert(plan[0]!=plan[1]);
 assert(a.search_probe_forced_for_test(o,plan[0]));
 std::cout<<"v36 sector search refactor scenarios passed\n";
}
''')
print('test_search_refactor.cpp: written')

ts = Path('competition/agents/juraj_v35_cpp/test.sh')
t = ts.read_text()
block = '''\ng++ -O2 -std=c++17 -Wall -Wextra -Wpedantic test_search_refactor.cpp -o test_search_refactor\n./test_search_refactor\n'''
if 'test_search_refactor.cpp' not in t:
    t += block
    ts.write_text(t)
    print('test.sh search regression: applied')
else:
    print('test.sh search regression: already applied')

print('V3.6 search refactor patch complete')
