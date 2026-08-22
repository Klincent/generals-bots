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
        {int target=attack_direction_target();if(target>=0){attack_direction_cell_=target;if(attack_direction_turn_<0)attack_direction_turn_=o.turn;}}
        update_castle_funding(o);
        intentional_hold_=false;
        if(enemy_general_<0&&turns_since_search_progress_>=3)++exploration_tempo_boost_turns_;
        bool production_valid=false;Action production_fallback=find_safe_neutral_capture(o,production_valid);
        pending_affinity_source_=pending_affinity_dest_=pending_affinity_sink_=-1;
        pending_rear_source_=pending_rear_dest_=-1;
        pending_frontier_feed_source_=pending_frontier_feed_dest_=-1;
        pending_edge_source_=pending_edge_dest_=-1;
        pending_v3_source_=pending_v3_dest_=-1;pending_v3_reason_=pending_v3_branch_=-1;pending_v3_secondary_value_=0;pending_rear_drain_source_=pending_rear_drain_dest_=pending_rear_drain_sink_=-1;pending_rear_drain_kind_=0;pending_belt_release_=false;pending_belt_layer_=0;v3_action_label_="NONE";approach_changed_this_turn_=false;approach_block_castle_feed_=false;approach_delayed_castle_index_=-1;
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
            Action planned=maybe_v31_castle_action(o);if(planned.kind==2)result=planned;else{bool mandatory=false;Action rear=mandatory_rear_hemisphere(o,mandatory);if(mandatory)result=rear;else{bool release=false;Action forward=release_belt_surplus(o,release);if(release)result=forward;else if(planned.kind==0)result=planned;else if(v3_castle_count_==0){Action build=maybe_contact_castle(o);result=build.kind==2?build:choose_strategic(o);}else result=choose_strategic(o);}}
        }else if(!tactical)deadline_guard=true;
        strategic_empty=result.kind==1&&!intentional_hold_;bool used_productive_fallback=false;
        if(result.kind==1&&!intentional_hold_){int replacement=0;Action productive=productive_fallback(o,production_fallback,production_valid,replacement);if(productive.kind!=1){result=productive;used_productive_fallback=true;++productive_fallback_actions_;if(replacement==1)++passes_replaced_expansion_;if(replacement==2){++passes_replaced_frontier_feed_;pending_frontier_feed_source_=cell(result.row,result.col);pending_frontier_feed_dest_=neighbor(pending_frontier_feed_source_,result.dir);}}}
        // Final legality guard always leaves time for a protocol-safe pass.
        if(result.kind==0){int x=cell(result.row,result.col),y=neighbor(x,result.dir);if(!inside(result.row,result.col)||y<0||!passable_[y]||o.owner[x]!=1||o.army[x]<=1){result=fallback;legality_guard=true;}}
        if(result.kind==1){++passes_total_;bool movable=false;for(int x:id_cell_)if(legal_source(o,x)){movable=true;break;}if(intentional_hold_)++passes_intentional_hold_;else if(!movable)++passes_no_movable_army_;else if(deadline_guard)++passes_deadline_guard_;else if(legality_guard)++passes_legality_guard_;else if(strategic_empty)++passes_strategic_empty_;else ++passes_no_safe_action_;}
        bool forced=tactical&&(required_defense_>0||hunter_trigger_turn_>=0);update_exploration_tempo(o,result,forced);update_main_stack_metrics(o,result,forced);update_contact_metrics(o,result,forced);
        if(result.kind==0){int sx=cell(result.row,result.col),sy=neighbor(sx,result.dir),moved=result.split?o.army[sx]/2:o.army[sx]-1;if(pending_rear_drain_source_==sx&&pending_rear_drain_dest_==sy){++rear_drain_actions_;rear_drain_army_+=moved;rear_source_sum_+=o.army[sx];rear_moved_sum_+=moved;rear_progress_sum_+=std::max(0,dist_[cell_id_[sx]][cell_id_[pending_rear_drain_sink_]]-dist_[cell_id_[sy]][cell_id_[pending_rear_drain_sink_]]);if(o.army[sx]==2)++rear_source_bins_[0];else if(o.army[sx]==3)++rear_source_bins_[1];else if(o.army[sx]==4)++rear_source_bins_[2];else ++rear_source_bins_[3];if(pending_rear_drain_kind_==1)++rear_drain_attack_;else if(pending_rear_drain_kind_==2)++rear_drain_defense_;if(std::min({row(sx),h_-1-row(sx),col(sx),w_-1-col(sx)})<=1)++rear_drain_edge_;if(degree_[sx]<=1||terminal_depth_[sx]>0)++rear_drain_terminal_;last_rear_drain_turn_=o.turn;if(pending_rear_drain_kind_==3){int available=std::min(moved,std::max(0,o.army[sx]-mobilization_reserve(sx)));mobilized_to_attack_+=available;if((int)mobilized_credit_.size()==n_)mobilized_credit_[sy]+=available;}if(pending_rear_drain_kind_==4){++mandatory_rear_actions_;mandatory_rear_army_+=moved;mandatory_rear_source_sum_+=o.army[sx];largest_rear_source_=std::max(largest_rear_source_,o.army[sx]);}}
            if(pending_belt_release_){++belt_attack_actions_;belt_attack_army_+=moved;if(previous_direction_threat_&&!approach_threat_active_)++threat_clear_release_actions_;if(o.owner[sy]==2)++counterattack_release_actions_;}
            previous_direction_threat_=approach_threat_active_;
        }
        int tdir=attack_direction_target();if(tdir>=0&&(rear_hemisphere_snapshots_.empty()||o.turn==attack_direction_turn_||o.turn-attack_direction_turn_==10||o.turn-attack_direction_turn_==25||o.turn-attack_direction_turn_==50||o.turn-attack_direction_turn_==100))rear_hemisphere_snapshots_.push_back(rear_hemisphere_snapshot(o,tdir));
        if(o.turn%50==0){auto ss=stranded_snapshot(o);stranded_snapshots_.push_back(ss);max_stranded_surplus_=std::max(max_stranded_surplus_,ss.total);}
        if(o.turn==50||o.turn==100||o.turn==150||o.turn==200||o.turn==250||o.turn==300||o.turn==400){int c1=planned_castle_[0]>=0&&o.owner[planned_castle_[0]]==1?o.army[planned_castle_[0]]:0,c2=planned_castle_[1]>=0&&o.owner[planned_castle_[1]]==1?o.army[planned_castle_[1]]:0;V3Snapshot s{o.turn,o.my_land,o.my_army,o.opp_land,o.opp_army,castles_built_,c1,c2,{}};for(int b=0;b<3;++b)for(int x:id_cell_)if(o.owner[x]==1&&v3_branch(x)==b)++s.branch_land[b];v3_snapshots_.push_back(s);}
        if(result.kind==0){int sx=cell(result.row,result.col),sy=neighbor(sx,result.dir);if(sx==pending_v3_source_&&sy==pending_v3_dest_){if(pending_v3_branch_>=0&&pending_v3_branch_<3)++branch_actions_[pending_v3_branch_];if(o.owner[sy]==0&&pending_v3_branch_>=0&&pending_v3_branch_<3)++branch_land_gain_[pending_v3_branch_];v3_objective_=pending_v3_reason_;v3_packet_path_.push_back(sy);if(v3_packet_path_.size()>12)v3_packet_path_.erase(v3_packet_path_.begin());}}
        if(approach_changed_this_turn_)++approach_selected_action_changes_;
        auto end=Clock::now(); decision_ms_.push_back(std::chrono::duration<double,std::milli>(end-begin).count());
        if(const char*tr=std::getenv("JURAJ_V3_TRACE"))if(*tr)std::fprintf(stderr,"[v3_action] turn=%d label=%s kind=%d row=%d col=%d dir=%d split=%d\n",o.turn,v3_action_label_.c_str(),result.kind,result.row,result.col,result.dir,result.split);
        return result;
    }
    void report() {
        if (decision_ms_.empty()) return;
        auto v=decision_ms_;std::sort(v.begin(),v.end());auto pct=[&](double p){size_t i=std::min(v.size()-1,(size_t)std::floor(p*(v.size()-1)));return v[i];};
        std::fprintf(stderr,"[juraj] decisions=%zu mean_ms=%.3f p95_ms=%.3f p99_ms=%.3f max_ms=%.3f all=%llu half=%llu half_gen=%llu half_castle=%llu half_choke=%llu half_main=%llu half_feed=%llu flips=%llu/%llu split_flips=%llu/%llu land50=%d opp_land50=%d army50=%d opp_army50=%d found=%d a10=%d a5=%d a2=%d a1=%d hunter_max=%.3f hunter_trigger=%d hunter_turns=%d raider_turn=%d raider_army=%d raider_moves=%d breadcrumb=%d holds=%d kills=%d gate_castles=%d gate_disconnects=%d hunter_general_found=%d kill_attempts=%d\n",v.size(),std::accumulate(v.begin(),v.end(),0.0)/v.size(),pct(.95),pct(.99),v.back(),all_moves_,half_moves_,half_from_general_,half_from_castle_,half_from_choke_,half_from_main_,half_from_feeder_,strategic_flips_taken_,strategic_flip_opportunities_,split_flips_taken_,split_flip_opportunities_,land50_,opp_land50_,my_army50_,opp_army50_,found_enemy_turn_,approach_turn_[0],approach_turn_[1],approach_turn_[2],approach_turn_[3],hunter_signature_max_,hunter_trigger_turn_,hunter_mode_turns_,hunter_raider_selected_turn_,hunter_raider_selected_army_,hunter_raider_progress_moves_,hunter_breadcrumb_moves_,hunter_kill_zone_holds_,hunter_convoy_kills_,hunter_gate_castles_,hunter_gate_disconnects_,hunter_general_found_turn_,hunter_general_kill_attempts_);
        std::fprintf(stderr,"[v34_rear_hemisphere] direction_turn=%d target=%d mandatory=%lld evacuated=%lld largest_source=%d mean_source=%.2f belt_to_attack_actions=%lld belt_to_attack_army=%lld threat_clear_release=%lld counterattack_release=%lld\n",attack_direction_turn_,attack_direction_cell_,mandatory_rear_actions_,mandatory_rear_army_,largest_rear_source_,mandatory_rear_actions_?(double)mandatory_rear_source_sum_/mandatory_rear_actions_:0,belt_attack_actions_,belt_attack_army_,threat_clear_release_actions_,counterattack_release_actions_);
        std::fprintf(stderr,"[v34_castles] C1:%d/%d C2:%d/%d C3:%d/%d\n",planned_castle_[0],planned_castle_built_turn_[0],planned_castle_[1],planned_castle_built_turn_[1],planned_castle_[2],planned_castle_built_turn_[2]);
    }
};

constexpr std::array<int,4> Agent::DR;
constexpr std::array<int,4> Agent::DC;

static bool read_grid(std::vector<int>& g) { for(int&x:g)if(std::scanf("%d",&x)!=1)return false;return true; }

int main() {
    int player,h,w;if(std::scanf("%d %d %d",&player,&h,&w)!=3)return 0;Agent agent(player,h,w);Observation o;o.type.resize(h*w);o.owner.resize(h*w);o.army.resize(h*w);
    while(std::scanf("%d %d %d %d %d",&o.turn,&o.my_land,&o.my_army,&o.opp_land,&o.opp_army)==5){if(!read_grid(o.type)||!read_grid(o.owner)||!read_grid(o.army))break;Action a=agent.act(o);std::printf("%d %d %d %d %d\n",a.kind,a.row,a.col,a.dir,a.split);std::fflush(stdout);}agent.report();return 0;
}
