        // interprets, but never changes, the existing spawn probabilities.
        for(int s=0;s<9;++s){int target=-1,best=-1;for(int x:id_cell_)if(nav_[x].sector==s&&dist_[gid][cell_id_[x]]>best){best=dist_[gid][cell_id_[x]];target=x;}for(int x=general_;target>=0&&x!=target;){nav_[x].route_load++;nav_[x].sector_route_mask|=1u<<s;int h=next_hop_[cell_id_[x]][cell_id_[target]];if(h<0)break;x=id_cell_[h];}}
        double total=0;for(int x:id_cell_)if(enemy_score_[x]>0)total+=enemy_score_[x];for(int t:id_cell_)if(enemy_score_[t]>0){double f=enemy_score_[t]/std::max(1.0,total);int x=general_;nav_[x].route_flow+=f;while(x!=t){int h=next_hop_[cell_id_[x]][cell_id_[t]];if(h<0)break;int y=id_cell_[h],d=direction(x,y);edge_route_flow_[x][d]+=f;nav_[y].route_flow+=f;x=y;}}
        // Removing an articulation and counting cells disconnected from the
        // general approximates the production space unlocked beyond it.
        for(int cut:id_cell_)if(articulation_[cut]&&cut!=general_){std::vector<char>seen(n_);std::queue<int>q;q.push(general_);seen[general_]=1;int count=0;while(!q.empty()){int x=q.front();q.pop();++count;for(int d=0;d<4;++d){int y=neighbor(x,d);if(y>=0&&passable_[y]&&y!=cut&&!seen[y])seen[y]=1,q.push(y);}}nav_[cut].breakthrough_gain=std::min(65535,p-count-1);}
        for(int x:id_cell_)nav_[x].static_route_value=nav_[x].route_flow*500+nav_[x].route_load*22+nav_[x].breakthrough_gain*2+degree_[x]*12+room_[x]*.3;
        std::array<std::pair<double,int>,4> branches{};for(int d=0;d<4;++d){int y=neighbor(general_,d);double value=-1;if(y>=0&&passable_[y]){value=0;for(int x:id_cell_)if(nav_[x].first_hop_mask&(1u<<d))value+=1+nav_[x].static_route_value*.01;}branches[d]={value,d};}std::sort(branches.begin(),branches.end(),std::greater<>());for(auto b:branches)if(b.first>=0&&primary_branch_count_<3)primary_branch_dir_[primary_branch_count_++]=b.second;
        auto pick=[&](const std::vector<int>&prior){int minc=INF;for(int x:id_cell_)if(x!=general_&&dist_[gid][cell_id_[x]]>=5&&dist_[gid][cell_id_[x]]<INF&&std::find(prior.begin(),prior.end(),x)==prior.end())minc=std::min(minc,initial_castle_cost(x,prior));int bx=-1;double bs=-1e100;for(int x:id_cell_){if(x==general_||dist_[gid][cell_id_[x]]<5||dist_[gid][cell_id_[x]]>=INF||std::find(prior.begin(),prior.end(),x)!=prior.end())continue;int c=initial_castle_cost(x,prior);if(c>minc+2)continue;int distinct=0;bool new_sector=true;for(int q:prior){if((nav_[x].first_hop_mask&nav_[q].first_hop_mask)==0)++distinct;if(nav_[x].sector==nav_[q].sector)new_sector=false;}double s=nav_[x].static_route_value-dist_[gid][cell_id_[x]]*6+distinct*120+(new_sector?80:0);if(s>bs)bs=s,bx=x;}return std::pair<int,int>{bx,bx<0?0:initial_castle_cost(bx,prior)};};
        std::vector<int> selected;for(int i=0;i<3;++i){auto c=pick(selected);planned_castle_[i]=c.first;planned_castle_cost_[i]=c.second;if(c.first>=0)selected.push_back(c.first);}
        if(const char*s=std::getenv("JURAJ_V3_SPLIT")){std::string v=s;v3_split_policy_=v=="full"?0:(v=="naive"?1:2);}if(const char*s=std::getenv("JURAJ_V3_CASTLES"))v3_castle_count_=std::clamp(std::atoi(s),0,3);
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
                if (!known_castle_[x]) { known_castle_[x]=true; castle_first_[x]=o.turn; }
                possible_enemy_castle_[x] = last_owner_[x] != 1; castle_owner_[x] = possible_enemy_castle_[x] ? 2 : 1;
            }
            if (o.type[x] == 3) {
                if (!known_castle_[x]) { known_castle_[x]=true; castle_first_[x]=o.turn; if(o.owner[x]==2){++enemy_castle_events_;enemy_castle_response_pending_=true;++enemy_castle_response_triggers_;} }
                castle_owner_[x] = o.owner[x]; possible_enemy_castle_[x] = o.owner[x] == 2;
            }
            if (visible) {
                last_owner_[x]=o.owner[x]; last_army_[x]=o.army[x]; last_seen_[x]=o.turn;
                if (o.type[x] == 4 && o.owner[x] == 1) general_=x;
                if (o.type[x] == 4 && o.owner[x] == 2) { enemy_general_=x; if(found_enemy_turn_<0)found_enemy_turn_=o.turn; }
                if (o.owner[x] != 2 || o.type[x] != 4) enemy_score_[x]=0;
                if (o.owner[x]==2) visible_enemy_stacks_.push_back({x,o.army[x]});
            }
        }
        std::sort(visible_enemy_stacks_.begin(), visible_enemy_stacks_.end(), [](auto a,auto b){return a.second>b.second;});
        for (auto s:visible_enemy_stacks_) if(s.second>=4) {
            auto it=std::find_if(important_enemy_stacks_.begin(),important_enemy_stacks_.end(),[&](auto z){return z.first==s.first;});
            if(it==important_enemy_stacks_.end())important_enemy_stacks_.push_back(s);else it->second=s.second;
        }
        land_behind_=o.my_land<o.opp_land;
        land_deficit_=o.my_land*10<o.opp_land*8;
        severe_land_deficit_=o.my_land*2<o.opp_land;
        int my_gain=my_land_hist_.size()>20?o.my_land-my_land_hist_[my_land_hist_.size()-21]:0;
        int opp_gain=opp_land_hist_.size()>20?o.opp_land-opp_land_hist_[opp_land_hist_.size()-21]:0;
        bool trigger=o.my_land*100<o.opp_land*65||(o.my_land*100<o.opp_land*75&&opp_gain>=my_gain+3);
        if(production_emergency_){if(o.my_land*100>=o.opp_land*85)production_emergency_=false;}else if(trigger)production_emergency_=true;
        if(production_emergency_)++production_emergency_turns_;
        if(land_deficit_)++land_deficit_turns_;
        if(severe_land_deficit_)++severe_land_deficit_turns_;
        if(o.turn==50||o.turn==100||o.turn==150||o.turn==200||o.turn==250||o.turn==300||o.turn==400)
            production_snapshots_.push_back({o.turn,o.my_land,o.opp_land,o.my_army,o.opp_army});
        update_enemy_scores(o);update_modes(o);update_qualifier_model(o);update_hunter_model(o);update_approach_threat(o);update_contact_model(o);
        update_strategy(o);
    }

    void update_contact_model(const Observation&o){
        int anchor=-1,best_army=-1;for(int x:id_cell_)if(o.owner[x]==2&&o.army[x]>=best_army){best_army=o.army[x];anchor=x;}
        if(anchor>=0){if(!contact_established_){contact_established_=true;first_contact_turn_=o.turn;}contact_anchor_=anchor;if(contact_anchor_history_.empty()||contact_anchor_history_.back()!=anchor)contact_anchor_history_.push_back(anchor);}
        if(!contact_established_||contact_anchor_<0)return;
        dominance_=o.my_army*10>=o.opp_army*18&&o.my_land*10>=o.opp_land*15;
        strong_dominance_=o.my_army*10>=o.opp_army*25&&o.my_land>=2*o.opp_land;
        if(dominance_)++dominance_mode_turns_;
        if(strong_dominance_)++strong_dominance_turns_;
        double stage_best=-1e100;int stage=-1;
        for(int x:id_cell_)if(o.owner[x]==1){int d=dist_[cell_id_[x]][cell_id_[contact_anchor_]];if(d<2||d>4)continue;double s=degree_[x]*18+room_[x]-(articulation_[x]?0:-8)+(known_castle_[x]?200:0);if(s>stage_best){stage_best=s;stage=x;}}
        if(stage>=0&&stage!=contact_staging_cell_){old_staging_cell_=contact_staging_cell_;contact_staging_cell_=stage;}
        front_stack_=-1;double fb=-1e100;for(int x:id_cell_)if(legal_source(o,x)){int d=dist_[cell_id_[x]][cell_id_[contact_anchor_]];double s=o.army[x]*4.0-d*28+degree_[x]*10+(x==contact_staging_cell_?80:0);if(s>fb){fb=s;front_stack_=x;}}
        if(front_stack_>=0){front_stack_path_.push_back(front_stack_);if(front_stack_path_.size()>40)front_stack_path_.erase(front_stack_path_.begin());}
        if(main_stack_>=0)max_largest_contact_distance_=std::max(max_largest_contact_distance_,dist_[cell_id_[main_stack_]][cell_id_[contact_anchor_]]);
        int attack=contact_staging_cell_>=0?contact_staging_cell_:contact_anchor_,dh=next_hop_[cell_id_[general_]][cell_id_[contact_anchor_]],defense=dh>=0?id_cell_[dh]:general_;
        int rear=0,excess=0,atk=0,def=0;for(int x:id_cell_)if(o.owner[x]==1){if(is_rear_low_value(o,x)){rear+=o.army[x];excess+=std::max(0,o.army[x]-1);}else{int ed=std::min({row(x),h_-1-row(x),col(x),w_-1-col(x)});if(ed<=1&&o.army[x]>=8&&active_affinity_exception(o,x))++active_edge_exemptions_;}if(dist_[cell_id_[x]][cell_id_[attack]]<=5)atk+=o.army[x];if(dist_[cell_id_[x]][cell_id_[defense]]<=3)def+=o.army[x];}
        rear_army_total_=rear;rear_excess_army_=excess;if(enemy_general_>=0&&(affinity_snapshots_.empty()||o.turn-affinity_snapshots_.back().turn>=50))affinity_snapshots_.push_back({o.turn,o.my_army,rear,atk,def});
    }

    int affinity_target()const{return enemy_general_>=0?enemy_general_:(contact_anchor_>=0?contact_anchor_:-1);}
    bool active_affinity_exception(const Observation&o,int x)const{
        int t=affinity_target();if(x==general_||x==front_stack_||x==contact_staging_cell_||known_castle_[x]||articulation_[x])return true;
        if(t>=0&&dist_[cell_id_[x]][cell_id_[t]]<=6)return true;
        for(auto e:visible_enemy_stacks_)if(dist_[cell_id_[x]][cell_id_[e.first]]<=4)return true;
        if(enemy_general_<0&&(strategy_==SEARCH_GENERAL||strategy_==QUALIFIER_PROBE)){int best=static_cast<int>(std::max_element(enemy_score_.begin(),enemy_score_.end())-enemy_score_.begin());if(enemy_score_[best]>0&&dist_[cell_id_[x]][cell_id_[best]]<=5)return true;int unseen=0;for(int d=0;d<4;++d){int y=neighbor(x,d);if(y>=0&&last_seen_[y]<0)++unseen;}if(unseen>=2&&o.owner[x]==1)return true;}
        return general_>=0&&dist_[cell_id_[x]][cell_id_[general_]]<=2;
    }
    double compute_dynamic_affinity(const Observation&o,int x)const{
        double a=static_affinity_[x];int t=affinity_target();
        if(t>=0){int dt=dist_[cell_id_[x]][cell_id_[t]],base=dist_[cell_id_[general_]][cell_id_[t]];double force=enemy_general_>=0?7.0:3.5;a-=dt*force;if(dist_[cell_id_[general_]][cell_id_[x]]+dt<=base+2)a+=enemy_general_>=0?90:42;if(dt<=6)a+=enemy_general_>=0?115:55;if(dt>base+2)a-=enemy_general_>=0?58:32;}
        int enemy_distance=INF;for(int z:id_cell_)if(o.owner[z]==2)enemy_distance=std::min(enemy_distance,dist_[cell_id_[x]][cell_id_[z]]);if(enemy_distance<INF)a+=std::max(0,9-enemy_distance)*7;
        for(auto e:visible_enemy_stacks_){int d=dist_[cell_id_[x]][cell_id_[e.first]];a+=std::max(0,7-d)*(required_defense_>0?8:3);}
        if(x==contact_staging_cell_)a+=110;
        if(x==front_stack_)a+=75;
        if(enemy_general_>=0&&x==enemy_general_)a+=240;
        int ds=t>=0?next_hop_[cell_id_[general_]][cell_id_[t]]:-1;if(ds>=0)a-=dist_[cell_id_[x]][ds]*(required_defense_>0?4.5:1.8);
        if(enemy_general_<0){int best=static_cast<int>(std::max_element(enemy_score_.begin(),enemy_score_.end())-enemy_score_.begin());if(enemy_score_[best]>0)a-=dist_[cell_id_[x]][cell_id_[best]]*(strategy_==SEARCH_GENERAL?4.5:1.5);}
        if(old_staging_cell_>=0&&x==old_staging_cell_&&x!=contact_staging_cell_)a-=25;
        if(dominance_)a+=t>=0?std::max(0,10-dist_[cell_id_[x]][cell_id_[t]])*3:0;
        if(active_affinity_exception(o,x))a+=45;
        return a;
    }
    void rebuild_dynamic_affinity(const Observation&o){
        for(int x:id_cell_)dynamic_affinity_[x]=compute_dynamic_affinity(o,x);
        int rear=*std::min_element(id_cell_.begin(),id_cell_.end(),[&](int a,int b){return static_affinity_[a]<static_affinity_[b];}),enemy=enemy_general_;
        bool event=o.turn%100==0||contact_staging_cell_!=last_field_stage_||enemy!=last_field_enemy_;if(event&&field_traces_.size()<20){field_traces_.push_back({o.turn,rear,old_staging_cell_,contact_staging_cell_,front_stack_,enemy,dynamic_affinity_[rear],old_staging_cell_>=0?dynamic_affinity_[old_staging_cell_]:0,contact_staging_cell_>=0?dynamic_affinity_[contact_staging_cell_]:0,front_stack_>=0?dynamic_affinity_[front_stack_]:0,enemy>=0?dynamic_affinity_[enemy]:0});last_field_stage_=contact_staging_cell_;last_field_enemy_=enemy;}
    }
    double dynamic_affinity(const Observation&,int x)const{return dynamic_affinity_[x];}
    bool is_rear_low_value(const Observation&o,int x)const{
        if(o.owner[x]!=1||o.army[x]<=1||x==general_||known_castle_[x]||articulation_[x]||active_affinity_exception(o,x))return false;
        for(auto e:visible_enemy_stacks_)if(dist_[cell_id_[x]][cell_id_[e.first]]<=5)return false;
        int t=affinity_target();if(t<0)return false;
        int base=dist_[cell_id_[general_]][cell_id_[t]],dt=dist_[cell_id_[x]][cell_id_[t]];
        int ed=std::min({row(x),h_-1-row(x),col(x),w_-1-col(x)}),corner=std::min({row(x)+col(x),row(x)+w_-1-col(x),h_-1-row(x)+col(x),h_-1-row(x)+w_-1-col(x)});
        return dt>base+2&&(ed<=1||corner<=2||degree_[x]==1||terminal_depth_[x]>0);
    }

    void update_hunter_model(const Observation&o){
        double evidence=0;
        if(!visible_enemy_stacks_.empty()){
            auto s=visible_enemy_stacks_.front();int dg=dist_[cell_id_[s.first]][cell_id_[general_]];
            if(hunter_first_stack_cell_<0){hunter_first_stack_cell_=s.first;hunter_first_stack_army_=s.second;hunter_first_stack_distance_=dg;}
            bool dominant=visible_enemy_stacks_.size()==1||s.second>=2*std::max(1,visible_enemy_stacks_[1].second);
            bool adjacent=false,crumb=false,closer=false;
            if(!hunter_stack_history_.empty()){
                auto p=hunter_stack_history_.back();adjacent=dist_[cell_id_[p.cell]][cell_id_[s.first]]==1;closer=dg<p.distance_to_general;
                if(adjacent&&o.owner[p.cell]==2&&o.army[p.cell]<=2){crumb=true;if(std::find(hunter_breadcrumbs_.begin(),hunter_breadcrumbs_.end(),p.cell)==hunter_breadcrumbs_.end())hunter_breadcrumbs_.push_back(p.cell);}
