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
            }
            if(hunter_stack_history_.empty()||hunter_stack_history_.back().cell!=s.first)hunter_stack_history_.push_back({o.turn,s.first,s.second,dg});
            evidence=(s.second>=8?.18:0)+(dominant?.18:0)+(adjacent?.20:0)+(crumb?.38:0)+(closer?.10:0);
            if(crumb&&dominant&&adjacent)hunter_signature_score_=std::max(hunter_signature_score_,.68);
        }
        double observed=std::clamp(evidence,0.0,1.0);hunter_signature_score_=.88*hunter_signature_score_+.12*observed;
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
        std::array<double,MODE_COUNT> raw{{1,1,1,1,1,1,1}};
        int k=std::min<int>(10,opp_land_hist_.size()-1);
        int land_v=k?o.opp_land-opp_land_hist_[opp_land_hist_.size()-1-k]:0;
        int army_v=k?o.opp_army-opp_army_hist_[opp_army_hist_.size()-1-k]:0;
        raw[EXPANSION]+=std::max(0,land_v)*.8; raw[CONSOLIDATION]+=land_v<=1?2:0;
        raw[ECONOMY]+=enemy_castle_events_*2 + (army_v < -20 ? 3:0);
