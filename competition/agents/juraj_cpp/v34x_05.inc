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
