
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

    int initial_castle_cost(int x,int prior=-1)const {int c=35+std::max(0,14-2*(std::abs(row(x)-row(general_))+std::abs(col(x)-col(general_))));if(prior>=0)c+=std::max(0,14-2*(std::abs(row(x)-row(prior))+std::abs(col(x)-col(prior))));return c;}
    void initialise_v3_routes(){
        nav_.assign(n_,{});edge_route_flow_.assign(n_,{});int p=id_cell_.size(),gid=cell_id_[general_];
        for(int x:id_cell_){auto&v=nav_[x];v.passable=true;v.sector=std::min(2,3*row(x)/std::max(1,h_))*3+std::min(2,3*col(x)/std::max(1,w_));v.dist_from_general=std::min(INF,dist_[gid][cell_id_[x]]);v.degree=degree_[x];v.articulation=articulation_[x];for(int d=0;d<4;++d){int y=neighbor(general_,d);if(y>=0&&passable_[y]&&dist_[cell_id_[y]][cell_id_[x]]+1==dist_[gid][cell_id_[x]])v.first_hop_mask|=1u<<d;}}
        // Nine immutable multi-source sector fields.
        for(int s=0;s<9;++s){sector_dist_[s].assign(n_,INF);sector_next_dir_[s].assign(n_,-1);std::queue<int>q;for(int x:id_cell_)if(nav_[x].sector==s){sector_dist_[s][x]=0;q.push(x);}while(!q.empty()){int x=q.front();q.pop();for(int d=0;d<4;++d){int y=neighbor(x,d);if(y>=0&&passable_[y]&&sector_dist_[s][y]>sector_dist_[s][x]+1){sector_dist_[s][y]=sector_dist_[s][x]+1;q.push(y);}}}for(int x:id_cell_)if(sector_dist_[s][x]>0&&sector_dist_[s][x]<INF)for(int d=0;d<4;++d){int y=neighbor(x,d);if(y>=0&&passable_[y]&&sector_dist_[s][y]+1==sector_dist_[s][x]){sector_next_dir_[s][x]=d;break;}}}
        // Route load uses one representative path to each sector; route flow
        // interprets, but never changes, the existing spawn probabilities.
        for(int s=0;s<9;++s){int target=-1,best=-1;for(int x:id_cell_)if(nav_[x].sector==s&&dist_[gid][cell_id_[x]]>best){best=dist_[gid][cell_id_[x]];target=x;}for(int x=general_;target>=0&&x!=target;){nav_[x].route_load++;nav_[x].sector_route_mask|=1u<<s;int h=next_hop_[cell_id_[x]][cell_id_[target]];if(h<0)break;x=id_cell_[h];}}
        double total=0;for(int x:id_cell_)if(enemy_score_[x]>0)total+=enemy_score_[x];for(int t:id_cell_)if(enemy_score_[t]>0){double f=enemy_score_[t]/std::max(1.0,total);int x=general_;nav_[x].route_flow+=f;while(x!=t){int h=next_hop_[cell_id_[x]][cell_id_[t]];if(h<0)break;int y=id_cell_[h],d=direction(x,y);edge_route_flow_[x][d]+=f;nav_[y].route_flow+=f;x=y;}}
        // Removing an articulation and counting cells disconnected from the
        // general approximates the production space unlocked beyond it.
        for(int cut:id_cell_)if(articulation_[cut]&&cut!=general_){std::vector<char>seen(n_);std::queue<int>q;q.push(general_);seen[general_]=1;int count=0;while(!q.empty()){int x=q.front();q.pop();++count;for(int d=0;d<4;++d){int y=neighbor(x,d);if(y>=0&&passable_[y]&&y!=cut&&!seen[y])seen[y]=1,q.push(y);}}nav_[cut].breakthrough_gain=std::min(65535,p-count-1);}
        for(int x:id_cell_)nav_[x].static_route_value=nav_[x].route_flow*500+nav_[x].route_load*22+nav_[x].breakthrough_gain*2+degree_[x]*12+room_[x]*.3;
        std::array<std::pair<double,int>,4> branches{};for(int d=0;d<4;++d){int y=neighbor(general_,d);double value=-1;if(y>=0&&passable_[y]){value=0;for(int x:id_cell_)if(nav_[x].first_hop_mask&(1u<<d))value+=1+nav_[x].static_route_value*.01;}branches[d]={value,d};}std::sort(branches.begin(),branches.end(),std::greater<>());for(auto b:branches)if(b.first>=0&&primary_branch_count_<3)primary_branch_dir_[primary_branch_count_++]=b.second;
        auto pick=[&](int prior){int minc=INF;for(int x:id_cell_)if(x!=general_&&dist_[gid][cell_id_[x]]>=5&&dist_[gid][cell_id_[x]]<INF&&(prior<0||x!=prior))minc=std::min(minc,initial_castle_cost(x,prior));int bx=-1;double bs=-1e100;for(int x:id_cell_){if(x==general_||dist_[gid][cell_id_[x]]<5||dist_[gid][cell_id_[x]]>=INF||(prior>=0&&x==prior))continue;int c=initial_castle_cost(x,prior);if(c>minc+2)continue;bool different=prior<0||(nav_[x].first_hop_mask&nav_[prior].first_hop_mask)==0;double s=nav_[x].static_route_value+dist_[gid][cell_id_[x]]*2+(different?160:0);if(s>bs)bs=s,bx=x;}return std::pair<int,int>{bx,bx<0?0:initial_castle_cost(bx,prior)};};
        auto c1=pick(-1);planned_castle_[0]=c1.first;planned_castle_cost_[0]=c1.second;auto c2=pick(c1.first);planned_castle_[1]=c2.first;planned_castle_cost_[1]=c2.second;
        if(const char*s=std::getenv("JURAJ_V3_SPLIT")){std::string v=s;v3_split_policy_=v=="full"?0:(v=="naive"?1:2);}if(const char*s=std::getenv("JURAJ_V3_CASTLES"))v3_castle_count_=std::clamp(std::atoi(s),0,2);
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
