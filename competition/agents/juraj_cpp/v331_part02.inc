    int second_castle_distance_to_front_ = -1;
    long long rear_army_total_ = 0, rear_excess_army_ = 0, rear_evacuated_army_ = 0;
    int rear_to_attack_moves_ = 0, rear_to_defense_moves_ = 0, edge_evacuations_ = 0;
    int corner_evacuations_ = 0, dead_end_evacuations_ = 0, active_edge_exemptions_ = 0;
    int affinity_moves_ = 0;double affinity_gain_total_ = 0;
    int pending_affinity_source_ = -1, pending_affinity_dest_ = -1, pending_affinity_sink_ = -1;
    struct AffinitySnapshot {int turn,total,rear,attack,defense;};
    struct EvacuationTrace {int turn,cell,army,dest,sink;double affinity;};
    std::vector<AffinitySnapshot> affinity_snapshots_;
    std::vector<EvacuationTrace> evacuation_traces_;
    struct FieldTrace {int turn,rear,old_stage,stage,front,enemy;double ar,ao,as,af,ae;};
    std::vector<FieldTrace> field_traces_;
    int old_staging_cell_ = -1, last_field_stage_ = -1, last_field_enemy_ = -1;
    bool land_deficit_ = false, severe_land_deficit_ = false;
    bool land_behind_ = false, production_emergency_ = false, intentional_hold_ = false;
    long long land_deficit_turns_ = 0, severe_land_deficit_turns_ = 0;
    long long neutral_expansion_moves_ = 0, neutral_expansion_before_300_ = 0;
    long long neutral_expansion_before_400_ = 0, neutral_captures_10_before_tick_ = 0;
    long long rear_surplus_moves_ = 0, rear_surplus_army_moved_ = 0;
    int pending_rear_source_ = -1, pending_rear_dest_ = -1;
    struct ProductionSnapshot { int turn, my_land, opp_land, my_army, opp_army; };
    std::vector<ProductionSnapshot> production_snapshots_;
    long long passes_total_=0,passes_intentional_hold_=0,passes_no_movable_army_=0;
    long long passes_no_safe_action_=0,passes_deadline_guard_=0,passes_legality_guard_=0;
    long long passes_strategic_empty_=0,passes_replaced_expansion_=0,passes_replaced_frontier_feed_=0;
    long long frontier_feed_moves_=0;
    long long production_emergency_turns_=0,normal_offense_actions_=0,normal_search_actions_=0;
    long long normal_economy_actions_=0,neutral_capture_actions_=0,productive_fallback_actions_=0;
    int turns_since_search_progress_=0,consecutive_low_info_contact_=0;
    long long exploration_tempo_boost_turns_=0,contact_repetition_penalties_=0;
    long long search_progress_actions_=0,meaningful_fog_reveal_actions_=0;
    int pending_frontier_feed_source_=-1,pending_frontier_feed_dest_=-1;
    long long edge_surplus_moves_=0,edge_surplus_army_moved_=0,edge_large_sources_seen_=0;
    int pending_edge_source_=-1,pending_edge_dest_=-1,last_edge_drain_turn_=-1000;
    struct EdgeSnapshot {int turn,excess;};
    std::vector<EdgeSnapshot> edge_excess_snapshots_;
    struct CastleRecord {int turn,cell,cost,min_cost,md_general;double hunter;int my_land,opp_land,my_army,opp_army;std::string type;};
    std::vector<CastleRecord> castle_records_;
    int first_castle_turn_=-1;

    // V3 static-route layer.  These fields are constructed once and never
    // derive from changing ownership or armies.
    struct NavCell { bool passable=false,articulation=false;unsigned char sector=0,first_hop_mask=0,degree=0;unsigned short dist_from_general=0,sector_route_mask=0,route_load=0,breakthrough_gain=0;double route_flow=0,static_route_value=0; };
    std::vector<NavCell> nav_;
    std::array<std::vector<int>,9> sector_dist_,sector_next_dir_;
    std::vector<std::array<double,4>> edge_route_flow_;
    std::array<int,3> primary_branch_dir_{{-1,-1,-1}};
    int primary_branch_count_=0;
    std::array<int,2> planned_castle_{{-1,-1}},planned_castle_cost_{{0,0}},planned_castle_built_turn_{{-1,-1}};
    int v3_split_policy_=2,v3_castle_count_=2;
    std::array<unsigned long long,7> v3_half_reason_{},v3_full_reason_{};
    unsigned long long v3_half_second_job_=0,v3_half_no_job_=0;
    std::array<unsigned long long,3> branch_actions_{},branch_land_gain_{};
    std::array<int,3> last_branch_land_{{0,0,0}};
    unsigned long long cycle2_rejected_=0,cycle3_rejected_=0,cycle4_rejected_=0,cycle5to10_penalized_=0,cycle_break_alternatives_=0;
    std::vector<int> v3_packet_path_;int v3_objective_=-1;std::string v3_action_label_="NONE";
    struct V3Snapshot {int turn,land,army,opp_land,opp_army,castles,c1army,c2army;std::array<int,3> branch_land;};
    std::vector<V3Snapshot> v3_snapshots_;
    int pending_v3_reason_=-1,pending_v3_branch_=-1,pending_v3_source_=-1,pending_v3_dest_=-1;double pending_v3_secondary_value_=0;
    bool hunter_suspicion_active_=false;int hunter_suspicion_turn_=-1,hunter_suspicion_clear_=0;
    struct HunterEntry {int turn,phase,land,opp_land,army,opp_army,garrison,own_stack,own_dist,enemy_stack,enemy_dist,packets,c1army;};
    std::vector<HunterEntry> hunter_entry_;
    struct CastleFunding {int live_cost=0,army=0,required=0,turns=0,closest=INF,max_army=0,min_required=INF,feeds=0;double urgency=0;std::array<int,6> skipped{};};
    std::array<CastleFunding,2> funding_;
    struct CastleCheckpoint {int turn,index,cost,army,required,closest;double urgency;};std::vector<CastleCheckpoint> castle_checkpoints_;
    long long v3_half_source_sum_=0,v3_half_secondary_sum_=0;int v3_half_source_min_=INF;
    bool hunter_warning_active_=false;double hunter_warning_score_=0;int hunter_warning_turn_=-1,hunter_warning_first_evidence_=-1,hunter_warning_clear_=0,hunter_warning_closing_streak_=0,hunter_warning_active_turns_=0,hunter_warning_activations_=0;
    struct WarningEntry {int turn,phase,land,opp_land,army,opp_army,garrison,own_stack,own_dist,enemy_stack,enemy_dist,packets,c1army,c1required;double warning,signature;};std::vector<WarningEntry> warning_entry_;
    int c1_first_funded_turn_=-1,c1_first_buildable_turn_=-1,c1_first_buildable_army_=0,c1_delay_reason_=0;bool c1_funded_used_tactically_=false;
    // V3.3 opponent-agnostic concentrated-force approach tracking.  This is
    // deliberately independent of every Hunter classifier/state.
    struct ThreatObservation {int turn,cell,army,dist;};std::vector<ThreatObservation> approach_history_;
    struct ThreatActivation {int turn,enemy_cell,enemy_army,enemy_total,enemy_dist,persistence,reaction_cell,reaction_army,reaction_dist,c1army;double concentration,closing,score;bool c1funded,c1built,distance_decreased,substantial,concentrated;};
    std::vector<ThreatActivation> approach_activations_log_;
    bool approach_threat_active_=false;double approach_threat_score_=0,approach_closing_rate_=0,approach_threat_max_score_=0;int approach_threat_first_turn_=-1,approach_threat_clear_=0,approach_persistence_=0,approach_enemy_cell_=-1,approach_enemy_army_=0,approach_enemy_dist_=INF,reaction_cell_=-1,reaction_army_=0,reaction_dist_=INF;
    long long approach_threat_activations_=0,approach_threat_turns_=0,approach_land_gain_=0,approach_suppressed_expansion_=0,approach_candidate_rejections_=0,approach_selected_action_changes_=0,approach_consolidations_=0,approach_castle_delays_=0,approach_c1_delay_turns_=0,approach_c1_feed_suppressions_=0;int approach_last_land_=0;bool approach_changed_this_turn_=false,approach_block_castle_feed_=false;

    bool flip10() { return unit_(rng_) < 0.10; }

    bool inside(int r, int c) const { return r >= 0 && r < h_ && c >= 0 && c < w_; }
    int cell(int r, int c) const { return r * w_ + c; }
    int row(int x) const { return x / w_; }
    int col(int x) const { return x % w_; }
    int neighbor(int x, int d) const {
        int r = row(x) + DR[d], c = col(x) + DC[d];
        return inside(r, c) ? cell(r, c) : -1;
    }
    int direction(int a, int b) const {
        for (int d = 0; d < 4; ++d) if (neighbor(a, d) == b) return d;
        return 0;
    }

    void initialise(const Observation& o) {
        passable_.assign(n_, false);
        cell_id_.assign(n_, -1);
        degree_.assign(n_, 0); component_.assign(n_, -1); room_.assign(n_, 0);
        articulation_.assign(n_, false); known_castle_.assign(n_, false);
        possible_enemy_castle_.assign(n_, false); castle_first_.assign(n_, -1);
        castle_owner_.assign(n_, 0); last_owner_.assign(n_, 0); last_army_.assign(n_, 0);
        last_seen_.assign(n_, -1); enemy_score_.assign(n_, 0);
