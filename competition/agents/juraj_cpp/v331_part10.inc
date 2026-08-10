        }
        if(enemy_general_<0&&offense.valid&&(strategy_==SEARCH_GENERAL||strategy_==QUALIFIER_PROBE)){int x=cell(offense.action.row,offense.action.col),y=neighbor(x,offense.action.dir),best=static_cast<int>(std::max_element(enemy_score_.begin(),enemy_score_.end())-enemy_score_.begin()),unseen=0;for(int d=0;d<4;++d){int z=neighbor(y,d);if(z>=0&&last_seen_[z]<0)++unseen;}if((enemy_score_[best]>0&&dist_[cell_id_[y]][cell_id_[best]]<dist_[cell_id_[x]][cell_id_[best]])||unseen>=2)return offense.action;}
        // V2.7.2 restores normal offense/economy competition.  Production is
        // a score modifier, not an opening command.  Only a hysteretic, severe
        // production emergency may displace ordinary consolidation, and even
        // then a legitimate offensive candidate still competes normally.
        if(production_emergency_&&expansion.valid){expansion.score+=350;if(!economy.valid||expansion.score>economy.score)economy=expansion;}
        if(production_emergency_&&!expansion.valid&&!offense.valid){bool feed_valid=false;Action feed=find_expansion_feed(o,feed_valid);if(feed_valid){pending_frontier_feed_source_=cell(feed.row,feed.col);pending_frontier_feed_dest_=neighbor(pending_frontier_feed_source_,feed.dir);return feed;}}
        // V3 replaces legacy opening feeders/affinity cleanup with one explicit
        // route-production choice. Existing search below remains authoritative.
        if(enemy_general_<0&&hunter_trigger_turn_<0&&!contact_established_){Choice routed=choose_v3_production(o);if(routed.valid)economy=routed;}
        if(!offense.valid)return economy.valid?economy.action:pass();
        if(!economy.valid){pending_v3_source_=pending_v3_dest_=-1;return offense.action;}
        bool prefer_offense=offense.score>economy.score;
        ++strategic_flip_opportunities_; if(flip10()){prefer_offense=!prefer_offense;++strategic_flips_taken_;}
        Action chosen=prefer_offense?offense.action:economy.action;
        if(chosen.kind!=0||cell(chosen.row,chosen.col)!=pending_v3_source_||neighbor(pending_v3_source_,chosen.dir)!=pending_v3_dest_||chosen.split!=economy.action.split)pending_v3_source_=pending_v3_dest_=-1;
        if(strategy_==QUALIFIER_FEINT)++feint_actions_;
        if(strategy_==DEATHTOUCH_FORK||(chosen.kind==0&&chosen.split&&cell(chosen.row,chosen.col)==main_stack_&&qualifier_defense_score_>.48))++fork_actions_;
        return chosen;
    }

    void update_exploration_tempo(const Observation&o,const Action&a,bool forced){
        if(enemy_general_>=0){turns_since_search_progress_=0;consecutive_low_info_contact_=0;return;}
        if(forced)return;
        bool progress=false,ordinary_contact=false;
        if(a.kind==0){int x=cell(a.row,a.col),y=neighbor(x,a.dir),unseen=0;for(int d=0;d<4;++d){int z=neighbor(y,d);if(z>=0&&last_seen_[z]<0)++unseen;}
            if(o.owner[y]==0)progress=true;
            int best=static_cast<int>(std::max_element(enemy_score_.begin(),enemy_score_.end())-enemy_score_.begin());
            bool search=enemy_score_[best]>0&&dist_[cell_id_[y]][cell_id_[best]]<dist_[cell_id_[x]][cell_id_[best]];
            if(search){progress=true;++search_progress_actions_;}
            if(unseen>=2){progress=true;++meaningful_fog_reveal_actions_;}
            ordinary_contact=contact_established_&&o.owner[y]==2&&o.type[y]!=3&&o.army[y]<std::max(8,o.opp_army/10)&&unseen<2&&hunter_trigger_turn_<0;
        }
        if(progress)turns_since_search_progress_=0;else ++turns_since_search_progress_;
        if(ordinary_contact){if(consecutive_low_info_contact_>=2)++contact_repetition_penalties_;++consecutive_low_info_contact_;}else consecutive_low_info_contact_=0;
    }

    void update_main_stack_metrics(const Observation&o,const Action&a,bool forced_defense){
        if(main_stack_<0)return;
        if(enemy_general_>=0&&trace_discovery_turn_<0){trace_discovery_turn_=o.turn;trace_main_army_=o.army[main_stack_];trace_main_distance_=dist_[cell_id_[main_stack_]][cell_id_[enemy_general_]];discovery_main_path_.push_back(main_stack_);}
        max_main_stack_army_=std::max(max_main_stack_army_,o.army[main_stack_]);
        double fraction=o.my_army?100.0*o.army[main_stack_]/o.my_army:0;
        max_main_stack_fraction_pct_=std::max(max_main_stack_fraction_pct_,fraction);
        bool over=overconcentrated(o);if(over)++overconcentrated_turns_;
        if(forced_defense)return;
        bool progress=false;int x=-1,y=-1;
        if(a.kind==0){x=cell(a.row,a.col);y=neighbor(x,a.dir);
            if(x==main_stack_){int before=enemy_general_>=0?dist_[cell_id_[x]][cell_id_[enemy_general_]]:INF,after=enemy_general_>=0?dist_[cell_id_[y]][cell_id_[enemy_general_]]:INF;
                progress=after<before||o.owner[y]!=1||(degree_[x]==1&&degree_[y]>1);
                if(degree_[x]==1&&degree_[y]>1)++dead_end_escape_moves_;
                if(recent_main_stack_positions_.empty()||recent_main_stack_positions_.back()!=x)recent_main_stack_positions_.push_back(x);
                recent_main_stack_positions_.push_back(y);
                while(recent_main_stack_positions_.size()>12)recent_main_stack_positions_.erase(recent_main_stack_positions_.begin());
                if(trace_discovery_turn_>=0&&discovery_main_path_.size()<11)discovery_main_path_.push_back(y);
            }
            if(x==main_stack_||o.army[x]>=std::max(20,o.my_army/10)){recent_significant_edges_.push_back({x,y});if(recent_significant_edges_.size()>8)recent_significant_edges_.erase(recent_significant_edges_.begin());}
        }
        if(enemy_general_>=0){if(progress){main_stack_idle_turns_=0;++main_stack_progress_moves_;}else{++main_stack_idle_turns_;if(over)++overconcentrated_idle_turns_;}main_stack_idle_max_=std::max(main_stack_idle_max_,main_stack_idle_turns_);}
    }
    void update_contact_metrics(const Observation&o,const Action&a,bool forced_defense){
        if(!contact_established_)return;
        std::string cls="OTHER";bool progress=false;
        if(forced_defense){cls="DEFENSE";}
        else if(a.kind==2&&o.turn==contact_castle_turn_){cls="FRONT_CASTLE";progress=true;}
        else if(a.kind==0){int x=cell(a.row,a.col),y=neighbor(x,a.dir),before=dist_[cell_id_[x]][cell_id_[contact_anchor_]],after=dist_[cell_id_[y]][cell_id_[contact_anchor_]];
            if(o.owner[y]==2){cls="FRONT_PRESSURE";progress=true;++enemy_frontier_captures_;}
            else if(y==contact_staging_cell_||y==front_stack_){cls="FRONT_FEED";progress=true;++front_feeder_moves_;}
            else if(x==front_stack_&&after<before){cls="FRONT_PRESSURE";progress=true;++front_stack_moves_;}
            else if(o.army[x]>=std::max(80,o.my_army/4)&&before>7&&after<before){cls="FRONT_PRESSURE";progress=true;++remote_relocation_moves_;}
            else if(o.owner[y]==0&&after>8)cls="REMOTE_EXPANSION";
            else if(after<before){cls="FRONT_PRESSURE";progress=true;}
        }
        if(!forced_defense){if(progress){contact_idle_turns_=0;++contact_pressure_turns_;}else ++contact_idle_turns_;contact_idle_max_=std::max(contact_idle_max_,contact_idle_turns_);}
        if(contact_action_trace_.size()<20)contact_action_trace_.push_back(cls);
        if(a.kind==0&&pending_rear_source_==cell(a.row,a.col)&&pending_rear_dest_==neighbor(pending_rear_source_,a.dir)){
            int moved=o.army[pending_rear_source_]-1;++rear_surplus_moves_;rear_surplus_army_moved_+=moved;
        }
    }

    void record_castle(const Observation&o,int x,int cost,int min_cost,const char* type){
        castle_records_.push_back({o.turn,x,cost,min_cost,std::abs(row(x)-row(general_))+std::abs(col(x)-col(general_)),hunter_signature_score_,o.my_land,o.opp_land,o.my_army,o.opp_army,type});
        if(first_castle_turn_<0)first_castle_turn_=o.turn;
    }
    bool proactive_castle_health(const Observation&o)const{
        if(production_emergency_||required_defense_>0||hunter_trigger_turn_>=0||hunter_signature_score_>=.20)return false;
        bool healthy=(o.my_land*10>=o.opp_land*9&&o.my_army*10>=o.opp_army*9)||dominance_;
        if(!healthy)return false;
        for(auto e:visible_enemy_stacks_)if(e.second>=std::max(20,o.my_army/4)&&dist_[cell_id_[e.first]][cell_id_[general_]]<=9)return false;
        return true;
    }
    Action maybe_build(const Observation& o) {
        if(castles_built_>=1||enemy_general_>=0||o.turn<250||o.turn>550||mode_[ATTACK]>.30||!proactive_castle_health(o))return pass();
        int target=static_cast<int>(std::max_element(enemy_score_.begin(),enemy_score_.end())-enemy_score_.begin());
        if(target<0||enemy_score_[target]<=0)return pass();
        struct C{int x,cost;double utility;};std::vector<C> cs;int axis=dist_[cell_id_[general_]][cell_id_[target]],min_cost=INF;
        for(int x:id_cell_)if(o.owner[x]==1&&o.type[x]==1){int md=std::abs(row(x)-row(general_))+std::abs(col(x)-col(general_));if(md<5)continue;int dc=dist_[cell_id_[general_]][cell_id_[x]],dt=dist_[cell_id_[x]][cell_id_[target]];if(dc+dt>axis+3||dt>=axis)continue;int cost=castle_cost(x,o);if(1200-o.turn<2*cost+100||o.army[x]<cost+10||o.my_army-cost<o.opp_army*9/10)continue;int danger=INF;for(auto e:visible_enemy_stacks_)danger=std::min(danger,dist_[cell_id_[x]][cell_id_[e.first]]);if(danger<6)continue;double u=(articulation_[x]?40:0)+room_[x]+degree_[x]*10-dt*2+(md>=7?30:0);cs.push_back({x,cost,u});min_cost=std::min(min_cost,cost);}
        int bx=-1,bc=0;double best=-1e100;for(auto c:cs)if(c.cost<=min_cost+2&&c.utility>best){best=c.utility;bx=c.x;bc=c.cost;}
        if(bx>=0){++castles_built_;castle_build_turns_.push_back(o.turn);record_castle(o,bx,bc,min_cost,"proactive");return {2,row(bx),col(bx),0,0};}return pass();
    }
