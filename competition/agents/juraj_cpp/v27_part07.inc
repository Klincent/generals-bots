        int unseen=0;for(int rr=-1;rr<=1;++rr)for(int cc=-1;cc<=1;++cc){int r=row(y)+rr,c=col(y)+cc;if(inside(r,c)&&last_seen_[cell(r,c)]<0)++unseen;}
        s+=unseen*(o.turn<800?16:24)+(articulation_[y]?45:0)+(degree_[y]<=1?-80:0)+room_[y]*1.2;
        s-=dist_[cell_id_[general_]][cell_id_[y]]*.35;
        int target=enemy_general_;
        if(target<0&&candidate_peak>0)target=static_cast<int>(std::max_element(enemy_score_.begin(),enemy_score_.end())-enemy_score_.begin());
        if(target>=0){int before=dist_[cell_id_[x]][cell_id_[target]],after=dist_[cell_id_[y]][cell_id_[target]];s+=(before-after)*(strategy_>=GENERAL_KNOWN_PREPARE?95:4);}
        // A qualified defender is likely to cover the unique shortest route.
        // Permit a one/two-step detour when it has mobility and less interception.
        if(target>=0&&x==main_stack_&&qualifier_defense_score_>.32){
            int before=dist_[cell_id_[x]][cell_id_[target]],after=dist_[cell_id_[y]][cell_id_[target]];
            if(after<=before+1){double risk=0;for(auto e:visible_enemy_stacks_)risk+=std::max(0,5-dist_[cell_id_[y]][cell_id_[e.first]])*e.second;
                s+=degree_[y]*13+room_[y]*.3-risk*2.5+(after>=before?28*qualifier_defense_score_:0);}
        }
        if(strategy_==QUALIFIER_FEINT&&target>=0){int d=dist_[cell_id_[y]][cell_id_[target]];if(d>=2&&d<=5)s+=90;else if(d<2)s-=120;}
        if(strategy_==QUALIFIER_EXPLOIT&&o.owner[y]==0)s+=120+(until_tick<=10?130:0);
        if(strategy_==GENERAL_CONTAINMENT&&target>=0){int d=dist_[cell_id_[y]][cell_id_[target]];s+=(d>=1&&d<=3?100:-30);if(o.owner[y]==2)s+=45;}
        if(strategy_==DEATHTOUCH_FORK&&target>=0&&dist_[cell_id_[y]][cell_id_[target]]==1)s+=2000;
        if(enemy_general_>=0&&x==main_stack_&&required_defense_==0){
            int before=dist_[cell_id_[x]][cell_id_[enemy_general_]],after=dist_[cell_id_[y]][cell_id_[enemy_general_]];
            bool staging=after<before||(before<=5&&after>=2&&after<=5);
            if(staging&&(main_stack_idle_turns_>=2||overconcentrated(o)))s+=800+std::min(700,main_stack_idle_turns_*120)+(overconcentrated(o)?300:0);
        }
        if(x==main_stack_&&degree_[x]==1&&x!=general_&&x!=enemy_general_&&degree_[y]>degree_[x])s+=700;
        if(contact_established_&&contact_anchor_>=0){
            int before=dist_[cell_id_[x]][cell_id_[contact_anchor_]],after=dist_[cell_id_[y]][cell_id_[contact_anchor_]];
            if(x==front_stack_&&after<before)s+=260+contact_idle_turns_*90+(dominance_?180:0)+(strong_dominance_?260:0);
            bool remote=o.army[x]>=std::max(80,o.my_army/4)&&before>7;
            if(remote&&after<before)s+=900+(strong_dominance_?450:0);
            if(o.owner[y]==2&&moved>=o.army[y]+2)s+=420+(dominance_?260:0)+(strong_dominance_?360:0);
            bool land_ahead=o.my_land*4>=o.opp_land*5;
            if(o.owner[y]==0&&land_ahead&&o.turn>=400&&!land_deficit_&&after>10&&until_tick>8)s*=strong_dominance_?.35:.48;
            else if(o.owner[y]==0&&land_ahead&&o.turn>=400&&!land_deficit_&&after>6&&until_tick>8)s*=.72;
            if(after<=6)s+=55;
        }
        double sv=source_value(o,x); s+=std::log1p(moved)*12+std::log1p(dest_after)*4;
        s+=std::min(sv,remain*7.0); if(remain<=1)s-=sv;
        if(split)s-=35; // action efficiency: retaining force must have real value
        if(x==main_stack_&&split)s-=70;
        if(split&&remain>=5&&dest_after>=5)s+=25; // two independently useful stacks
        if(split&&x==main_stack_&&qualifier_defense_score_>.48&&remain>=8&&dest_after>=8&&degree_[x]>=2&&degree_[y]>=2)s+=125;
        s+=local_counter_value(o,move(x,y,split));
        return s;
    }
    Action choose_strategic(const Observation& o) {
        Choice offense,economy,expansion,rear_cleanup;
        int next_tick=((o.turn/50)+1)*50, until_tick=next_tick-o.turn;
        int candidate_peak=*std::max_element(enemy_score_.begin(),enemy_score_.end());
        for(int x:id_cell_) if(legal_source(o,x)) for(int d=0;d<4;++d) {
            int y=neighbor(x,d); if(y<0||!passable_[y])continue;
            bool captures=o.owner[y]==2;
            bool target_progress=enemy_general_>=0&&dist_[cell_id_[y]][cell_id_[enemy_general_]]<dist_[cell_id_[x]][cell_id_[enemy_general_]];
            bool reverse=std::any_of(recent_significant_edges_.rbegin(),recent_significant_edges_.rend(),[&](auto e){return e.first==y&&e.second==x;});
            if(reverse&&!captures&&!target_progress){++reverse_candidates_rejected_;++two_cycle_detections_;continue;}
            double all=score_variant(o,x,y,0,until_tick,candidate_peak), half=score_variant(o,x,y,1,until_tick,candidate_peak);
            int revisits=static_cast<int>(std::count(recent_main_stack_positions_.begin(),recent_main_stack_positions_.end(),y));
            if(x==main_stack_&&revisits){double penalty=180.0*revisits;all-=penalty;half-=penalty;++repeated_cell_penalties_;max_main_stack_recent_revisits_=std::max(max_main_stack_recent_revisits_,revisits);if(revisits>=2)++short_cycle_detections_;}
            bool half_distinct=o.army[x]/2!=o.army[x]-1, both=half_distinct&&all>-1e90&&half>-1e90;
            bool prefer_half=half>all;
            if(both){++split_flip_opportunities_;if(flip10()){prefer_half=!prefer_half;++split_flips_taken_;}}
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
        if(enemy_general_<0&&offense.valid&&(strategy_==SEARCH_GENERAL||strategy_==QUALIFIER_PROBE)){int x=cell(offense.action.row,offense.action.col),y=neighbor(x,offense.action.dir),best=static_cast<int>(std::max_element(enemy_score_.begin(),enemy_score_.end())-enemy_score_.begin()),unseen=0;for(int d=0;d<4;++d){int z=neighbor(y,d);if(z>=0&&last_seen_[z]<0)++unseen;}if((enemy_score_[best]>0&&dist_[cell_id_[y]][cell_id_[best]]<dist_[cell_id_[x]][cell_id_[best]])||unseen>=2)return offense.action;}
        // Territory is permanent production.  While the opening is still
        // claiming space, or whenever the ledger says we are behind, use the
        // best safe frontier capture before consolidation and cleanup.  Exact
        // tactical captures and general/Hunter emergencies have already run.
        if(expansion.valid&&(o.turn<300||land_deficit_||severe_land_deficit_))return expansion.action;
        if(expansion.valid&&(land_deficit_||o.turn<300)&&( !economy.valid||expansion.score>=economy.score))economy=expansion;
        if(rear_cleanup.valid&&(!economy.valid||rear_cleanup.score>economy.score)){economy=rear_cleanup;pending_rear_source_=cell(economy.action.row,economy.action.col);pending_rear_dest_=neighbor(pending_rear_source_,economy.action.dir);}
        if(!offense.valid)return economy.valid?economy.action:pass();
        if(!economy.valid)return offense.action;
        bool prefer_offense=offense.score>economy.score;
        ++strategic_flip_opportunities_; if(flip10()){prefer_offense=!prefer_offense;++strategic_flips_taken_;}
        Action chosen=prefer_offense?offense.action:economy.action;
        if(strategy_==QUALIFIER_FEINT)++feint_actions_;
        if(strategy_==DEATHTOUCH_FORK||(chosen.kind==0&&chosen.split&&cell(chosen.row,chosen.col)==main_stack_&&qualifier_defense_score_>.48))++fork_actions_;
        return chosen;
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
