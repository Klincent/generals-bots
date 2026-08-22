    bool approach_threat_active_=false;double approach_threat_score_=0,approach_closing_rate_=0,approach_threat_max_score_=0;int approach_threat_first_turn_=-1,approach_threat_clear_=0,approach_persistence_=0,approach_enemy_cell_=-1,approach_enemy_army_=0,approach_enemy_dist_=INF,reaction_cell_=-1,reaction_army_=0,reaction_dist_=INF;
    long long approach_threat_activations_=0,approach_threat_turns_=0,approach_land_gain_=0,approach_suppressed_expansion_=0,approach_candidate_rejections_=0,approach_selected_action_changes_=0,approach_consolidations_=0,approach_castle_delays_=0,approach_c1_delay_turns_=0,approach_c1_feed_suppressions_=0;int approach_last_land_=0,approach_delayed_castle_index_=-1;bool approach_changed_this_turn_=false,approach_block_castle_feed_=false;
    std::array<int,3> planned_first_funded_{{-1,-1,-1}},planned_actual_cost_{{0,0,0}},planned_delay_turns_{{0,0,0}},planned_tactical_use_{{0,0,0}};
    struct StrandedSnapshot {int turn,total,edge,terminal,remote;std::array<int,3> branch;};std::vector<StrandedSnapshot> stranded_snapshots_;
    long long rear_drain_candidates_=0,rear_drain_actions_=0,rear_drain_army_=0,rear_drain_attack_=0,rear_drain_defense_=0,rear_drain_edge_=0,rear_drain_terminal_=0,rear_source_sum_=0,rear_moved_sum_=0,rear_progress_sum_=0;std::array<long long,4> rear_source_bins_{};int max_stranded_surplus_=0,last_rear_drain_turn_=-100,pending_rear_drain_source_=-1,pending_rear_drain_dest_=-1,pending_rear_drain_sink_=-1,pending_rear_drain_kind_=0;
    struct MobilizationSnapshot {int turn,eligible,still,moved,network,largest,second;double ratio;};std::vector<MobilizationSnapshot> mobilization_snapshots_;
    std::vector<int> mobilized_credit_,large_rear_since_,evacuation_target_;long long mobilized_to_attack_=0,mobilized_to_defense_=0;int mobilization_initial_eligible_=0,mobilization_discovery_turn_=-1,mobilization_idle10_=0,mobilization_idle25_=0,mobilization_idle50_=0;
    struct RearHemisphereSnapshot {int turn,cells,army,remaining,belt,belt1,belt2,reserve,surplus,released;};std::vector<RearHemisphereSnapshot> rear_hemisphere_snapshots_;
    long long mandatory_rear_actions_=0,mandatory_rear_army_=0,mandatory_rear_source_sum_=0,belt_attack_actions_=0,belt_attack_army_=0,threat_clear_release_actions_=0,counterattack_release_actions_=0;int attack_direction_turn_=-1,attack_direction_cell_=-1,largest_rear_source_=0,pending_belt_layer_=0;bool pending_belt_release_=false,previous_direction_threat_=false;
    std::array<int,3> castle_funding_start_{{-1,-1,-1}},castle_first_safe_{{-1,-1,-1}};

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

        // Connected components and all-pairs BFS distances/first hops.  With at
        // most 441 cells this is useful real work yet remains far below 8.5 s.
        int cc = 0;
        for (int start : id_cell_) if (component_[start] < 0) {
            std::queue<int> q; q.push(start); component_[start] = cc;
            while (!q.empty()) { int x=q.front(); q.pop(); for(int d=0;d<4;++d){int y=neighbor(x,d);if(y>=0&&passable_[y]&&component_[y]<0){component_[y]=cc;q.push(y);}} }
            ++cc;
        }
        dist_.assign(p, std::vector<int>(p, INF)); next_hop_.assign(p, std::vector<int>(p, -1));
        for (int si = 0; si < p; ++si) {
            std::queue<int> q; q.push(si); dist_[si][si] = 0;
            while (!q.empty()) {
                int u=q.front(); q.pop();
                for (int v : adj[u]) if (dist_[si][v] == INF) {
                    dist_[si][v] = dist_[si][u] + 1;
                    next_hop_[si][v] = (u == si ? v : next_hop_[si][u]); q.push(v);
                }
            }
        }
        // Radius-seven local room scores, matching the spawn generator metric.
        for (int x : id_cell_) for (int y : id_cell_)
            if (dist_[cell_id_[x]][cell_id_[y]] <= 7 && x != y) ++room_[x];

        // Tarjan articulation points identify genuine graph chokepoints.
        std::vector<int> disc(p, -1), low(p), parent(p, -1); int timer = 0;
        std::function<void(int)> dfs = [&](int u) {
            disc[u]=low[u]=timer++; int children=0;
            for(int v:adj[u]) if(disc[v]<0){parent[v]=u;++children;dfs(v);low[u]=std::min(low[u],low[v]);if(parent[u]<0&&children>1)articulation_[id_cell_[u]]=true;if(parent[u]>=0&&low[v]>=disc[u])articulation_[id_cell_[u]]=true;}else if(v!=parent[u])low[u]=std::min(low[u],disc[v]);
        };
        for (int i=0;i<p;++i) if(disc[i]<0) dfs(i);

        terminal_depth_.assign(n_,0);static_affinity_.assign(n_,-1e9);dynamic_affinity_.assign(n_,-1e9);
