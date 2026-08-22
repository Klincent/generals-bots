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
    }

    bool visible_type(int t) const { return t == 1 || t == 2 || t == 3 || t == 4; }
    void update_memory(const Observation& o) {
        turn_ = o.turn; visible_enemy_stacks_.clear();
        observation_history_.push_back({o.turn,o.my_land,o.my_army,o.opp_land,o.opp_army});
        full_observation_history_.push_back(o);
        if (!opp_army_hist_.empty()) {
            int expected = 0;
            if (o.turn % 50 == 0) expected += opp_land_hist_.back();
            if (o.turn % 2 == 0) {
                expected += 1;  // the enemy general
                expected += static_cast<int>(std::count(castle_owner_.begin(), castle_owner_.end(), 2));
            }
            expected_opp_production_ += expected;
            int known_loss = 0;
            for (int x : id_cell_) {
                if (last_seen_[x] == o.turn - 1 && last_owner_[x] == 2 &&
                    visible_type(o.type[x]) && o.owner[x] == 2 && o.army[x] < last_army_[x])
                    known_loss += last_army_[x] - o.army[x];
            }
            known_opp_combat_losses_ += known_loss;
            opponent_unexplained_delta_ = o.opp_army - opp_army_hist_.back() - expected + known_loss;
            // A build costs at least 35.  Treat a matching unexplained drop as
            // evidence, not certainty: fogged combat or movement can confound it.
            if (opponent_unexplained_delta_ <= -35) ++suspected_enemy_builds_;
        }
        my_land_hist_.push_back(o.my_land); my_army_hist_.push_back(o.my_army);
        opp_land_hist_.push_back(o.opp_land); opp_army_hist_.push_back(o.opp_army);
        if (o.turn == 50) { land50_ = o.my_land; opp_land50_=o.opp_land; my_army50_=o.my_army; opp_army50_=o.opp_army; }
        for (int x=0;x<n_;++x) {
            bool visible = visible_type(o.type[x]);
            // A structure-in-fog on initially passable ground can only be a built castle.
            if (o.type[x] == 5 && passable_[x]) {
