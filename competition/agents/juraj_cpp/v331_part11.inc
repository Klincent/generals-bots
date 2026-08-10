    Action maybe_contact_castle(const Observation&o){
        if(!contact_established_||contact_anchor_<0||contact_castle_built_||hunter_trigger_turn_>=0||castles_built_>=2)return pass();
        if(severe_land_deficit_&&castles_built_>=1)return pass();
        for(int x:id_cell_)if(known_castle_[x]&&o.owner[x]==1){int d=dist_[cell_id_[x]][cell_id_[contact_anchor_]];if(d>=2&&d<=4){contact_castle_built_=true;contact_staging_cell_=x;return pass();}}
        if(o.turn-first_contact_turn_<4)return pass();
        struct C{int x,cost,d;double utility;};std::vector<C> cs;int min_cost=INF;
        for(int x:id_cell_)if(o.owner[x]==1&&o.type[x]==1){int d=dist_[cell_id_[x]][cell_id_[contact_anchor_]];if(d<2||d>4)continue;int cost=castle_cost(x,o);if(o.army[x]<cost+8)continue;int danger=INF;for(auto e:visible_enemy_stacks_)danger=std::min(danger,dist_[cell_id_[x]][cell_id_[e.first]]);if(danger<=2)continue;double u=degree_[x]*24+room_[x]+(articulation_[x]?70:0)-d*8;cs.push_back({x,cost,d,u});min_cost=std::min(min_cost,cost);}
        double best=-1e100;int bx=-1,bc=0,bd=0;for(auto c:cs){
            // Preserve the known-good V2.7.3 contact-castle choice as soon as
            // Hunter-like evidence exists; changing this early blocker was the
            // source of the rejected Hunter regression.
            if(hunter_signature_score_<.05&&c.cost>min_cost+2)continue;
            if(c.utility>best){best=c.utility;bx=c.x;bc=c.cost;bd=c.d;}}
        if(bx<0)return pass();
        bool second=castles_built_==1;contact_castle_built_=true;contact_staging_cell_=bx;contact_castle_turn_=o.turn;++contact_castles_built_;++castles_built_;castle_build_turns_.push_back(o.turn);record_castle(o,bx,bc,min_cost,"contact");if(second){second_castle_turn_=o.turn;second_castle_cost_=bc;second_castle_attack_utility_=best;second_castle_defense_utility_=degree_[bx]*10+(articulation_[bx]?35:0);second_castle_distance_to_front_=bd;}return {2,row(bx),col(bx),0,0};
    }
    Action maybe_second_castle(const Observation&o){
        if(castles_built_!=1||o.turn>700||first_castle_turn_<0||o.turn-first_castle_turn_<150||land_behind_||o.my_army<o.opp_army||!proactive_castle_health(o))return pass();
        int front=enemy_general_>=0?enemy_general_:(contact_anchor_>=0?contact_anchor_:static_cast<int>(std::max_element(enemy_score_.begin(),enemy_score_.end())-enemy_score_.begin()));if(front<0)return pass();
        bool first_far=true;for(int x:id_cell_)if(known_castle_[x]&&o.owner[x]==1&&dist_[cell_id_[x]][cell_id_[front]]<=6)first_far=false;
        if(!enemy_castle_response_pending_&&!strong_dominance_&&!dominance_&&!first_far)return pass();
        struct C{int x,cost,df;double au,du,utility;};std::vector<C> cs;int min_cost=INF,axis=dist_[cell_id_[general_]][cell_id_[front]];
        for(int x:id_cell_)if(o.owner[x]==1&&o.type[x]==1){int df=dist_[cell_id_[x]][cell_id_[front]];if(df<2||df>6)continue;if(dist_[cell_id_[general_]][cell_id_[x]]+df>axis+3)continue;int cost=castle_cost(x,o);if(o.army[x]<cost+10)continue;int danger=INF;for(auto e:visible_enemy_stacks_)danger=std::min(danger,dist_[cell_id_[x]][cell_id_[e.first]]);if(danger<=2)continue;
            if(1200-o.turn<2*cost+100||o.my_army-cost<o.opp_army*9/10)continue;
            double au=130-df*12+degree_[x]*12+room_[x]*.25,du=75-dist_[cell_id_[x]][cell_id_[general_]]*2+(articulation_[x]?45:0)+degree_[x]*7;cs.push_back({x,cost,df,au,du,au+du});min_cost=std::min(min_cost,cost);}
        double best=-1e100,ba=0,bd=0;int bx=-1,bc=0,bdf=0;for(auto c:cs)if(c.cost<=min_cost+2&&c.utility>best){best=c.utility;bx=c.x;bc=c.cost;ba=c.au;bd=c.du;bdf=c.df;}
        if(bx<0)return pass();
        ++castles_built_;castle_build_turns_.push_back(o.turn);record_castle(o,bx,bc,min_cost,"second");second_castle_turn_=o.turn;second_castle_cost_=bc;second_castle_attack_utility_=ba;second_castle_defense_utility_=bd;second_castle_distance_to_front_=bdf;enemy_castle_response_pending_=false;return {2,row(bx),col(bx),0,0};
    }

public:
    Agent(int player_id,int h,int w):player_id_(player_id),h_(h),w_(w),n_(h*w){
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
        update_castle_funding(o);
        intentional_hold_=false;
        if(enemy_general_<0&&turns_since_search_progress_>=3)++exploration_tempo_boost_turns_;
        bool production_valid=false;Action production_fallback=find_safe_neutral_capture(o,production_valid);
        pending_affinity_source_=pending_affinity_dest_=pending_affinity_sink_=-1;
        pending_rear_source_=pending_rear_dest_=-1;
        pending_frontier_feed_source_=pending_frontier_feed_dest_=-1;
        pending_edge_source_=pending_edge_dest_=-1;
        pending_v3_source_=pending_v3_dest_=-1;pending_v3_reason_=pending_v3_branch_=-1;pending_v3_secondary_value_=0;v3_action_label_="NONE";approach_changed_this_turn_=false;approach_block_castle_feed_=false;
        Action fallback=pass(), result=fallback; bool tactical=false;
        result=immediate_tactics(o,tactical);
        if(!tactical)result=hunter_counterattack(o,tactical);
        if(!tactical)result=defense_emergency(o,tactical);
        if(!tactical){bool positioned=false;Action a=hunter_suspicion_position(o,positioned);if(positioned){result=a;tactical=true;}}
        if(!tactical)result=high_confidence_capture(o,tactical);
        if(tactical&&approach_threat_active_)v3_action_label_="APPROACH_TACTICAL_OVERRIDE";
        if(!tactical&&enemy_general_<0){bool positioned=false;Action a=approach_threat_position(o,positioned);if(positioned){result=a;tactical=true;}}
        if(!tactical){bool positioned=false;Action a=hunter_warning_position(o,positioned);if(positioned){result=a;tactical=true;}}
        bool deadline_guard=false,legality_guard=false,strategic_empty=false;
        if(!tactical&&Clock::now()<hard-std::chrono::milliseconds(5)){
            Action planned=maybe_v31_castle_action(o);if(planned.kind!=1)result=planned;else if(v3_castle_count_==0){Action build=maybe_contact_castle(o);result=build.kind==2?build:choose_strategic(o);}else result=choose_strategic(o);
        }else if(!tactical)deadline_guard=true;
        strategic_empty=result.kind==1&&!intentional_hold_;bool used_productive_fallback=false;
        if(result.kind==1&&!intentional_hold_){int replacement=0;Action productive=productive_fallback(o,production_fallback,production_valid,replacement);if(productive.kind!=1){result=productive;used_productive_fallback=true;++productive_fallback_actions_;if(replacement==1)++passes_replaced_expansion_;if(replacement==2){++passes_replaced_frontier_feed_;pending_frontier_feed_source_=cell(result.row,result.col);pending_frontier_feed_dest_=neighbor(pending_frontier_feed_source_,result.dir);}}}
        // Final legality guard always leaves time for a protocol-safe pass.
        if(result.kind==0){int x=cell(result.row,result.col),y=neighbor(x,result.dir);if(!inside(result.row,result.col)||y<0||!passable_[y]||o.owner[x]!=1||o.army[x]<=1){result=fallback;legality_guard=true;}}
        if(result.kind==1){++passes_total_;bool movable=false;for(int x:id_cell_)if(legal_source(o,x)){movable=true;break;}if(intentional_hold_)++passes_intentional_hold_;else if(!movable)++passes_no_movable_army_;else if(deadline_guard)++passes_deadline_guard_;else if(legality_guard)++passes_legality_guard_;else if(strategic_empty)++passes_strategic_empty_;else ++passes_no_safe_action_;}
        bool forced=tactical&&(required_defense_>0||hunter_trigger_turn_>=0);update_exploration_tempo(o,result,forced);update_contact_metrics(o,result,tactical&&required_defense_>0);update_main_stack_metrics(o,result,tactical&&required_defense_>0);
        if(result.kind==0){int x=cell(result.row,result.col),y=neighbor(x,result.dir);if(x==planned_castle_[0]&&c1_first_funded_turn_>=0&&planned_castle_built_turn_[0]<0)c1_funded_used_tactically_=true;bool frontier_feed=x==pending_frontier_feed_source_&&y==pending_frontier_feed_dest_;bool edge_drain=x==pending_edge_source_&&y==pending_edge_dest_;bool v3=x==pending_v3_source_&&y==pending_v3_dest_;if(frontier_feed)++frontier_feed_moves_;if(edge_drain){++edge_surplus_moves_;edge_surplus_army_moved_+=o.army[x]-1;last_edge_drain_turn_=o.turn;}if(v3){if(pending_v3_branch_>=0){++branch_actions_[pending_v3_branch_];if(o.owner[y]==0)++branch_land_gain_[pending_v3_branch_];}v3_packet_path_.push_back(x);v3_packet_path_.push_back(y);while(v3_packet_path_.size()>12)v3_packet_path_.erase(v3_packet_path_.begin());if(result.split){++v3_half_reason_[std::max(0,pending_v3_reason_)];v3_half_source_sum_+=o.army[x];v3_half_source_min_=std::min(v3_half_source_min_,o.army[x]);v3_half_secondary_sum_+=(long long)pending_v3_secondary_value_;if(v3_second_job(o,x,result.dir))++v3_half_second_job_;else ++v3_half_no_job_;}else ++v3_full_reason_[std::max(0,pending_v3_reason_)];}++movement_decisions_;if(o.owner[y]==0){++neutral_capture_actions_;++neutral_expansion_moves_;if(o.turn<300)++neutral_expansion_before_300_;if(o.turn<400)++neutral_expansion_before_400_;int until=50-o.turn%50;if(until<=10)++neutral_captures_10_before_tick_;}else if(!used_productive_fallback&&frontier_feed){}else if(!used_productive_fallback&&enemy_general_<0&&(strategy_==SEARCH_GENERAL||strategy_==QUALIFIER_PROBE))++normal_search_actions_;else if(!used_productive_fallback&&(o.owner[y]==2||(contact_anchor_>=0&&dist_[cell_id_[y]][cell_id_[contact_anchor_]]<dist_[cell_id_[x]][cell_id_[contact_anchor_]])||(enemy_general_>=0&&dist_[cell_id_[y]][cell_id_[enemy_general_]]<dist_[cell_id_[x]][cell_id_[enemy_general_]])))++normal_offense_actions_;else if(!used_productive_fallback)++normal_economy_actions_;if(result.split){++half_moves_;++half_by_mode_[strategy_];if(x==general_)++half_from_general_;if(known_castle_[x])++half_from_castle_;if(articulation_[x])++half_from_choke_;if(x==main_stack_)++half_from_main_;else ++half_from_feeder_;}else ++all_moves_;}
        if(approach_changed_this_turn_){++approach_selected_action_changes_;if(approach_block_castle_feed_)v3_action_label_="APPROACH_DELAY_C1";else if(v3_action_label_!="APPROACH_CONSOLIDATE"&&v3_action_label_!="APPROACH_TACTICAL_OVERRIDE"&&v3_action_label_!="APPROACH_ALLOW_C1")v3_action_label_="APPROACH_KEEP_REACTION";}
        if(o.turn==50||o.turn==100||o.turn==150||o.turn==200||o.turn==250||o.turn==300||o.turn==350||o.turn==400){std::array<int,3> bl{};for(int x:id_cell_)if(o.owner[x]==1){int b=v3_branch(x);if(b>=0)++bl[b];}v3_snapshots_.push_back({o.turn,o.my_land,o.my_army,o.opp_land,o.opp_army,castles_built_,planned_castle_[0]>=0?o.army[planned_castle_[0]]:0,planned_castle_[1]>=0?o.army[planned_castle_[1]]:0,bl});}
        if(std::getenv("JURAJ_V3_TRACE")&&v3_action_label_!="NONE")std::fprintf(stderr,"[v3_action] turn=%d label=%s c1=%d/%d c2=%d/%d\n",o.turn,v3_action_label_.c_str(),planned_castle_[0]>=0?o.army[planned_castle_[0]]:0,planned_castle_cost_[0],planned_castle_[1]>=0?o.army[planned_castle_[1]]:0,planned_castle_cost_[1]);
        if(o.turn==200||o.turn==300||o.turn==400||o.turn==600||o.turn==800||o.turn==1000){int excess=0;for(int x:id_cell_)if(o.owner[x]==1){int edge=std::min({row(x),h_-1-row(x),col(x),w_-1-col(x)});if(edge<=1||degree_[x]==1||terminal_depth_[x]>0)excess+=std::max(0,o.army[x]-1);}edge_excess_snapshots_.push_back({o.turn,excess});}
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
        int total=my_army_hist_.empty()?0:my_army_hist_.back();double rear_pct=total?100.0*rear_army_total_/total:0;
        std::fprintf(stderr,"[affinity_metrics] rear_army=%lld rear_pct=%.3f rear_excess=%lld evacuated_army=%lld to_attack=%d to_defense=%d edge_evacuations=%d corner_evacuations=%d dead_end_evacuations=%d active_edge_exemptions=%d affinity_moves=%d affinity_gain=%.3f enemy_castle_response_triggers=%d response_pending=%d second_castle_turn=%d second_castle_cost=%d second_castle_attack_utility=%.3f second_castle_defense_utility=%.3f second_castle_distance_front=%d snapshots=",rear_army_total_,rear_pct,rear_excess_army_,rear_evacuated_army_,rear_to_attack_moves_,rear_to_defense_moves_,edge_evacuations_,corner_evacuations_,dead_end_evacuations_,active_edge_exemptions_,affinity_moves_,affinity_gain_total_,enemy_castle_response_triggers_,enemy_castle_response_pending_,second_castle_turn_,second_castle_cost_,second_castle_attack_utility_,second_castle_defense_utility_,second_castle_distance_to_front_);
        for(size_t i=0;i<affinity_snapshots_.size();++i){auto s=affinity_snapshots_[i];std::fprintf(stderr,"%s%d:%d:%d:%d:%d",i?",":"",s.turn,s.total,s.rear,s.attack,s.defense);}std::fprintf(stderr," evacuations=");
        for(size_t i=0;i<evacuation_traces_.size();++i){auto e=evacuation_traces_[i];std::fprintf(stderr,"%s%d:%d:%d:%.1f:%d:%s",i?",":"",e.turn,e.cell,e.army,e.affinity,e.dest,e.sink==0?"ATTACK":"DEFENSE");}std::fputc('\n',stderr);
        std::fprintf(stderr,"[field_metrics] traces=");for(size_t i=0;i<field_traces_.size();++i){auto f=field_traces_[i];std::fprintf(stderr,"%s%d|rear=%d:%.1f|old=%d:%.1f|stage=%d:%.1f|front=%d:%.1f|enemy=%d:%.1f",i?",":"",f.turn,f.rear,f.ar,f.old_stage,f.ao,f.stage,f.as,f.front,f.af,f.enemy,f.ae);}std::fputc('\n',stderr);
        std::fprintf(stderr,"[production_metrics] land_deficit_turns=%lld severe_land_deficit_turns=%lld neutral_expansion_moves=%lld neutral_before_300=%lld neutral_before_400=%lld neutral_10_before_tick=%lld rear_surplus_moves=%lld rear_surplus_army_moved=%lld affinity_action_candidates=0 snapshots=",land_deficit_turns_,severe_land_deficit_turns_,neutral_expansion_moves_,neutral_expansion_before_300_,neutral_expansion_before_400_,neutral_captures_10_before_tick_,rear_surplus_moves_,rear_surplus_army_moved_);
        for(size_t i=0;i<production_snapshots_.size();++i){auto s=production_snapshots_[i];std::fprintf(stderr,"%s%d:%d:%d:%d:%d",i?",":"",s.turn,s.my_land,s.opp_land,s.my_army,s.opp_army);}std::fputc('\n',stderr);
