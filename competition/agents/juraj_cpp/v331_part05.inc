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
        update_hunter_warning(o);update_hunter_suspicion(o);
    }
    void record_warning_entry(const Observation&o,int phase){int own=-1,oa=0;for(int x:id_cell_)if(o.owner[x]==1&&x!=general_&&o.army[x]>oa)oa=o.army[x],own=x;int es=visible_enemy_stacks_.empty()?-1:visible_enemy_stacks_.front().first,ea=es<0?0:o.army[es],packets=0;for(int x:id_cell_)if(o.owner[x]==1&&o.army[x]>=4)++packets;warning_entry_.push_back({o.turn,phase,o.my_land,o.opp_land,o.my_army,o.opp_army,general_>=0?o.army[general_]:0,oa,own<0?-1:dist_[cell_id_[own]][cell_id_[general_]],ea,es<0?-1:dist_[cell_id_[es]][cell_id_[general_]],packets,planned_castle_[0]>=0?o.army[planned_castle_[0]]:0,funding_[0].required,hunter_warning_score_,hunter_signature_score_});}
    void update_hunter_warning(const Observation&o){double ratio=0,proximity=0,persistence=0;bool corroborated=false;if(!visible_enemy_stacks_.empty()){auto e=visible_enemy_stacks_.front();ratio=(double)e.second/std::max(1,o.opp_army);int dg=dist_[cell_id_[e.first]][cell_id_[general_]];proximity=std::max(0,16-dg)/16.0;if(hunter_stack_history_.size()>=2){auto&a=hunter_stack_history_[hunter_stack_history_.size()-2];auto&b=hunter_stack_history_.back();bool adjacent=dist_[cell_id_[a.cell]][cell_id_[b.cell]]<=1,closing=b.distance_to_general<a.distance_to_general;persistence=adjacent?.18:0;if(adjacent&&closing)++hunter_warning_closing_streak_;else hunter_warning_closing_streak_=std::max(0,hunter_warning_closing_streak_-1);corroborated=adjacent&&(closing||hunter_warning_closing_streak_>=1);corroborated=corroborated||(ratio>=.15&&dg<=16);}}
        int land_gain=opp_land_hist_.size()>20?o.opp_land-opp_land_hist_[opp_land_hist_.size()-21]:o.opp_land;double low_growth=land_gain<=8&&ratio>=.30?.10:0;double observed=.55*hunter_signature_score_+.30*ratio+.22*proximity+persistence+low_growth+.06*std::min(2,hunter_warning_closing_streak_);hunter_warning_score_=.72*hunter_warning_score_+.28*std::clamp(observed,0.0,1.0);
        if(hunter_warning_first_evidence_<0&&hunter_warning_score_>=.06&&corroborated){hunter_warning_first_evidence_=o.turn;record_warning_entry(o,0);}if(!hunter_warning_active_&&hunter_trigger_turn_<0&&hunter_warning_score_>=.10&&corroborated){hunter_warning_active_=true;hunter_warning_turn_=o.turn;++hunter_warning_activations_;hunter_warning_clear_=0;record_warning_entry(o,1);}if(hunter_warning_active_){++hunter_warning_active_turns_;if(hunter_warning_score_<.05&&!corroborated){if(++hunter_warning_clear_>=8)hunter_warning_active_=false;}else hunter_warning_clear_=0;}if(hunter_trigger_turn_==o.turn){record_warning_entry(o,3);hunter_warning_active_=false;}
    }
    void record_hunter_entry(const Observation&o,int phase){int own=-1,oa=0;for(int x:id_cell_)if(o.owner[x]==1&&x!=general_&&o.army[x]>oa)oa=o.army[x],own=x;int es=visible_enemy_stacks_.empty()?-1:visible_enemy_stacks_.front().first,ea=es<0?0:o.army[es],packets=0;for(int x:id_cell_)if(o.owner[x]==1&&o.army[x]>=4)++packets;hunter_entry_.push_back({o.turn,phase,o.my_land,o.opp_land,o.my_army,o.opp_army,general_>=0?o.army[general_]:0,oa,own<0?-1:dist_[cell_id_[own]][cell_id_[general_]],ea,es<0?-1:dist_[cell_id_[es]][cell_id_[general_]],packets,planned_castle_[0]>=0?o.army[planned_castle_[0]]:0});}
    void update_hunter_suspicion(const Observation&o){bool dominant=false;if(!visible_enemy_stacks_.empty()){auto e=visible_enemy_stacks_.front();dominant=e.second>=std::max(10,o.opp_army/3)&&dist_[cell_id_[e.first]][cell_id_[general_]]<=16;}
        if(hunter_entry_.empty()&&hunter_signature_score_>=.10)record_hunter_entry(o,0);
        if(!hunter_suspicion_active_&&o.turn<=250&&(hunter_signature_score_>=.22||dominant)){hunter_suspicion_active_=true;hunter_suspicion_turn_=o.turn;hunter_suspicion_clear_=0;record_hunter_entry(o,1);}
        if(hunter_suspicion_active_&&hunter_trigger_turn_<0){if(hunter_signature_score_<.12&&!dominant){if(++hunter_suspicion_clear_>=8)hunter_suspicion_active_=false;}else hunter_suspicion_clear_=0;}
        if(hunter_trigger_turn_==o.turn)record_hunter_entry(o,2);
    }

    void find_reaction_stack(const Observation&o,int excluded=-1){reaction_cell_=-1;reaction_army_=0;reaction_dist_=INF;for(int x:id_cell_)if(x!=excluded&&o.owner[x]==1&&o.army[x]>=4&&degree_[x]>1){int d=dist_[cell_id_[x]][cell_id_[general_]];double value=o.army[x]*20-d*3+nav_[x].route_load*5;if(reaction_cell_<0||value>reaction_army_*20-reaction_dist_*3+nav_[reaction_cell_].route_load*5)reaction_cell_=x,reaction_army_=o.army[x],reaction_dist_=d;}}
    bool reaction_adequate()const{if(reaction_cell_<0)return false;bool force_adequate=reaction_army_>=approach_enemy_army_;bool central=nav_[reaction_cell_].route_load>=3;bool position_adequate=reaction_dist_<=approach_enemy_dist_+2||(central&&reaction_dist_<=approach_enemy_dist_+4);return force_adequate&&position_adequate;}
    void update_approach_threat(const Observation&o){
        find_reaction_stack(o);int ec=-1,ea=0,ed=INF;for(auto e:visible_enemy_stacks_)if(e.second>=8){int d=dist_[cell_id_[e.first]][cell_id_[general_]];double importance=e.second*(1.0+std::max(0,18-d)/18.0);if(ec<0||importance>ea*(1.0+std::max(0,18-ed)/18.0))ec=e.first,ea=e.second,ed=d;}
        bool seen=ec>=0,related=false;double closing=0;if(seen&&!approach_history_.empty()){auto p=approach_history_.back();int dt=std::max(1,o.turn-p.turn),travel=dist_[cell_id_[p.cell]][cell_id_[ec]];related=travel<=dt+2&&ea*2>=p.army&&p.army*2>=ea;closing=related?(double)(p.dist-ed)/dt:0;}
        if(seen){approach_persistence_=related?std::min(8,approach_persistence_+1):1;approach_history_.push_back({o.turn,ec,ea,ed});if(approach_history_.size()>12)approach_history_.erase(approach_history_.begin());approach_enemy_cell_=ec;approach_enemy_army_=ea;approach_enemy_dist_=ed;approach_closing_rate_=closing;
            double force=std::min(1.0,(double)ea/std::max(1,reaction_army_)),concentration=std::min(1.0,(double)ea/std::max(1,o.opp_army)/.50),proximity=std::clamp((18.0-ed)/18.0,0.0,1.0),closing_component=std::clamp(closing,0.0,1.0),persistence=std::min(1.0,std::max(0,approach_persistence_-1)/2.0),gap=std::min(1.0,std::max(0.0,(double)(ea-reaction_army_)/std::max(1,ea))+std::min(1.0,reaction_dist_/20.0)*.5);
            double raw=.25*force+.20*concentration+.15*proximity+.20*closing_component+.10*persistence+.10*gap;approach_threat_score_=.55*approach_threat_score_+.45*raw;
            bool qualifies=approach_persistence_>=2&&closing>0&&ea>=8&&(double)ea/std::max(1,o.opp_army)>=.12;if(!approach_threat_active_&&qualifies&&approach_threat_score_>=.55){approach_threat_active_=true;approach_threat_clear_=0;++approach_threat_activations_;if(approach_threat_first_turn_<0)approach_threat_first_turn_=o.turn;int c1=planned_castle_[0]>=0&&o.owner[planned_castle_[0]]==1?o.army[planned_castle_[0]]:0;approach_activations_log_.push_back({o.turn,ec,ea,o.opp_army,ed,approach_persistence_,reaction_cell_,reaction_army_,reaction_dist_,c1,(double)ea/std::max(1,o.opp_army),closing,approach_threat_score_,funding_[0].required==0,planned_castle_built_turn_[0]>=0,true,ea>=8,(double)ea/std::max(1,o.opp_army)>=.12});}
        }else{int age=approach_history_.empty()?INF:o.turn-approach_history_.back().turn;approach_threat_score_*=age<=3?.90:(age<=7?.72:.45);approach_closing_rate_=0;}
        approach_threat_max_score_=std::max(approach_threat_max_score_,approach_threat_score_);if(approach_threat_active_){++approach_threat_turns_;if(approach_last_land_)approach_land_gain_+=std::max(0,o.my_land-approach_last_land_);if(approach_threat_score_<=.30){if(++approach_threat_clear_>=5)approach_threat_active_=false;}else approach_threat_clear_=0;}approach_last_land_=o.my_land;
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
