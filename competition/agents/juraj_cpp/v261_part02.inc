    unsigned long long repeated_cell_penalties_ = 0;
    int max_main_stack_recent_revisits_ = 0;
    std::vector<std::pair<int,int>> recent_significant_edges_;
    std::vector<int> recent_main_stack_positions_;
    int trace_discovery_turn_ = -1, trace_main_army_ = 0, trace_main_distance_ = -1;
    std::vector<int> discovery_main_path_;
    struct HunterSighting { int turn, cell, army, distance_to_general; };
    std::vector<HunterSighting> hunter_stack_history_;
    std::vector<int> hunter_breadcrumbs_, hunter_raider_path_;
    double hunter_signature_score_ = 0, hunter_signature_max_ = 0;
    int hunter_trigger_turn_ = -1, hunter_mode_turns_ = 0, hunter_raider_ = -1;
    int hunter_raider_selected_turn_ = -1, hunter_raider_selected_army_ = 0;
    int hunter_raider_progress_moves_ = 0, hunter_breadcrumb_moves_ = 0;
    int hunter_kill_zone_holds_ = 0, hunter_convoy_kills_ = 0;
    int hunter_gate_castles_ = 0, hunter_gate_disconnects_ = 0;
    int hunter_general_found_turn_ = -1, hunter_general_kill_attempts_ = 0;
    int hunter_first_stack_cell_ = -1, hunter_first_stack_army_ = 0, hunter_first_stack_distance_ = -1;
    bool contact_established_ = false, contact_castle_built_ = false;
    int first_contact_turn_ = -1, contact_anchor_ = -1, contact_staging_cell_ = -1, front_stack_ = -1;
    int contact_pressure_turns_ = 0, contact_idle_turns_ = 0, contact_idle_max_ = 0;
    int front_stack_moves_ = 0, remote_relocation_moves_ = 0, contact_castle_turn_ = -1;
    int contact_castles_built_ = 0, front_feeder_moves_ = 0, enemy_frontier_captures_ = 0;
    int dominance_mode_turns_ = 0, strong_dominance_turns_ = 0, max_largest_contact_distance_ = 0;
    bool dominance_ = false, strong_dominance_ = false;
    std::vector<int> front_stack_path_, contact_anchor_history_;
    std::vector<std::string> contact_action_trace_;
    std::vector<double> static_affinity_, dynamic_affinity_;
    std::vector<int> terminal_depth_;
    bool enemy_castle_response_pending_ = false;
    int enemy_castle_response_triggers_ = 0, second_castle_turn_ = -1, second_castle_cost_ = 0;
    double second_castle_attack_utility_ = 0, second_castle_defense_utility_ = 0;
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

        // At turn zero competition mode has no castles.  Both visible mountains
        // (2) and structures in fog (5) are therefore original mountains.
        for (int x = 0; x < n_; ++x) {
            passable_[x] = o.type[x] != 2 && o.type[x] != 5;
            if (passable_[x]) { cell_id_[x] = static_cast<int>(id_cell_.size()); id_cell_.push_back(x); }
            if (o.type[x] == 4 && o.owner[x] == 1) general_ = x;
        }
        const int p = static_cast<int>(id_cell_.size());
        std::vector<std::vector<int>> adj(p);
        for (int x : id_cell_) for (int d = 0; d < 4; ++d) {
            int y = neighbor(x, d); if (y >= 0 && passable_[y]) adj[cell_id_[x]].push_back(cell_id_[y]);
        }
        for (int x : id_cell_) degree_[x] = static_cast<int>(adj[cell_id_[x]].size());
