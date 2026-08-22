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
    std::array<int,3> planned_castle_{{-1,-1,-1}},planned_castle_cost_{{0,0,0}},planned_castle_built_turn_{{-1,-1,-1}};
    int v3_split_policy_=2,v3_castle_count_=3;
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
    std::array<CastleFunding,3> funding_;
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
        for(int end:id_cell_)if(degree_[end]==1){int prev=-1,x=end,depth=4;while(x>=0&&degree_[x]<=2&&depth>0){terminal_depth_[x]=std::max(terminal_depth_[x],depth--);int nx=-1;for(int d=0;d<4;++d){int y=neighbor(x,d);if(y>=0&&passable_[y]&&y!=prev){nx=y;break;}}prev=x;x=nx;}}
        for(int x:id_cell_){int ed=std::min({row(x),h_-1-row(x),col(x),w_-1-col(x)}),corner=std::min({row(x)+col(x),row(x)+w_-1-col(x),h_-1-row(x)+col(x),h_-1-row(x)+w_-1-col(x)});
            double a=degree_[x]*13+room_[x]*.45+(articulation_[x]?18:0)-std::max(0,4-ed)*13-std::max(0,3-corner)*18-terminal_depth_[x]*22;
            if(general_>=0){double dx=(col(x)-col(general_))*(col(general_)<w_/2?1:-1),dy=(row(x)-row(general_))*(row(general_)<h_/2?1:-1);a+=.35*(dx+dy);}
            static_affinity_[x]=a;}

        // Official placement: walking distance >=17 and radius-seven room gap
        // <=5. Uniform sampling inside that fair set means no sharper claim is valid.
        if (general_ >= 0) {
            for (int x : id_cell_) {
                int d = dist_[cell_id_[general_]][cell_id_[x]];
                if (d >= 17 && std::abs(room_[x] - room_[general_]) <= 5)
                    enemy_score_[x] = 1000 + 10*d + room_[x];
            }
            if (*std::max_element(enemy_score_.begin(), enemy_score_.end()) == 0)
                for (int x:id_cell_) if(dist_[cell_id_[general_]][cell_id_[x]]>=17) enemy_score_[x]=500;
        }
        initialise_v3_routes();
    }

    int initial_castle_cost(int x,const std::vector<int>&prior={})const {int c=35+std::max(0,14-2*(std::abs(row(x)-row(general_))+std::abs(col(x)-col(general_))));for(int s:prior)c+=std::max(0,14-2*(std::abs(row(x)-row(s))+std::abs(col(x)-col(s))));return c;}
    void initialise_v3_routes(){
        nav_.assign(n_,{});edge_route_flow_.assign(n_,{});int p=id_cell_.size(),gid=cell_id_[general_];
        for(int x:id_cell_){auto&v=nav_[x];v.passable=true;v.sector=std::min(2,3*row(x)/std::max(1,h_))*3+std::min(2,3*col(x)/std::max(1,w_));v.dist_from_general=std::min(INF,dist_[gid][cell_id_[x]]);v.degree=degree_[x];v.articulation=articulation_[x];for(int d=0;d<4;++d){int y=neighbor(general_,d);if(y>=0&&passable_[y]&&dist_[cell_id_[y]][cell_id_[x]]+1==dist_[gid][cell_id_[x]])v.first_hop_mask|=1u<<d;}}
        // Nine immutable multi-source sector fields.
        for(int s=0;s<9;++s){sector_dist_[s].assign(n_,INF);sector_next_dir_[s].assign(n_,-1);std::queue<int>q;for(int x:id_cell_)if(nav_[x].sector==s){sector_dist_[s][x]=0;q.push(x);}while(!q.empty()){int x=q.front();q.pop();for(int d=0;d<4;++d){int y=neighbor(x,d);if(y>=0&&passable_[y]&&sector_dist_[s][y]>sector_dist_[s][x]+1){sector_dist_[s][y]=sector_dist_[s][x]+1;q.push(y);}}}for(int x:id_cell_)if(sector_dist_[s][x]>0&&sector_dist_[s][x]<INF)for(int d=0;d<4;++d){int y=neighbor(x,d);if(y>=0&&passable_[y]&&sector_dist_[s][y]+1==sector_dist_[s][x]){sector_next_dir_[s][x]=d;break;}}}
        // Route load uses one representative path to each sector; route flow
