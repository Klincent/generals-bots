        int unseen=0;for(int rr=-1;rr<=1;++rr)for(int cc=-1;cc<=1;++cc){int r=row(y)+rr,c=col(y)+cc;if(inside(r,c)&&last_seen_[cell(r,c)]<0)++unseen;}
        s+=unseen*(o.turn<800?20:24)+(articulation_[y]?45:0)+(degree_[y]<=1?-80:0)+room_[y]*1.2;
        s-=dist_[cell_id_[general_]][cell_id_[y]]*.35;
        int target=enemy_general_;
        if(target<0&&candidate_peak>0)target=static_cast<int>(std::max_element(enemy_score_.begin(),enemy_score_.end())-enemy_score_.begin());
        if(target>=0){int before=dist_[cell_id_[x]][cell_id_[target]],after=dist_[cell_id_[y]][cell_id_[target]];s+=(before-after)*(strategy_>=GENERAL_KNOWN_PREPARE?95:4);if(enemy_general_<0&&after<before)s+=80+(turns_since_search_progress_>=3?(turns_since_search_progress_>=5?250:140):0);}
        if(enemy_general_<0&&contact_established_&&o.owner[y]==2&&o.type[y]!=3&&o.army[y]<std::max(8,o.opp_army/10)&&unseen<2&&hunter_trigger_turn_<0&&consecutive_low_info_contact_>=2)s-=std::min(220,45*(consecutive_low_info_contact_-1));
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
    Action find_safe_neutral_capture(const Observation&o,bool&found)const{
        found=false;double best=-1e100;Action ans=pass();int until=50-o.turn%50;
        for(int x:id_cell_)if(legal_source(o,x))for(int d=0;d<4;++d){int y=neighbor(x,d);if(y<0||!passable_[y]||o.owner[y]!=0||o.type[y]!=1||o.army[x]-1<=o.army[y])continue;
            if(x==general_){bool danger=false;for(auto e:visible_enemy_stacks_)if(e.second>=2&&dist_[cell_id_[e.first]][cell_id_[general_]]<=2)danger=true;if(danger)continue;}
            double counter=local_counter_value(o,move(x,y,0));if(counter<=-10000)continue;
            int adjacent=0,nearby=0,unseen=0;for(int z:id_cell_){int dz=dist_[cell_id_[y]][cell_id_[z]];if(o.owner[z]==0&&o.type[z]==1&&dz<=3)++nearby;}
            for(int k=0;k<4;++k){int z=neighbor(y,k);if(z>=0&&o.owner[z]==0&&o.type[z]==1)++adjacent;if(z>=0&&last_seen_[z]<0)++unseen;}
            double s=adjacent*120+nearby*24+room_[y]*1.5+unseen*30+(until<=10?160:0)+(land_behind_?180:0)+(land_deficit_?260:0)+(o.turn<350?120:0)+counter;
            if(s>best){best=s;ans=move(x,y,0);found=true;}
        }return ans;
    }
    Action find_expansion_feed(const Observation&o,bool&found)const{
        found=false;double best=-1e100;Action ans=pass();
        for(int f:id_cell_)if(o.owner[f]==1){int adjacent=0,nearby=0,unseen=0,threat=INF;for(int z:id_cell_){int d=dist_[cell_id_[f]][cell_id_[z]];if(o.owner[z]==0&&o.type[z]==1&&d<=3)++nearby;}for(int d=0;d<4;++d){int z=neighbor(f,d);if(z>=0&&o.owner[z]==0&&o.type[z]==1)++adjacent;if(z>=0&&last_seen_[z]<0)++unseen;}if(!adjacent)continue;for(auto e:visible_enemy_stacks_)threat=std::min(threat,dist_[cell_id_[f]][cell_id_[e.first]]);if(threat<=2)continue;
            double frontier=adjacent*180+nearby*28+room_[f]+unseen*25;
            for(int x:id_cell_)if(x!=f&&legal_source(o,x)&&x!=general_&&!known_castle_[x]){int dx=dist_[cell_id_[x]][cell_id_[f]];if(dx>6)continue;int hop=next_hop_[cell_id_[x]][cell_id_[f]];if(hop<0)continue;int y=id_cell_[hop];if(o.owner[y]!=1)continue;double s=frontier+o.army[x]*8-dx*70+(dx<=3?240:0)+(land_behind_?260:0);if(s>best){best=s;ans=move(x,y,0);found=true;}}
        }return ans;
    }
    Action productive_fallback(const Observation&o,const Action&production,bool production_valid,int&replacement)const{
        replacement=0;if(production_valid){replacement=1;return production;}
        bool feed=false;Action a=find_expansion_feed(o,feed);if(feed){replacement=2;return a;}
        int target=-1;if(enemy_general_>=0)target=enemy_general_;else if(*std::max_element(enemy_score_.begin(),enemy_score_.end())>0)target=static_cast<int>(std::max_element(enemy_score_.begin(),enemy_score_.end())-enemy_score_.begin());
        if(target>=0){double best=-1e100;Action ans=pass();for(int x:id_cell_)if(legal_source(o,x)){int hop=next_hop_[cell_id_[x]][cell_id_[target]];if(hop<0)continue;int y=id_cell_[hop];if(o.owner[y]==2&&o.army[x]-1<=o.army[y])continue;double s=(dist_[cell_id_[x]][cell_id_[target]]-dist_[cell_id_[y]][cell_id_[target]])*100+o.army[x];if(s>best){best=s;ans=move(x,y,0);}}if(best>-1e90){replacement=3;return ans;}}
        return pass();
    }
    int v3_branch(int x)const{for(int b=0;b<primary_branch_count_;++b)if(nav_[x].first_hop_mask&(1u<<primary_branch_dir_[b]))return b;return -1;}
    bool v3_second_job(const Observation&o,int x,int chosen_dir)const{int jobs=0;for(int d=0;d<4;++d)if(d!=chosen_dir){int y=neighbor(x,d);if(y<0||!passable_[y])continue;bool frontier=o.owner[y]==0&&o.type[y]==1;bool route=edge_route_flow_[x][d]>.01||nav_[y].sector_route_mask!=nav_[x].sector_route_mask;if(frontier||route)++jobs;}return jobs>0;}
    std::pair<int,double> v31_secondary_objective(const Observation&o,int x,int chosen_dir,int moved_branch)const{int id=-1;double best=0;for(int d=0;d<4;++d)if(d!=chosen_dir){int y=neighbor(x,d);if(y<0||!passable_[y])continue;int b=v3_branch(y),space=0;for(int z:id_cell_)if(v3_branch(z)==b&&o.owner[z]==0)++space;double value=(b>=0&&b!=moved_branch&&space>=10?space*4.0:0)+edge_route_flow_[x][d]*300+(nav_[y].route_load>=2?80:0);if(value>best)best=value,id=(b>=0?b:9+nav_[y].sector);}return {id,best};}
    void update_castle_funding(const Observation&o){static constexpr int target[3]={145,178,235};for(int i=0;i<3;++i){int x=planned_castle_[i];if(x<0)continue;auto&f=funding_[i];f.live_cost=castle_cost(x,o);f.army=o.owner[x]==1?o.army[x]:0;f.required=std::max(0,f.live_cost-f.army);f.turns=std::max(1,target[i]-o.turn);f.urgency=(double)f.required/f.turns;f.closest=INF;for(int s:id_cell_)if(legal_source(o,s))f.closest=std::min(f.closest,dist_[cell_id_[s]][cell_id_[x]]);f.max_army=std::max(f.max_army,f.army);f.min_required=std::min(f.min_required,f.required);if(f.required==0&&planned_first_funded_[i]<0)planned_first_funded_[i]=o.turn;if(i==0&&f.required==0&&c1_first_funded_turn_<0)c1_first_funded_turn_=o.turn;if(i==0&&f.required==0&&o.owner[x]==1&&o.type[x]==1&&c1_first_buildable_turn_<0)c1_first_buildable_turn_=o.turn,c1_first_buildable_army_=f.army;if(o.turn%25==0)castle_checkpoints_.push_back({o.turn,i,f.live_cost,f.army,f.required,f.closest,f.urgency});}}
    Action maybe_v31_castle_action(const Observation&o){if(v3_castle_count_<=0||hunter_trigger_turn_>=0||required_defense_>0||production_emergency_)return pass();int i=0;while(i<3&&planned_castle_built_turn_[i]>=0)++i;if(i>=v3_castle_count_||i>=3||(i>0&&planned_castle_built_turn_[i-1]<0))return pass();static constexpr int lo[3]={140,165,220};int x=planned_castle_[i];if(x<0)return pass();auto&f=funding_[i];
        if(hunter_suspicion_active_){++f.skipped[2];return pass();}int danger=INF;for(auto e:visible_enemy_stacks_)danger=std::min(danger,dist_[cell_id_[x]][cell_id_[e.first]]);
        bool early=i==0&&o.turn<140,early_safe=!early||(o.my_army-f.live_cost>=std::max(80,(o.opp_army*5)/4)&&!hunter_warning_active_&&!hunter_suspicion_active_&&danger>5&&o.army[general_]>=6);
        if(i==0&&f.required==0&&o.turn<140&&!early_safe)c1_delay_reason_=hunter_warning_active_?2:(hunter_suspicion_active_?3:(danger<=5?7:5));
        bool approach_safe=true;if(approach_threat_active_){find_reaction_stack(o,x);int nearby=o.army[general_];for(int z:id_cell_)if(z!=x&&z!=general_&&o.owner[z]==1&&dist_[cell_id_[z]][cell_id_[general_]]<=5)nearby+=std::max(0,o.army[z]-1)/2;int eta=std::max(1,approach_enemy_dist_),needed=std::max(8,approach_enemy_army_-(eta>=10?6:0));approach_safe=std::max(reaction_army_,nearby)>=needed;if(f.required==0&&!approach_safe){++approach_castle_delays_;++planned_delay_turns_[i];if(i==0)++approach_c1_delay_turns_;++approach_c1_feed_suppressions_;approach_block_castle_feed_=true;approach_delayed_castle_index_=i;approach_changed_this_turn_=true;v3_action_label_="APPROACH_DELAY_C"+std::to_string(i+1);find_reaction_stack(o);return pass();}else if(f.required==0)v3_action_label_="APPROACH_ALLOW_C"+std::to_string(i+1);find_reaction_stack(o);}
        if(o.owner[x]==1&&o.type[x]==1&&o.turn>=lo[i]&&f.army>=f.live_cost&&early_safe&&approach_safe&&danger>2&&o.my_army-f.live_cost>=std::max(20,o.opp_army/2)&&castle_first_safe_[i]<0){castle_first_safe_[i]=o.turn;}
        if(o.owner[x]==1&&o.type[x]==1&&o.turn>=lo[i]&&f.army>=f.live_cost&&early_safe&&approach_safe&&!hunter_warning_active_&&!hunter_suspicion_active_&&danger>2&&o.my_army-f.live_cost>=std::max(20,o.opp_army/2)){planned_castle_built_turn_[i]=o.turn;planned_actual_cost_[i]=f.live_cost;++castles_built_;castle_build_turns_.push_back(o.turn);std::string type="v34_c"+std::to_string(i+1);record_castle(o,x,f.live_cost,f.live_cost,type.c_str());v3_action_label_=approach_threat_active_?"APPROACH_ALLOW_C"+std::to_string(i+1):"C"+std::to_string(i+1)+"_BUILD";return {2,row(x),col(x),0,0};}
        int fi=(f.required==0&&i+1<v3_castle_count_)?i+1:i,fx=planned_castle_[fi];auto&ff=funding_[fi];int start=fi?90:90,feed_danger=INF;for(auto e:visible_enemy_stacks_)feed_danger=std::min(feed_danger,dist_[cell_id_[fx]][cell_id_[e.first]]);if(o.turn>=start&&castle_funding_start_[fi]<0)castle_funding_start_[fi]=o.turn;if(o.turn<start||feed_danger<=2||ff.required==0){++ff.skipped[feed_danger<=2?1:5];return pass();}if(fi==0&&((o.turn<110&&o.turn%4)||(o.turn<130&&o.turn%2))){++ff.skipped[4];return pass();}
        double best=-1e100;int bx=-1,by=-1;for(int s:id_cell_)if(legal_source(o,s)&&s!=fx){int h=next_hop_[cell_id_[s]][cell_id_[fx]];if(h<0)continue;int y=id_cell_[h];if(o.owner[y]==2||(o.owner[y]==0&&o.army[s]-1<=o.army[y]))continue;if(s==general_&&o.army[s]<10)continue;double score=o.army[s]*8-dist_[cell_id_[s]][cell_id_[fx]]*12+(o.owner[y]==0?100:0);if(score>best)best=score,bx=s,by=y;}if(bx>=0){++ff.feeds;pending_v3_source_=bx;pending_v3_dest_=by;pending_v3_reason_=1;pending_v3_branch_=v3_branch(by);v3_action_label_="C"+std::to_string(fi+1)+"_FUND";return move(bx,by,0);}++ff.skipped[0];return pass();}
    Action hunter_suspicion_position(const Observation&o,bool&found){found=false;if(!hunter_suspicion_active_||hunter_trigger_turn_>=0)return pass();int bx=-1,by=-1;double best=-1e100;for(int x:id_cell_)if(legal_source(o,x)&&x!=general_){int dg=dist_[cell_id_[x]][cell_id_[general_]];if(dg<=3)continue;int h=next_hop_[cell_id_[x]][cell_id_[general_]];if(h<0)continue;int y=id_cell_[h];if(o.owner[y]!=1)continue;double s=o.army[x]*10+dg*4;if(s>best)best=s,bx=x,by=y;}if(bx>=0){found=true;v3_action_label_="HUNTER_SUSPECT_CONSOLIDATE";return move(bx,by,0);}return pass();}
    Action hunter_warning_position(const Observation&o,bool&found){found=false;if(!hunter_warning_active_||hunter_suspicion_active_||hunter_trigger_turn_>=0||o.turn%3)return pass();int bx=-1,by=-1,army=0;for(int x:id_cell_)if(legal_source(o,x)&&x!=general_&&o.army[x]>army&&dist_[cell_id_[x]][cell_id_[general_]]>7){int h=next_hop_[cell_id_[x]][cell_id_[general_]];if(h<0)continue;int y=id_cell_[h];if(o.owner[y]!=1||nav_[y].route_load==0)continue;army=o.army[x];bx=x;by=y;}if(bx>=0){found=true;v3_action_label_="HUNTER_WARNING_CONSOLIDATE";return move(bx,by,0);}return pass();}
    Action approach_threat_position(const Observation&o,bool&found){found=false;if(!approach_threat_active_||o.turn%4||reaction_cell_<0||reaction_dist_<=8||reaction_adequate())return pass();int h=next_hop_[cell_id_[reaction_cell_]][cell_id_[general_]];if(h<0)return pass();int y=id_cell_[h];if(o.owner[y]!=1||nav_[y].route_load==0)return pass();found=true;++approach_consolidations_;approach_changed_this_turn_=true;v3_action_label_="APPROACH_CONSOLIDATE";return move(reaction_cell_,y,0);}
    Choice choose_v3_production(const Observation&o){
        Choice best;int until=50-o.turn%50;int castle_index=0;while(castle_index<3&&(planned_castle_built_turn_[castle_index]>=0||funding_[castle_index].required==0))++castle_index;int largest=-1,largest_army=0;for(int z:id_cell_)if(legal_source(o,z)&&o.army[z]>largest_army)largest_army=o.army[z],largest=z;
