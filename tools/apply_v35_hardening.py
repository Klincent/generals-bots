#!/usr/bin/env python3
from pathlib import Path

P5 = Path('competition/agents/juraj_cpp/v34_part05.inc')
P6 = Path('competition/agents/juraj_cpp/v34_part06.inc')


def replace_once(text: str, old: str, new: str, label: str) -> str:
    n = text.count(old)
    if n == 0:
        if new in text:
            print(f'{label}: already applied')
            return text
        raise SystemExit(f'{label}: source pattern not found')
    if n != 1:
        raise SystemExit(f'{label}: expected 1 match, found {n}')
    print(f'{label}: applied')
    return text.replace(old, new, 1)

p5 = P5.read_text()
p5 = replace_once(
    p5,
    'static constexpr int target[3]={150,225,315};',
    'static constexpr int target[3]={160,235,325};',
    'castle funding targets',
)
p5 = replace_once(
    p5,
    'Action maybe_v31_castle_action(const Observation&o){if(v3_castle_count_<=0||hunter_trigger_turn_>=0||required_defense_>0||production_emergency_)return pass();',
    'Action maybe_v31_castle_action(const Observation&o){if(v3_castle_count_<=0||hunter_trigger_turn_>=0||required_defense_>0)return pass();',
    'C1 production-emergency override',
)
p5 = replace_once(
    p5,
    'static constexpr int lo[3]={130,225,300},hi[3]={175,285,375};',
    'static constexpr int lo[3]={145,225,300},hi[3]={190,285,375};',
    'castle windows',
)
p5 = replace_once(
    p5,
    'if(hunter_suspicion_active_){++f.skipped[2];return pass();}int danger=INF;',
    'if(hunter_suspicion_active_&&!(i==0&&o.turn>=170)){++f.skipped[2];return pass();}int danger=INF;',
    'overdue C1 suspicion override',
)
p5 = replace_once(
    p5,
    'for(auto e:visible_enemy_stacks_)danger=std::min(danger,dist_[cell_id_[x]][cell_id_[e.first]]);\n        bool early=',
    'for(auto e:visible_enemy_stacks_)danger=std::min(danger,dist_[cell_id_[x]][cell_id_[e.first]]);bool c1_overdue=i==0&&o.turn>=170;\n        bool early=',
    'C1 overdue state',
)
old_build = 'if(o.owner[x]==1&&o.type[x]==1&&o.turn>=lo[i]&&o.turn<=hi[i]&&f.army>=f.live_cost&&early_safe&&approach_safe&&!hunter_warning_active_&&!hunter_suspicion_active_&&danger>2&&o.my_army-f.live_cost>=std::max(20,o.opp_army/2))'
new_build = 'if(o.owner[x]==1&&o.type[x]==1&&o.turn>=lo[i]&&o.turn<=hi[i]&&f.army>=f.live_cost&&early_safe&&approach_safe&&(c1_overdue||(!hunter_warning_active_&&!hunter_suspicion_active_))&&danger>2&&(c1_overdue?o.my_army-f.live_cost>=20:o.my_army-f.live_cost>=std::max(20,o.opp_army/2)))'
p5 = replace_once(p5, old_build, new_build, 'C1 hard deadline build gate')
P5.write_text(p5)

p6 = P6.read_text()
needle = 'Choice choose_rear_drain(const Observation&o){Choice best;int attack=-1,defense=-1;bool to_defense=false;rear_sinks(o,attack,defense,to_defense);bool mass='
insert = '''Choice choose_rear_drain(const Observation&o){Choice best;int attack=-1,defense=-1;bool to_defense=false;rear_sinks(o,attack,defense,to_defense);
        // V3.5: before contact, safe boundary army must not fossilize on the map edge.
        // Build up to two independent inward-flow chunks.  Prefer owned planned
        // castle hubs (so logistics simultaneously funds C1/C2); otherwise pick
        // separated interior owned rally cells.  Every move is FULL-1 and strictly
        // decreases static graph distance to its chosen rally.
        if(enemy_general_<0&&!contact_established_&&required_defense_==0&&!approach_threat_active_&&hunter_trigger_turn_<0){
            std::array<int,2> rally{{-1,-1}};int rc=0;
            for(int i=0;i<2&&rc<2;++i){int q=planned_castle_[i];if(q>=0&&o.owner[q]==1&&q!=general_)rally[rc++]=q;}
            for(int pass=0;pass<2&&rc<2;++pass){int bx=-1;double bs=-1e100;for(int z:id_cell_)if(o.owner[z]==1&&z!=general_&&!known_castle_[z]){int edge=std::min({row(z),h_-1-row(z),col(z),w_-1-col(z)});if(edge<2)continue;if(rc&&dist_[cell_id_[z]][cell_id_[rally[0]]]<5)continue;double s=edge*35+nav_[z].route_load*20+degree_[z]*8+o.army[z]*.5;if(s>bs)bs=s,bx=z;}if(bx>=0)rally[rc++]=bx;}
            if(rc>0){std::array<int,3> branch{};std::array<int,9> sector{};for(int z:id_cell_){int edge=std::min({row(z),h_-1-row(z),col(z),w_-1-col(z)});if(o.owner[z]!=1||o.army[z]<=1||z==general_||known_castle_[z]||planned_unbuilt_site(z)||z==front_stack_||z==contact_staging_cell_||z==main_stack_||z==reaction_cell_||articulation_[z])continue;if(edge>1&&degree_[z]>1&&terminal_depth_[z]<=0)continue;bool threatened=false;for(auto e:visible_enemy_stacks_)if(e.second>=8&&dist_[cell_id_[z]][cell_id_[e.first]]<=5)threatened=true;if(threatened)continue;int b=v3_branch(z),surplus=o.army[z]-1;if(b>=0)branch[b]+=surplus;sector[nav_[z].sector]+=surplus;}
                for(int z:id_cell_){int edge=std::min({row(z),h_-1-row(z),col(z),w_-1-col(z)});if(o.owner[z]!=1||o.army[z]<=1||z==general_||known_castle_[z]||planned_unbuilt_site(z)||z==front_stack_||z==contact_staging_cell_||z==main_stack_||z==reaction_cell_||articulation_[z])continue;if(edge>1&&degree_[z]>1&&terminal_depth_[z]<=0)continue;bool threatened=false;for(auto e:visible_enemy_stacks_)if(e.second>=8&&dist_[cell_id_[z]][cell_id_[e.first]]<=5)threatened=true;if(threatened)continue;int sink=rally[0];if(rc>1&&dist_[cell_id_[z]][cell_id_[rally[1]]]<dist_[cell_id_[z]][cell_id_[rally[0]]])sink=rally[1];int h=next_hop_[cell_id_[z]][cell_id_[sink]];if(h<0)continue;int y=id_cell_[h];if(o.owner[y]!=1||dist_[cell_id_[y]][cell_id_[sink]]>=dist_[cell_id_[z]][cell_id_[sink]])continue;int surplus=o.army[z]-1,b=v3_branch(z),aggregate=b>=0?branch[b]:sector[nav_[z].sector];int corner=(row(z)==0||row(z)==h_-1)&&(col(z)==0||col(z)==w_-1);double score=420+std::min(aggregate,24)*16+std::min(surplus,16)*14+dist_[cell_id_[z]][cell_id_[sink]]*4+(edge==0?90:40)+(corner?80:0);if(o.army[z]>=8)score+=180;if(o.turn>=120&&planned_castle_built_turn_[0]<0&&sink==planned_castle_[0])score+=220;if(score>best.score){best={score,move(z,y,0),true};pending_rear_drain_source_=z;pending_rear_drain_dest_=y;pending_rear_drain_sink_=sink;pending_rear_drain_kind_=1;}}
                if(best.valid)return best;
            }
        }
        bool mass='''
p6 = replace_once(p6, needle, insert, 'pre-contact two-chunk edge consolidation')
P6.write_text(p6)

print('V3.5 hardening patch complete')
