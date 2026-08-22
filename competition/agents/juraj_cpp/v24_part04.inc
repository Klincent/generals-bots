        hunter_signature_max_=std::max(hunter_signature_max_,hunter_signature_score_);
        if(hunter_signature_score_>=.55&&hunter_trigger_turn_<0)hunter_trigger_turn_=o.turn;
        if(hunter_trigger_turn_>=0)hunter_signature_score_=std::max(hunter_signature_score_,.58);
        if(enemy_general_>=0&&hunter_signature_score_>=.55&&hunter_general_found_turn_<0)hunter_general_found_turn_=o.turn;
    }

    void update_strategy(const Observation& o) {
        main_stack_=-1;
        double best=-1e100;
        int target=enemy_general_;
        if(target<0&&!enemy_score_.empty()) target=static_cast<int>(std::max_element(enemy_score_.begin(),enemy_score_.end())-enemy_score_.begin());
        for(int x:id_cell_) if(o.owner[x]==1&&o.army[x]>1) {
            int d=(target>=0?dist_[cell_id_[x]][cell_id_[target]]:0);
            double utility=o.army[x]*8.0-degree_[x]*.3-d*1.5+(known_castle_[x]?5:0);
            if(utility>best){best=utility;main_stack_=x;}
        }
        if(o.turn<55) strategy_=OPENING;
        else if(enemy_general_>=0) {
            int d=main_stack_>=0?dist_[cell_id_[main_stack_]][cell_id_[enemy_general_]]:INF;
            int seen=(last_seen_[enemy_general_]>=0?last_army_[enemy_general_]:1);
            int hidden=std::max(0,o.opp_army-seen);
            defense_lower_=seen; defense_expected_=seen+hidden/std::max(3,d+2); defense_upper_=seen+hidden;
            int arrival=main_stack_>=0?std::max(0,o.army[main_stack_]-1):0;
            bool confident=arrival>defense_expected_+std::max(2,d/3)||o.turn>=720;
            int adjacent=0;for(int d2=0;d2<4;++d2){int z=neighbor(enemy_general_,d2);if(z>=0&&o.owner[z]==1&&o.army[z]>1)++adjacent;}
            if(o.turn>=800&&adjacent>=2)strategy_=DEATHTOUCH_FORK;
            else if(o.turn>=800)strategy_=DEATHTOUCH_ATTACK;
            else if(!confident&&qualifier_defense_score_>.48)strategy_=GENERAL_CONTAINMENT;
            else strategy_=o.turn>=700?DEATHTOUCH_PREPARE:(confident?GENERAL_KNOWN_ATTACK:GENERAL_KNOWN_PREPARE);
            if(main_stack_>=0) for(int i=0;i<4;++i) if(approach_turn_[i]<0&&d<=std::array<int,4>{{10,5,2,1}}[i]) approach_turn_[i]=o.turn;
        } else if(!visible_enemy_stacks_.empty()) strategy_=CONTACT;
        else strategy_=o.turn<300?EXPAND:(o.turn>=700?DEATHTOUCH_PREPARE:SEARCH_GENERAL);
        if(required_defense_>0){strategy_=GENERAL_DEFENSE_ALERT;++defense_alert_turns_;return;}
        if(enemy_general_<0&&qualifier_defense_score_>.58)strategy_=QUALIFIER_EXPLOIT;
        else if(main_stack_>=0&&qualifier_defense_score_>.48&&strategy_==CONTACT)strategy_=QUALIFIER_FEINT;
        else if(main_stack_>=0&&qualifier_defense_score_>.32&&strategy_==SEARCH_GENERAL)strategy_=QUALIFIER_PROBE;
        if(strategy_>=QUALIFIER_PROBE&&strategy_<=DEATHTOUCH_FORK)++meta_turns_;
    }

    void update_qualifier_model(const Observation& o) {
        required_defense_=0; double evidence=0;
        if(!visible_enemy_stacks_.empty()){
            auto s=visible_enemy_stacks_.front();int dg=general_>=0?dist_[cell_id_[s.first]][cell_id_[general_]]:INF;
            largest_enemy_history_.push_back({o.turn,s.first,s.second,dg});
            if(largest_enemy_history_.size()>12)largest_enemy_history_.erase(largest_enemy_history_.begin());
            int local=o.army[general_];
            for(int d=0;d<4;++d){int x=neighbor(general_,d);if(x>=0&&o.owner[x]==1)local+=std::max(0,o.army[x]-1);}
            int near_power=s.second+3;
            bool closing_twice=largest_enemy_history_.size()>=3;
            if(closing_twice){auto a=largest_enemy_history_[largest_enemy_history_.size()-3];auto b=largest_enemy_history_[largest_enemy_history_.size()-2];closing_twice=a.distance_to_general>b.distance_to_general&&b.distance_to_general>dg;}
            if(dg<=5){required_defense_=s.second+std::max(3,(8-dg)/2)+4;++hard_defense_alerts_;evidence+=.28;}
            else if(dg<=8){++watch_zone_sightings_;bool dangerous=near_power>=local-2||(closing_twice&&s.second>=std::max(8,local/2));
                if(dangerous){required_defense_=s.second+std::max(3,(8-dg)/2)+4;++watch_zone_alerts_;}else ++watch_zone_ignored_;
                evidence+=dangerous?.22:.08;}
            if(largest_enemy_history_.size()>=2){auto p=largest_enemy_history_[largest_enemy_history_.size()-2];if(dg<p.distance_to_general)evidence+=.12;}
            if(main_stack_>=0&&dist_[cell_id_[s.first]][cell_id_[main_stack_]]<=4)evidence+=.35;
        }
        int k=std::min<int>(8,opp_land_hist_.size()-1);
        if(k>0){int lv=o.opp_land-opp_land_hist_[opp_land_hist_.size()-1-k];if(lv<=2&&o.opp_army>std::max(20,o.my_army/2))evidence+=.08;else if(lv>=6)evidence-=.08;}
        double observed=std::clamp(.18+evidence,0.0,1.0);
        qualifier_defense_score_=.90*qualifier_defense_score_+.10*observed;
        if((strategy_==QUALIFIER_PROBE||strategy_==QUALIFIER_FEINT)&&o.turn%10==0&&main_stack_>=0){
            int da=visible_enemy_stacks_.empty()?0:visible_enemy_stacks_.front().second;
            int dd=visible_enemy_stacks_.empty()?-1:direction(visible_enemy_stacks_.front().first,main_stack_);
            int ld=k>0?o.opp_land-opp_land_hist_[opp_land_hist_.size()-1-k]:0;
            int av=k>0?o.opp_army-opp_army_hist_[opp_army_hist_.size()-1-k]:0;
            probe_history_.push_back({o.turn,main_stack_,o.army[main_stack_],ld,av,!visible_enemy_stacks_.empty(),da,dd});
        }
    }

    void update_enemy_scores(const Observation& o) {
        if (enemy_general_ >= 0) { std::fill(enemy_score_.begin(),enemy_score_.end(),0); enemy_score_[enemy_general_]=1000000; return; }
        for(int x:id_cell_) {
            if(enemy_score_[x]<=0) continue;
            if(last_seen_[x]==o.turn) enemy_score_[x]=0;
            else {
                int activity=INF;
                for(auto s:visible_enemy_stacks_) activity=std::min(activity,dist_[cell_id_[x]][cell_id_[s.first]]);
                if(activity<INF) enemy_score_[x]+=std::max(0,18-activity)*8;
                if(possible_enemy_castle_[x]) enemy_score_[x]+=40;
            }
        }
    }

    void update_modes(const Observation& o) {
