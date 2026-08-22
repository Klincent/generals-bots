    void record_castle(const Observation&o,int x,int cost,int min_cost,const char* type){
        castle_records_.push_back({o.turn,x,cost,min_cost,std::abs(row(x)-row(general_))+std::abs(col(x)-col(general_)),hunter_signature_score_,o.my_land,o.opp_land,o.my_army,o.opp_army,type});
        if(first_castle_turn_<0)first_castle_turn_=o.turn;
    }
    bool proactive_castle_health(const Observation&o)const{
        if(production_emergency_||required_defense_>0||hunter_trigger_turn_>=0||hunter_signature_score_>=.20)return false;
        bool healthy=(o.my_land*10>=o.opp_land*9&&o.my_army*10>=o.opp_army*9)||dominance_;
        if(!healthy)return false;
        for(auto e:visible_enemy_stacks_)if(e.second>=std::max(20,o.my_army/4)&&dist_[cell_id_[e.first]][cell_id_[general_]]<=9)return false;
        return true;
    }
    Action maybe_build(const Observation& o) {
        if(castles_built_>=1||enemy_general_>=0||o.turn<250||o.turn>550||mode_[ATTACK]>.30||!proactive_castle_health(o))return pass();
        int target=static_cast<int>(std::max_element(enemy_score_.begin(),enemy_score_.end())-enemy_score_.begin());
        if(target<0||enemy_score_[target]<=0)return pass();
        struct C{int x,cost;double utility;};std::vector<C> cs;int axis=dist_[cell_id_[general_]][cell_id_[target]],min_cost=INF;
        for(int x:id_cell_)if(o.owner[x]==1&&o.type[x]==1){int md=std::abs(row(x)-row(general_))+std::abs(col(x)-col(general_));if(md<5)continue;int dc=dist_[cell_id_[general_]][cell_id_[x]],dt=dist_[cell_id_[x]][cell_id_[target]];if(dc+dt>axis+3||dt>=axis)continue;int cost=castle_cost(x,o);if(1200-o.turn<2*cost+100||o.army[x]<cost+10||o.my_army-cost<o.opp_army*9/10)continue;int danger=INF;for(auto e:visible_enemy_stacks_)danger=std::min(danger,dist_[cell_id_[x]][cell_id_[e.first]]);if(danger<6)continue;double u=(articulation_[x]?40:0)+room_[x]+degree_[x]*10-dt*2+(md>=7?30:0);cs.push_back({x,cost,u});min_cost=std::min(min_cost,cost);}
        int bx=-1,bc=0;double best=-1e100;for(auto c:cs)if(c.cost<=min_cost+2&&c.utility>best){best=c.utility;bx=c.x;bc=c.cost;}
        if(bx>=0){++castles_built_;castle_build_turns_.push_back(o.turn);record_castle(o,bx,bc,min_cost,"proactive");return {2,row(bx),col(bx),0,0};}return pass();
    }
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
        update_known_mobilization(o);
        update_castle_funding(o);
        intentional_hold_=false;
        if(enemy_general_<0&&turns_since_search_progress_>=3)++exploration_tempo_boost_turns_;
        bool production_valid=false;Action production_fallback=find_safe_neutral_capture(o,production_valid);
        pending_affinity_source_=pending_affinity_dest_=pending_affinity_sink_=-1;
        pending_rear_source_=pending_rear_dest_=-1;
        pending_frontier_feed_source_=pending_frontier_feed_dest_=-1;
        pending_edge_source_=pending_edge_dest_=-1;
        pending_v3_source_=pending_v3_dest_=-1;pending_v3_reason_=pending_v3_branch_=-1;pending_v3_secondary_value_=0;pending_rear_drain_source_=pending_rear_drain_dest_=pending_rear_drain_sink_=-1;pending_rear_drain_kind_=0;v3_action_label_="NONE";approach_changed_this_turn_=false;approach_block_castle_feed_=false;approach_delayed_castle_index_=-1;
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
        if(result.kind==0){int x=cell(result.row,result.col),y=neighbor(x,result.dir),carried=std::min(mobilized_credit_[x],o.army[x]-1);mobilized_credit_[x]-=carried;mobilized_credit_[y]+=carried;for(int i=0;i<3;++i)if(x==planned_castle_[i]&&planned_first_funded_[i]>=0&&planned_castle_built_turn_[i]<0)++planned_tactical_use_[i];if(x==planned_castle_[0]&&c1_first_funded_turn_>=0&&planned_castle_built_turn_[0]<0)c1_funded_used_tactically_=true;bool frontier_feed=x==pending_frontier_feed_source_&&y==pending_frontier_feed_dest_;bool edge_drain=x==pending_edge_source_&&y==pending_edge_dest_;bool v3=x==pending_v3_source_&&y==pending_v3_dest_,rear=x==pending_rear_drain_source_&&y==pending_rear_drain_dest_;if(frontier_feed)++frontier_feed_moves_;if(edge_drain){++edge_surplus_moves_;edge_surplus_army_moved_+=o.army[x]-1;last_edge_drain_turn_=o.turn;}if(rear){int moved=o.army[x]-1,edge=std::min({row(x),h_-1-row(x),col(x),w_-1-col(x)});++rear_drain_actions_;last_rear_drain_turn_=o.turn;rear_drain_army_+=moved;rear_source_sum_+=o.army[x];rear_moved_sum_+=moved;rear_progress_sum_+=dist_[cell_id_[x]][cell_id_[pending_rear_drain_sink_]]-dist_[cell_id_[y]][cell_id_[pending_rear_drain_sink_]];rear_source_bins_[o.army[x]<=2?0:(o.army[x]==3?1:(o.army[x]==4?2:3))]++;if(pending_rear_drain_kind_==3){int newly=std::max(0,moved-carried);mobilized_credit_[y]+=newly;mobilized_to_attack_+=newly;++rear_drain_attack_;}else if(pending_rear_drain_kind_==2){mobilized_to_defense_+=moved;++rear_drain_defense_;}else ++rear_drain_attack_;if(edge<=1)++rear_drain_edge_;if(degree_[x]<=1||terminal_depth_[x]>0)++rear_drain_terminal_;v3_action_label_=pending_rear_drain_kind_==3?"KNOWN_GENERAL_MOBILIZE":(pending_rear_drain_kind_==2?"REAR_DRAIN_DEFENSE":"REAR_DRAIN_ATTACK");}if(v3){if(pending_v3_branch_>=0){++branch_actions_[pending_v3_branch_];if(o.owner[y]==0)++branch_land_gain_[pending_v3_branch_];}v3_packet_path_.push_back(x);v3_packet_path_.push_back(y);while(v3_packet_path_.size()>12)v3_packet_path_.erase(v3_packet_path_.begin());if(result.split){++v3_half_reason_[std::max(0,pending_v3_reason_)];v3_half_source_sum_+=o.army[x];v3_half_source_min_=std::min(v3_half_source_min_,o.army[x]);v3_half_secondary_sum_+=(long long)pending_v3_secondary_value_;if(v3_second_job(o,x,result.dir))++v3_half_second_job_;else ++v3_half_no_job_;}else ++v3_full_reason_[std::max(0,pending_v3_reason_)];}++movement_decisions_;if(o.owner[y]==0){++neutral_capture_actions_;++neutral_expansion_moves_;if(o.turn<300)++neutral_expansion_before_300_;if(o.turn<400)++neutral_expansion_before_400_;int until=50-o.turn%50;if(until<=10)++neutral_captures_10_before_tick_;}else if(!used_productive_fallback&&frontier_feed){}else if(!used_productive_fallback&&enemy_general_<0&&(strategy_==SEARCH_GENERAL||strategy_==QUALIFIER_PROBE))++normal_search_actions_;else if(!used_productive_fallback&&(o.owner[y]==2||(contact_anchor_>=0&&dist_[cell_id_[y]][cell_id_[contact_anchor_]]<dist_[cell_id_[x]][cell_id_[contact_anchor_]])||(enemy_general_>=0&&dist_[cell_id_[y]][cell_id_[enemy_general_]]<dist_[cell_id_[x]][cell_id_[enemy_general_]])))++normal_offense_actions_;else if(!used_productive_fallback)++normal_economy_actions_;if(result.split){++half_moves_;++half_by_mode_[strategy_];if(x==general_)++half_from_general_;if(known_castle_[x])++half_from_castle_;if(articulation_[x])++half_from_choke_;if(x==main_stack_)++half_from_main_;else ++half_from_feeder_;}else ++all_moves_;}
        if(approach_changed_this_turn_){++approach_selected_action_changes_;if(approach_block_castle_feed_)v3_action_label_="APPROACH_DELAY_C"+std::to_string(approach_delayed_castle_index_+1);else if(v3_action_label_!="APPROACH_CONSOLIDATE"&&v3_action_label_!="APPROACH_TACTICAL_OVERRIDE"&&v3_action_label_.rfind("APPROACH_ALLOW_C",0)!=0)v3_action_label_="APPROACH_KEEP_REACTION";}
        if(o.turn==50||o.turn==100||o.turn==150||o.turn==200||o.turn==250||o.turn==300||o.turn==350||o.turn==400||o.turn==600){std::array<int,3> bl{};for(int x:id_cell_)if(o.owner[x]==1){int b=v3_branch(x);if(b>=0)++bl[b];}v3_snapshots_.push_back({o.turn,o.my_land,o.my_army,o.opp_land,o.opp_army,castles_built_,planned_castle_[0]>=0?o.army[planned_castle_[0]]:0,planned_castle_[1]>=0?o.army[planned_castle_[1]]:0,bl});}
        if(o.turn==100||o.turn==150||o.turn==200||o.turn==250||o.turn==300||o.turn==400||o.turn==600||(first_contact_turn_>=0&&(o.turn==first_contact_turn_+25||o.turn==first_contact_turn_+50))){auto s=stranded_snapshot(o);max_stranded_surplus_=std::max(max_stranded_surplus_,s.total);stranded_snapshots_.push_back(s);}
        if(std::getenv("JURAJ_V3_TRACE")&&v3_action_label_!="NONE")std::fprintf(stderr,"[v3_action] turn=%d label=%s c1=%d/%d c2=%d/%d c3=%d/%d\n",o.turn,v3_action_label_.c_str(),planned_castle_[0]>=0?o.army[planned_castle_[0]]:0,planned_castle_cost_[0],planned_castle_[1]>=0?o.army[planned_castle_[1]]:0,planned_castle_cost_[1],planned_castle_[2]>=0?o.army[planned_castle_[2]]:0,planned_castle_cost_[2]);
        if(o.turn==200||o.turn==300||o.turn==400||o.turn==600||o.turn==800||o.turn==1000){int excess=0;for(int x:id_cell_)if(o.owner[x]==1){int edge=std::min({row(x),h_-1-row(x),col(x),w_-1-col(x)});if(edge<=1||degree_[x]==1||terminal_depth_[x]>0)excess+=std::max(0,o.army[x]-1);}edge_excess_snapshots_.push_back({o.turn,excess});}
        auto end=Clock::now();decision_ms_.push_back(std::chrono::duration<double,std::milli>(end-begin).count());return result;
    }
    void report() const {
