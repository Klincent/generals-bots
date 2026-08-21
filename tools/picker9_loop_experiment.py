from pathlib import Path
import re
import subprocess
import sys

FINAL = "2260b6f19d51a14d7c68770677f22d04dfd88022"
REL = "competition/agents/juraj_v35_cpp/main.cpp"

p = Path(sys.argv[1])
final_src = subprocess.check_output(["git", "show", f"{FINAL}:{REL}"], text=True)
s = final_src

# Keep the best completed small-loop search-share candidate as the base.
old = "!enemy_seen?.20:.08"
new = "(production_==ProductionState::HEALTHY&&!enemy_seen&&o.turn<=50)?.29:(!enemy_seen?.20:.08)"
if s.count(old) != 1:
    raise SystemExit(f"final search-share anchor count={s.count(old)}")
s = s.replace(old, new, 1)

# Picker mitigation 1: late_muster must not hard-disable starting a new edge picker.
old = "if(picker_enabled_&&!picker_.active&&!immediate&&general_>=0&&!late_muster){"
new = "if(picker_enabled_&&!picker_.active&&!immediate&&general_>=0){"
if s.count(old) != 1:
    raise SystemExit(f"late-muster picker gate anchor count={s.count(old)}")
s = s.replace(old, new, 1)

# Picker mitigation 2: after t300, a genuinely useful late harvest may start even
# when territorial growth has naturally flattened.
old = "else if(!growing)++picker_reject_growth_;"
new = "else if(!growing&&!(o.turn>=300&&best_mass>=std::max(24,edge_picker_threshold_+8)))++picker_reject_growth_;"
if s.count(old) != 1:
    raise SystemExit(f"growth gate anchor count={s.count(old)}")
s = s.replace(old, new, 1)

# Picker mitigation 3: evaluate every contiguous safe segment of an irrelevant
# wall, rather than only the segment directly connected to the general's wall
# projection. Mountains / unsafe cells may split a wall; the picker sweeps the
# chosen segment toward the nearest exit and then returns through owned interior.
pattern = re.compile(
    r"for\(int wall=0;wall<4;\+\+wall\)if\(wall_irrelevant\(wall,picker_sink\)\)\{.*?\}\}\n   if\(best_start>=0\)\{",
    re.S,
)
replacement = r'''for(int wall=0;wall<4;++wall)if(wall_irrelevant(wall,picker_sink)){
    int proj=(wall==0||wall==2)?general_%w_:general_/w_,limit=(wall==0||wall==2)?w_:h_;
    for(int cc=0;cc<limit;){
     auto ok=[&](int q){int z=wall_cell_at(wall,q);return z>=0&&z!=general_&&picker_transit_safe(o,z);};
     while(cc<limit&&!ok(cc))++cc;if(cc>=limit)break;
     int lo=cc;while(cc<limit&&ok(cc))++cc;int hi=cc-1;if(lo>hi)continue;
     bool proj_in=proj>=lo&&proj<=hi;
     int target_coord=-1,far=-1;
     if(proj_in){int dl=proj-lo,dr=hi-proj;target_coord=proj;far=dl>=dr?lo:hi;}
     else{target_coord=std::abs(lo-proj)<=std::abs(hi-proj)?lo:hi;far=target_coord==lo?hi:lo;}
     if(far==target_coord)continue;
     int step=far<target_coord?1:-1,mass=0;
     for(int q=far;;q+=step){int z=wall_cell_at(wall,q);if(z>=0&&z!=general_&&picker_transit_safe(o,z))mass+=std::max(0,o.army[z]-1);if(q==target_coord)break;}
     if(mass<=edge_picker_threshold_){++picker_start_mass_rejects_;continue;}
     int start=wall_cell_at(wall,far),target_cell=wall_cell_at(wall,target_coord);if(start<0||owned_next_to_general(o,start)<0)continue;
     int sweep=std::abs(far-target_coord),back=(target_cell>=0&&g_.dist[target_cell][general_]<INF)?g_.dist[target_cell][general_]:g_.dist[start][general_];int moves=std::max(1,sweep+std::max(0,back));
     double eff=double(mass)/moves;if(eff<edge_picker_min_efficiency_){++picker_start_efficiency_rejects_;continue;}double margin=mass-edge_picker_min_efficiency_*moves;
     int pdir=step;
     if(best_start<0||std::tuple(-margin,-mass,moves,wall,start)<std::tuple(-best_margin,-best_mass,best_moves,best_wall,best_start)){best_wall=wall;best_start=start;best_dir=pdir;best_mass=mass;best_moves=moves;best_margin=margin;}
    }
   }
   if(best_start>=0){'''
s, n = pattern.subn(replacement, s, count=1)
if n != 1:
    raise SystemExit(f"wall-segment picker block replacements={n}")

p.write_text(s)

# Baseline remains the unmodified final candidate, so this run measures the
# search-share + late-picker mitigation as one candidate against exact final.
parent = Path("/tmp/parent") / REL
if not parent.exists():
    raise SystemExit("ephemeral /tmp/parent source missing")
parent.write_text(final_src)

print("experiment=final_2260b6f_best_search029_plus_late_picker_mitigation")
