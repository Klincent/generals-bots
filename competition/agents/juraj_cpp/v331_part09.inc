        double best=-1e100;int bx=-1,by=-1;for(int s:id_cell_)if(legal_source(o,s)&&s!=x){int h=next_hop_[cell_id_[s]][cell_id_[x]];if(h<0)continue;int y=id_cell_[h];if(o.owner[y]==2||(o.owner[y]==0&&o.army[s]-1<=o.army[y]))continue;if(s==general_&&o.army[s]<10)continue;double score=o.army[s]*8-dist_[cell_id_[s]][cell_id_[x]]*12+(o.owner[y]==0?100:0);if(score>best)best=score,bx=s,by=y;}if(bx>=0){++f.feeds;pending_v3_source_=bx;pending_v3_dest_=by;pending_v3_reason_=1;pending_v3_branch_=v3_branch(by);v3_action_label_=i?"C2_FUND":"C1_FUND";return move(bx,by,0);}++f.skipped[0];return pass();}
    Action hunter_suspicion_position(const Observation&o,bool&found){found=false;if(!hunter_suspicion_active_||hunter_trigger_turn_>=0)return pass();int bx=-1,by=-1;double best=-1e100;for(int x:id_cell_)if(legal_source(o,x)&&x!=general_){int dg=dist_[cell_id_[x]][cell_id_[general_]];if(dg<=3)continue;int h=next_hop_[cell_id_[x]][cell_id_[general_]];if(h<0)continue;int y=id_cell_[h];if(o.owner[y]!=1)continue;double s=o.army[x]*10+dg*4;if(s>best)best=s,bx=x,by=y;}if(bx>=0){found=true;v3_action_label_="HUNTER_SUSPECT_CONSOLIDATE";return move(bx,by,0);}return pass();}
    Action hunter_warning_position(const Observation&o,bool&found){found=false;if(!hunter_warning_active_||hunter_suspicion_active_||hunter_trigger_turn_>=0||o.turn%3)return pass();int bx=-1,by=-1,army=0;for(int x:id_cell_)if(legal_source(o,x)&&x!=general_&&o.army[x]>army&&dist_[cell_id_[x]][cell_id_[general_]]>7){int h=next_hop_[cell_id_[x]][cell_id_[general_]];if(h<0)continue;int y=id_cell_[h];if(o.owner[y]!=1||nav_[y].route_load==0)continue;army=o.army[x];bx=x;by=y;}if(bx>=0){found=true;v3_action_label_="HUNTER_WARNING_CONSOLIDATE";return move(bx,by,0);}return pass();}
    Action approach_threat_position(const Observation&o,bool&found){found=false;if(!approach_threat_active_||o.turn%4||reaction_cell_<0||reaction_dist_<=8||reaction_adequate())return pass();int h=next_hop_[cell_id_[reaction_cell_]][cell_id_[general_]];if(h<0)return pass();int y=id_cell_[h];if(o.owner[y]!=1||nav_[y].route_load==0)return pass();found=true;++approach_consolidations_;approach_changed_this_turn_=true;v3_action_label_="APPROACH_CONSOLIDATE";return move(reaction_cell_,y,0);}
    Choice choose_v3_production(const Observation&o){
        Choice best;int until=50-o.turn%50;int castle_index=planned_castle_built_turn_[0]<0?0:(planned_castle_built_turn_[1]<0?1:2),largest=-1,largest_army=0;for(int z:id_cell_)if(legal_source(o,z)&&o.army[z]>largest_army)largest_army=o.army[z],largest=z;
        for(int x:id_cell_)if(legal_source(o,x))for(int d=0;d<4;++d){int y=neighbor(x,d);if(y<0||!passable_[y]||o.owner[y]==2)continue;bool neutral=o.owner[y]==0&&o.type[y]==1;bool opens=false;int open=0,unseen=0;for(int k=0;k<4;++k){int z=neighbor(y,k);if(z>=0&&o.owner[z]==0&&o.type[z]==1)++open;if(z>=0&&last_seen_[z]<0)++unseen;}opens=open>0;
            int objective=neutral?y:(castle_index<v3_castle_count_?planned_castle_[castle_index]:-1);bool castle_feed=objective>=0&&!neutral&&o.owner[y]==1&&dist_[cell_id_[y]][cell_id_[objective]]<dist_[cell_id_[x]][cell_id_[objective]];
            if(!neutral&&!castle_feed)continue;
            if(castle_feed&&approach_block_castle_feed_)continue;
            bool progress=neutral||(objective>=0&&dist_[cell_id_[y]][cell_id_[objective]]<dist_[cell_id_[x]][cell_id_[objective]]);int recent=-1;for(int i=(int)v3_packet_path_.size()-1;i>=0;--i)if(v3_packet_path_[i]==y){recent=(int)v3_packet_path_.size()-i;break;}if(recent>=2&&recent<=4&&!progress){if(recent==2)++cycle2_rejected_;else if(recent==3)++cycle3_rejected_;else ++cycle4_rejected_;continue;}
            double s=neutral?520+open*95+unseen*55+nav_[y].breakthrough_gain*3+nav_[y].route_flow*120+nav_[y].route_load*12:180+nav_[y].static_route_value*.2-o.turn*.15;
            if(hunter_warning_active_){s+=nav_[y].route_load*18-dist_[cell_id_[y]][cell_id_[general_]]*3;if(x==largest&&dist_[cell_id_[y]][cell_id_[general_]]>dist_[cell_id_[x]][cell_id_[general_]])s-=260;}
            if(approach_threat_active_){s+=nav_[y].route_load*10;if(x==reaction_cell_&&!reaction_adequate()&&dist_[cell_id_[y]][cell_id_[general_]]>reaction_dist_){++approach_candidate_rejections_;approach_changed_this_turn_=true;continue;}}
            if(neutral&&until<=5)s+=220;else if(neutral&&until<=12)s+=120;if(neutral&&opens)s+=140;if(castle_feed&&o.turn<(castle_index?220:100))s-=260;
            if(recent>=5&&recent<=10){s-=350;++cycle5to10_penalized_;}
            int moved_branch=v3_branch(y);auto secondary=v31_secondary_objective(o,x,d,moved_branch);bool second=secondary.first>=0&&secondary.second>=120,half=false;
            if(o.army[x]>=10&&second&&!castle_feed&&!hunter_warning_active_&&!hunter_suspicion_active_&&!approach_threat_active_&&neutral&&open>=2&&degree_[x]>=3){if(v3_split_policy_==1)half=true;else if(v3_split_policy_==2){int moved=o.army[x]/2,remain=o.army[x]-moved;half=moved>=4&&remain>=5;}}
            if(v3_split_policy_==0)half=false;
            if(half)s+=90;else if(second&&v3_split_policy_==2)s-=10;
            if(s>best.score){best={s,move(x,y,half),true};pending_v3_reason_=half?(castle_feed?2:(until<=10?3:0)):(castle_feed?1:0);pending_v3_branch_=v3_branch(y);pending_v3_source_=x;pending_v3_dest_=y;pending_v3_secondary_value_=half?secondary.second:0;v3_action_label_=half?"V3_FORK_HALF":(castle_feed?(castle_index?"C2_FUND":"C1_FUND"):(approach_threat_active_?"APPROACH_SAFE_EXPAND":"V3_EXPAND_FULL"));}
        }if(approach_changed_this_turn_&&best.valid)v3_action_label_="APPROACH_KEEP_REACTION";return best;
    }
    Action maybe_v3_castle(const Observation&o){
        if(v3_castle_count_<=0||contact_established_||enemy_general_>=0||required_defense_>0||hunter_signature_score_>.12||production_emergency_)return pass();
        int i=planned_castle_built_turn_[0]<0?0:1;if(i>=v3_castle_count_)return pass();int x=planned_castle_[i],target=i?250:150;
        if(x<0||o.owner[x]!=1||o.type[x]!=1||o.turn<target-10||o.turn>target+45)return pass();
        int cost=castle_cost(x,o);if(o.army[x]<cost+5)return pass();
        planned_castle_built_turn_[i]=o.turn;++castles_built_;castle_build_turns_.push_back(o.turn);record_castle(o,x,cost,cost,i?"v3_c2":"v3_c1");v3_action_label_=i?"CASTLE2_BUILD":"CASTLE1_BUILD";return {2,row(x),col(x),0,0};
    }
    Action choose_strategic(const Observation& o) {
        Choice offense,economy,expansion,rear_cleanup,edge_surplus;
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
