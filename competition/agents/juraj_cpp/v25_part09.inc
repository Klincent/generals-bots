        const char* seed=std::getenv("JURAJ_RNG_SEED");
        if(seed){char* end=nullptr;unsigned long long v=std::strtoull(seed,&end,10);if(end==seed)v=0;rng_.seed(v);}
        else {std::random_device rd;auto t=std::chrono::high_resolution_clock::now().time_since_epoch().count();std::seed_seq seq{rd(),rd(),static_cast<unsigned>(t),static_cast<unsigned>(t>>32)};rng_.seed(seq);}
    }
    Action act(const Observation& o) {
        auto begin=Clock::now();
        auto hard=o.turn==0 ? process_start_+std::chrono::milliseconds(8500)
                            : begin+std::chrono::milliseconds(120);
        if (o.turn==0) initialise(o);
        update_memory(o);
        Action fallback=pass(), result=fallback; bool tactical=false;
        result=immediate_tactics(o,tactical);
        if(!tactical)result=hunter_counterattack(o,tactical);
        if(!tactical)result=defense_emergency(o,tactical);
        if(!tactical)result=high_confidence_capture(o,tactical);
        if(!tactical&&Clock::now()<hard-std::chrono::milliseconds(5)){
            Action build=maybe_contact_castle(o);if(build.kind!=2)build=maybe_build(o);result=build.kind==2?build:choose_strategic(o);
        }
        // Final legality guard always leaves time for a protocol-safe pass.
        if(result.kind==0){int x=cell(result.row,result.col),y=neighbor(x,result.dir);if(!inside(result.row,result.col)||y<0||!passable_[y]||o.owner[x]!=1||o.army[x]<=1)result=fallback;}
        update_contact_metrics(o,result,tactical&&required_defense_>0);update_main_stack_metrics(o,result,tactical&&required_defense_>0);
        if(result.kind==0){++movement_decisions_;if(result.split){++half_moves_;++half_by_mode_[strategy_];int x=cell(result.row,result.col);if(x==general_)++half_from_general_;if(known_castle_[x])++half_from_castle_;if(articulation_[x])++half_from_choke_;if(x==main_stack_)++half_from_main_;else ++half_from_feeder_;}else ++all_moves_;}
        auto end=Clock::now();decision_ms_.push_back(std::chrono::duration<double,std::milli>(end-begin).count());return result;
    }
    void report() const {
        if (decision_ms_.empty()) return;
        std::vector<double> t=decision_ms_;std::sort(t.begin(),t.end());double mean=std::accumulate(t.begin(),t.end(),0.0)/t.size();auto pct=[&](double p){return t[std::min(t.size()-1,static_cast<size_t>(std::ceil(p*t.size())-1))];};
        double sf=strategic_flip_opportunities_?100.0*strategic_flips_taken_/strategic_flip_opportunities_:0, pf=split_flip_opportunities_?100.0*split_flips_taken_/split_flip_opportunities_:0, hp=movement_decisions_?100.0*half_moves_/movement_decisions_:0;
        std::fprintf(stderr,"[juraj_metrics] player=%d turns=%zu land50=%d opp_land50=%d army50=%d opp_army50=%d enemy_general_found=%d found_turn=%d approach10=%d approach5=%d approach2=%d approach1=%d castles_built=%d moves=%llu all=%llu half=%llu half_pct=%.3f strategic_flip_opportunities=%llu strategic_flips=%llu strategic_flip_pct=%.3f split_flip_opportunities=%llu split_flips=%llu split_flip_pct=%.3f half_general=%llu half_castle=%llu half_choke=%llu half_main=%llu half_feeder=%llu qualifier_score=%.3f meta_turns=%d defense_alert_turns=%d hard_defense_alerts_1_5=%d watch_zone_sightings_6_8=%d watch_zone_alerts=%d watch_zone_ignored=%d feints=%d intercepts=%d forks=%d probes=%zu main_stack_idle_max=%d main_stack_progress_moves=%d overconcentrated_turns=%d overconcentrated_idle_turns=%d max_main_stack_army=%d max_main_stack_fraction_pct=%.3f reverse_move_candidates_rejected=%llu two_cycle_detections=%llu short_cycle_detections=%llu dead_end_escape_moves=%llu repeated_cell_penalties=%llu max_main_stack_recent_revisits=%d mean_ms=%.4f p95_ms=%.4f p99_ms=%.4f max_ms=%.4f main_path=",player_id_,decision_ms_.size(),land50_,opp_land50_,my_army50_,opp_army50_,enemy_general_>=0,found_enemy_turn_,approach_turn_[0],approach_turn_[1],approach_turn_[2],approach_turn_[3],castles_built_,movement_decisions_,all_moves_,half_moves_,hp,strategic_flip_opportunities_,strategic_flips_taken_,sf,split_flip_opportunities_,split_flips_taken_,pf,half_from_general_,half_from_castle_,half_from_choke_,half_from_main_,half_from_feeder_,qualifier_defense_score_,meta_turns_,defense_alert_turns_,hard_defense_alerts_,watch_zone_sightings_,watch_zone_alerts_,watch_zone_ignored_,feint_actions_,intercept_actions_,fork_actions_,probe_history_.size(),main_stack_idle_max_,main_stack_progress_moves_,overconcentrated_turns_,overconcentrated_idle_turns_,max_main_stack_army_,max_main_stack_fraction_pct_,reverse_candidates_rejected_,two_cycle_detections_,short_cycle_detections_,dead_end_escape_moves_,repeated_cell_penalties_,max_main_stack_recent_revisits_,mean,pct(.95),pct(.99),t.back());
        for(size_t i=0;i<recent_main_stack_positions_.size();++i)std::fprintf(stderr,"%s%d",i?",":"",recent_main_stack_positions_[i]);
        std::fprintf(stderr," discovery_trace_turn=%d discovery_trace_army=%d discovery_trace_distance=%d discovery_path=",trace_discovery_turn_,trace_main_army_,trace_main_distance_);
        for(size_t i=0;i<discovery_main_path_.size();++i)std::fprintf(stderr,"%s%d",i?",":"",discovery_main_path_[i]);
        std::fputc('\n',stderr);
        std::fprintf(stderr,"[hunter_metrics] signature=%.3f signature_max=%.3f trigger_turn=%d mode_turns=%d first_stack_cell=%d first_stack_army=%d first_stack_distance=%d raider_selected_turn=%d raider_selected_army=%d raider_progress=%d breadcrumb_moves=%d kill_zone_holds=%d convoy_kills=%d gate_castles=%d gate_disconnects=%d general_found_turn=%d general_kill_attempts=%d stack_path=",hunter_signature_score_,hunter_signature_max_,hunter_trigger_turn_,hunter_mode_turns_,hunter_first_stack_cell_,hunter_first_stack_army_,hunter_first_stack_distance_,hunter_raider_selected_turn_,hunter_raider_selected_army_,hunter_raider_progress_moves_,hunter_breadcrumb_moves_,hunter_kill_zone_holds_,hunter_convoy_kills_,hunter_gate_castles_,hunter_gate_disconnects_,hunter_general_found_turn_,hunter_general_kill_attempts_);
        for(size_t i=0;i<hunter_stack_history_.size();++i)std::fprintf(stderr,"%s%d",i?",":"",hunter_stack_history_[i].cell);
        std::fprintf(stderr," raider_path=");for(size_t i=0;i<hunter_raider_path_.size();++i)std::fprintf(stderr,"%s%d",i?",":"",hunter_raider_path_[i]);std::fputc('\n',stderr);
        std::fprintf(stderr,"[contact_metrics] established=%d first_turn=%d anchor=%d staging=%d pressure_turns=%d idle_max=%d front_stack_moves=%d remote_relocations=%d castle_turn=%d castles=%d front_feeders=%d frontier_captures=%d dominance_turns=%d strong_dominance_turns=%d max_largest_distance=%d anchor_path=",contact_established_,first_contact_turn_,contact_anchor_,contact_staging_cell_,contact_pressure_turns_,contact_idle_max_,front_stack_moves_,remote_relocation_moves_,contact_castle_turn_,contact_castles_built_,front_feeder_moves_,enemy_frontier_captures_,dominance_mode_turns_,strong_dominance_turns_,max_largest_contact_distance_);
        for(size_t i=0;i<contact_anchor_history_.size();++i)std::fprintf(stderr,"%s%d",i?",":"",contact_anchor_history_[i]);
        std::fprintf(stderr," front_path=");for(size_t i=0;i<front_stack_path_.size();++i)std::fprintf(stderr,"%s%d",i?",":"",front_stack_path_[i]);
        std::fprintf(stderr," actions=");for(size_t i=0;i<contact_action_trace_.size();++i)std::fprintf(stderr,"%s%s",i?",":"",contact_action_trace_[i].c_str());std::fputc('\n',stderr);
    }
};

constexpr std::array<int,4> Agent::DR;
constexpr std::array<int,4> Agent::DC;

static bool read_grid(std::vector<int>& g) { for(int&x:g)if(std::scanf("%d",&x)!=1)return false;return true; }

int main() {
    int player,h,w;if(std::scanf("%d %d %d",&player,&h,&w)!=3)return 0;Agent agent(player,h,w);Observation o;o.type.resize(h*w);o.owner.resize(h*w);o.army.resize(h*w);
    while(std::scanf("%d %d %d %d %d",&o.turn,&o.my_land,&o.my_army,&o.opp_land,&o.opp_army)==5){if(!read_grid(o.type)||!read_grid(o.owner)||!read_grid(o.army))break;Action a=agent.act(o);std::printf("%d %d %d %d %d\n",a.kind,a.row,a.col,a.dir,a.split);std::fflush(stdout);}agent.report();return 0;
}
