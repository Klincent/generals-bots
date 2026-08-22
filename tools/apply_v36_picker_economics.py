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

replace_once(
''' EdgePickerState picker_;int edge_picker_threshold_=4,picker_wait_=0;long picker_starts_=0,picker_completions_=0,picker_moves_=0,picker_aborts_=0,picker_units_delivered_=0,picker_blocked_ticks_=0,picker_lost_aborts_=0,picker_depleted_aborts_=0,picker_source_guard_rejects_=0,picker_critical_preempt_moves_=0;''',
''' EdgePickerState picker_;int edge_picker_threshold_=12,picker_wait_=0;double edge_picker_min_efficiency_=2.0;long picker_starts_=0,picker_completions_=0,picker_moves_=0,picker_aborts_=0,picker_units_delivered_=0,picker_blocked_ticks_=0,picker_lost_aborts_=0,picker_depleted_aborts_=0,picker_source_guard_rejects_=0,picker_critical_preempt_moves_=0,picker_start_mass_rejects_=0,picker_start_efficiency_rejects_=0,picker_planned_mass_sum_=0,picker_planned_moves_sum_=0;''',
'picker economic fields')

replace_once(
'''packet_at_.assign(n_,0);if(const char*e=std::getenv("V35_EDGE_PICKER_THRESHOLD")){int v=std::atoi(e);if(v>=0&&v<=100)edge_picker_threshold_=v;}std::fprintf''',
'''packet_at_.assign(n_,0);if(const char*e=std::getenv("V35_EDGE_PICKER_THRESHOLD")){int v=std::atoi(e);if(v>=0&&v<=100)edge_picker_threshold_=v;}if(const char*e=std::getenv("V36_EDGE_PICKER_MIN_EFFICIENCY")){double v=std::atof(e);if(v>=0.0&&v<=20.0)edge_picker_min_efficiency_=v;}std::fprintf''',
'picker efficiency runtime setting')

old_start = '''  if(!picker_.active&&!immediate&&general_>=0){int best_wall=-1,best_mass=edge_picker_threshold_;for(int wall=0;wall<4;++wall)if(wall_irrelevant(wall,picker_sink)){int mass=0;for(int x=0;x<n_;++x)if(wall_contains(x,wall)&&x!=general_&&picker_transit_safe(o,x))mass+=std::max(0,o.army[x]-1);if(mass>edge_picker_threshold_&&(best_wall<0||mass>best_mass)){best_wall=wall;best_mass=mass;}}if(best_wall>=0){int proj=(best_wall==0||best_wall==2)?general_%w_:general_/w_,start=-1,far=-1;for(int x=0;x<n_;++x)if(wall_contains(x,best_wall)&&x!=general_&&picker_transit_safe(o,x)&&o.army[x]>1){int d=std::abs(wall_coord(x,best_wall)-proj);if(d>far){far=d;start=x;}}if(start>=0&&owned_next_to_general(o,start)>=0){int c0=wall_coord(start,best_wall);picker_={true,best_wall,start,c0<proj?1:c0>proj?-1:0,0,o.turn,o.army[start],0};picker_wait_=0;++picker_starts_;}}}'''
new_start = '''  if(!picker_.active&&!immediate&&general_>=0){int best_wall=-1,best_start=-1,best_dir=0,best_mass=-1,best_moves=INF;double best_margin=-1e100;for(int wall=0;wall<4;++wall)if(wall_irrelevant(wall,picker_sink)){int proj=(wall==0||wall==2)?general_%w_:general_/w_,limit=(wall==0||wall==2)?w_:h_;for(int side:{-1,1}){int far=proj,mass=0;for(int cc=proj+side;cc>=0&&cc<limit;cc+=side){int z=wall_cell_at(wall,cc);if(z<0||z==general_||!picker_transit_safe(o,z))break;if(o.army[z]>1)far=cc;}if(far==proj)continue;for(int cc=far;;cc-=side){int z=wall_cell_at(wall,cc);if(z>=0&&z!=general_&&picker_transit_safe(o,z))mass+=std::max(0,o.army[z]-1);if(cc==proj)break;}int start=wall_cell_at(wall,far),proj_cell=wall_cell_at(wall,proj);if(start<0||owned_next_to_general(o,start)<0)continue;int sweep=std::abs(far-proj),back=(proj_cell>=0&&g_.dist[proj_cell][general_]<INF)?g_.dist[proj_cell][general_]:g_.dist[start][general_];int moves=std::max(1,sweep+std::max(0,back));if(mass<=edge_picker_threshold_){++picker_start_mass_rejects_;continue;}double eff=double(mass)/moves;if(eff<edge_picker_min_efficiency_){++picker_start_efficiency_rejects_;continue;}double margin=mass-edge_picker_min_efficiency_*moves;if(best_start<0||std::tuple(-margin,-mass,moves,wall,start)<std::tuple(-best_margin,-best_mass,best_moves,best_wall,best_start)){best_wall=wall;best_start=start;best_dir=side<0?1:-1;best_mass=mass;best_moves=moves;best_margin=margin;}}}if(best_start>=0){picker_={true,best_wall,best_start,best_dir,0,o.turn,o.army[best_start],0};picker_wait_=0;++picker_starts_;picker_planned_mass_sum_+=best_mass;picker_planned_moves_sum_+=best_moves;}}'''
replace_once(old_start, new_start, 'ray-local economic picker trigger')

old_report = '''std::fprintf(stderr,"[v36_picker] threshold=%d starts=%ld completions=%ld moves=%ld delivered=%ld aborts=%ld active=%d blocked_ticks=%ld lost_aborts=%ld depleted_aborts=%ld source_guard=%ld critical_preempt_moves=%ld\\n",edge_picker_threshold_,picker_starts_,picker_completions_,picker_moves_,picker_units_delivered_,picker_aborts_,picker_.active?1:0,picker_blocked_ticks_,picker_lost_aborts_,picker_depleted_aborts_,picker_source_guard_rejects_,picker_critical_preempt_moves_);'''
new_report = '''std::fprintf(stderr,"[v36_picker] threshold=%d min_eff=%.2f starts=%ld completions=%ld moves=%ld delivered=%ld aborts=%ld active=%d blocked_ticks=%ld lost_aborts=%ld depleted_aborts=%ld source_guard=%ld critical_preempt_moves=%ld mass_rejects=%ld efficiency_rejects=%ld planned_mass=%ld planned_moves=%ld\\n",edge_picker_threshold_,edge_picker_min_efficiency_,picker_starts_,picker_completions_,picker_moves_,picker_units_delivered_,picker_aborts_,picker_.active?1:0,picker_blocked_ticks_,picker_lost_aborts_,picker_depleted_aborts_,picker_source_guard_rejects_,picker_critical_preempt_moves_,picker_start_mass_rejects_,picker_start_efficiency_rejects_,picker_planned_mass_sum_,picker_planned_moves_sum_);'''
replace_once(old_report, new_report, 'picker economics telemetry')

old_public = '''int edge_picker_cell()const{return picker_.cell;}int edge_picker_threshold()const{return edge_picker_threshold_;}bool edge_picker_active()const{return picker_.active;}'''
new_public = '''int edge_picker_cell()const{return picker_.cell;}int edge_picker_threshold()const{return edge_picker_threshold_;}double edge_picker_min_efficiency()const{return edge_picker_min_efficiency_;}long edge_picker_mass_rejects()const{return picker_start_mass_rejects_;}long edge_picker_efficiency_rejects()const{return picker_start_efficiency_rejects_;}bool edge_picker_active()const{return picker_.active;}'''
replace_once(old_public, new_public, 'picker economics test accessors')

p.write_text(s)

# Preserve the lifecycle regression by disabling the new start-economics gate there.
tp = Path('competition/agents/juraj_v35_cpp/test_picker.cpp')
t = tp.read_text()
needle = 'int main(){\n'
insert = 'int main(){\n setenv("V36_EDGE_PICKER_MIN_EFFICIENCY","0",1);\n'
if insert not in t:
    if t.count(needle) != 1:
        raise SystemExit('test_picker main: unexpected shape')
    t = t.replace(needle, insert, 1)
    tp.write_text(t)
    print('lifecycle test economics override: applied')

te = Path('competition/agents/juraj_v35_cpp/test_picker_economics.cpp')
te.write_text(r'''#define V35_AGENT_TEST
#include "main.cpp"
#include <cassert>
#include <cstdlib>
#include <iostream>

static Observation board(){
 Observation o;o.turn=80;o.type.assign(441,1);o.owner.assign(441,1);o.army.assign(441,1);
 o.type[220]=4;o.army[220]=8;o.my_land=441;o.my_army=448;o.opp_land=0;o.opp_army=0;return o;
}
static void recalc(Observation&o){o.my_army=0;o.my_land=0;for(int z=0;z<441;++z)if(o.owner[z]==1){++o.my_land;o.my_army+=o.army[z];}}
int main(){
 setenv("V35_EDGE_PICKER_THRESHOLD","8",1);setenv("V36_EDGE_PICKER_MIN_EFFICIENCY","2.0",1);
 // Whole-wall mass must not falsely combine two separate sweep rays.
 {Agent a(0,21,21);auto o=board();for(int r:{4,7,13,16})o.army[r*21+20]=3;recalc(o);a.decide(o);assert(a.edge_picker_starts()==0);assert(!a.edge_picker_active());}
 // A large but very sparse/distant sweep is rejected by army-per-move economics.
 {Agent a(0,21,21);auto o=board();o.army[2*21+20]=12;recalc(o);a.decide(o);assert(a.edge_picker_starts()==0);assert(a.edge_picker_efficiency_rejects()>0);}
 // Dense valuable ray starts and lifecycle still runs it all the way to the general.
 {Agent a(0,21,21);auto o=board();for(int r:{2,3,4,5,6,7,8,9})o.army[r*21+20]=8;recalc(o);for(int i=0;i<100&&a.edge_picker_completions()==0;++i){auto q=a.decide(o);if(q.kind==0){static int dr[4]={-1,1,0,0},dc[4]={0,0,-1,1};int x=q.row*21+q.col,y=(q.row+dr[q.dir])*21+q.col+dc[q.dir],m=o.army[x]-1;o.army[x]=1;o.army[y]+=m;recalc(o);}++o.turn;}assert(a.edge_picker_starts()==1);assert(a.edge_picker_completions()==1);assert(a.edge_picker_aborts()==0);assert(a.edge_picker_delivered()>20);}
 std::cout<<"v36 picker economics scenarios passed\n";
}
''')
print('test_picker_economics.cpp: written')

ts = Path('competition/agents/juraj_v35_cpp/test.sh')
u = ts.read_text()
block = '''\ng++ -O2 -std=c++17 -Wall -Wextra -Wpedantic test_picker_economics.cpp -o test_picker_economics\n./test_picker_economics\n'''
if 'test_picker_economics.cpp' not in u:
    u += block
    ts.write_text(u)
    print('test.sh economics regression: applied')

print('V3.6 picker economics patch complete')
