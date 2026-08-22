            int split=(both&&prefer_half)?1:0; double s=split?half:all;
            if(s<=-1e90)continue;
            int strategic_target=enemy_general_>=0?enemy_general_:static_cast<int>(std::max_element(enemy_score_.begin(),enemy_score_.end())-enemy_score_.begin());
            bool pressure=o.owner[y]==2||(strategic_target>=0&&enemy_score_[strategic_target]>0&&
                dist_[cell_id_[y]][cell_id_[strategic_target]]<dist_[cell_id_[x]][cell_id_[strategic_target]]);
            Choice& bucket=pressure?offense:economy;
            if(s>bucket.score){bucket={s,move(x,y,split),true};}
            if(o.owner[y]==0&&s>expansion.score)expansion={s,move(x,y,split),true};
        }
        // Interior forces are feeders: when no good frontier action exists, route
        // the most efficient one toward the main stack or its attack path.
        bool stop_feeding=enemy_general_>=0&&overconcentrated(o)&&dist_[cell_id_[main_stack_]][cell_id_[enemy_general_]]>5;
        if(main_stack_>=0&&!stop_feeding)for(int x:id_cell_)if(x!=main_stack_&&legal_source(o,x)&&o.owner[x]==1){int hop=next_hop_[cell_id_[x]][cell_id_[main_stack_]];if(hop>=0){int y=id_cell_[hop];double s=o.army[x]*7.0-dist_[cell_id_[x]][cell_id_[main_stack_]]*5+source_value(o,x)*.1;if(s>economy.score)economy={s,move(x,y,source_value(o,x)>60&&o.army[x]>=6),true};}}
        int feed_target=contact_staging_cell_>=0?contact_staging_cell_:front_stack_;
        if(contact_established_&&feed_target>=0)for(int x:id_cell_)if(x!=feed_target&&x!=front_stack_&&legal_source(o,x)){int hop=next_hop_[cell_id_[x]][cell_id_[feed_target]];if(hop>=0){int y=id_cell_[hop];double s=o.army[x]*6.0-dist_[cell_id_[x]][cell_id_[feed_target]]*9+(dominance_?180:80);if(s>economy.score)economy={s,move(x,y,0),true};}}
        if(enemy_general_>=0&&(main_stack_idle_turns_>=2||overconcentrated(o))&&economy.valid&&!land_deficit_){double factor=until_tick<=8?.65:.48;economy.score*=factor;}
        if(contact_established_&&contact_anchor_>=0){int attack=enemy_general_>=0?enemy_general_:(contact_staging_cell_>=0?contact_staging_cell_:contact_anchor_),dh=next_hop_[cell_id_[general_]][cell_id_[contact_anchor_]],defense=dh>=0?id_cell_[dh]:general_;
            int aa=0,da=0;for(int z:id_cell_)if(o.owner[z]==1){if(dist_[cell_id_[z]][cell_id_[attack]]<=5)aa+=o.army[z];if(dist_[cell_id_[z]][cell_id_[defense]]<=3)da+=o.army[z];}double target=strong_dominance_?.73:(dominance_?.65:.56);bool send_attack=aa<std::max(1,aa+da)*target;
            for(int x:id_cell_)if(legal_source(o,x)&&is_rear_low_value(o,x)){
                int threshold=(enemy_general_>=0||dominance_||degree_[x]==1)?5:8;if(o.army[x]<threshold)continue;
                int sink=send_attack?attack:defense,hop=next_hop_[cell_id_[x]][cell_id_[sink]];if(hop<0)continue;int y=id_cell_[hop];if(o.owner[y]==2)continue;
                int excess=o.army[x]-1;double s=excess*12.0+(enemy_general_>=0?160:0)+(dominance_?120:0);
                if(severe_land_deficit_&&expansion.valid)s-=1200;else if(land_deficit_&&expansion.valid)s-=500;
                if(s>rear_cleanup.score)rear_cleanup={s,move(x,y,0),true};
            }
        }
        // V2.7.5: a single, rate-limited logistics candidate may displace only
        // ordinary feeding.  It is deliberately not a mode or a forced layer.
        int existing_sink=main_stack_;
        if(enemy_general_>=0&&main_stack_>=0)existing_sink=main_stack_;
        else if(contact_established_)existing_sink=front_stack_>=0?front_stack_:(contact_staging_cell_>=0?contact_staging_cell_:contact_anchor_);
        int best_search=enemy_score_.empty()?-1:static_cast<int>(std::max_element(enemy_score_.begin(),enemy_score_.end())-enemy_score_.begin());
        if(existing_sink<0&&(strategy_==SEARCH_GENERAL||strategy_==QUALIFIER_PROBE)&&best_search>=0)existing_sink=best_search;
        // Any live Hunter evidence leaves V2.7.3's action distribution wholly
        // untouched; the .20 gate below remains the castle-specific ceiling.
        bool hunter_quiet=hunter_trigger_turn_<0&&hunter_signature_score_<=.001&&visible_enemy_stacks_.empty();
        if(existing_sink>=0&&hunter_quiet){
            for(int x:id_cell_)if(legal_source(o,x)&&o.owner[x]==1&&o.army[x]>=8){
                int edge=std::min({row(x),h_-1-row(x),col(x),w_-1-col(x)});
                if(edge>1&&degree_[x]>1&&terminal_depth_[x]<=0)continue;
                if(x==general_||known_castle_[x]||articulation_[x]||x==front_stack_||x==contact_staging_cell_||x==existing_sink)continue;
                int threat=INF;for(auto e:visible_enemy_stacks_)threat=std::min(threat,dist_[cell_id_[x]][cell_id_[e.first]]);if(threat<=5)continue;
                if(required_defense_>0&&dist_[cell_id_[x]][cell_id_[general_]]<=4)continue;
                if(best_search>=0&&enemy_general_<0&&dist_[cell_id_[general_]][cell_id_[x]]+dist_[cell_id_[x]][cell_id_[best_search]]<=dist_[cell_id_[general_]][cell_id_[best_search]]+1)continue;
                if(enemy_general_>=0&&dist_[cell_id_[general_]][cell_id_[x]]+dist_[cell_id_[x]][cell_id_[enemy_general_]]<=dist_[cell_id_[general_]][cell_id_[enemy_general_]]+1)continue;
                int min_gap=o.army[x]>=25?4:5;if(enemy_general_<0&&o.turn-last_edge_drain_turn_<min_gap)continue;
                int hop=next_hop_[cell_id_[x]][cell_id_[existing_sink]];if(hop<0)continue;int y=id_cell_[hop];if(o.owner[y]==2)continue;
                ++edge_large_sources_seen_;int surplus=o.army[x]-1;
                // Sub-20 stacks are eligible diagnostics, but deliberately too
                // weak to steal normal tempo; genuinely large piles can beat a
                // routine feeder while remaining far below attack/search value.
                double urgency=o.army[x]>=20?surplus*6.0+120:surplus*2.0+10;
                if(urgency>edge_surplus.score)edge_surplus={urgency,move(x,y,0),true};
            }
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
        Choice rear_drain=choose_rear_drain(o);if(rear_drain.valid&&(!economy.valid||rear_drain.score>economy.score))economy=rear_drain;
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
