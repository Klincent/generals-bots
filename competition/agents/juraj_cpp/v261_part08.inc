    double local_counter_value(const Observation&o,const Action&a)const {
        int x=cell(a.row,a.col), y=neighbor(x,a.dir); double worst=0;
        for(auto e:visible_enemy_stacks_) if(e.second>2&&dist_[cell_id_[e.first]][cell_id_[y]]<=1) {
            Action ea=move(e.first,y,0); Sim after=simulate(o,a,ea);
            if(after.owner[y]==2)worst=std::max(worst,80.0+after.army[y]*3.0);
            if(general_>=0&&after.owner[general_]==2)worst=100000;
        }
        return -worst;
    }
    double score_variant(const Observation&o,int x,int y,int split,int until_tick,int candidate_peak)const {
        int moved=split?o.army[x]/2:o.army[x]-1, remain=o.army[x]-moved;
        int dest_after=o.owner[y]==1?o.army[y]+moved:std::abs(o.army[y]-moved);
        bool captures=o.owner[y]!=1&&moved>o.army[y];
        if(o.owner[y]==2&&!captures)return -1e100;
        double s=0;
        if(o.owner[y]==2)s+=500+4*o.army[y]+(o.type[y]==4?100000:0)+(o.type[y]==3?250:0);
        else if(o.owner[y]==0)s+=190+(until_tick<=12?80:0)+std::max(0,10-last_seen_[y])*4;
        else s-=35-(o.army[y]>1?10:0);
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
            if(o.owner[y]==0&&after>10&&until_tick>8)s*=strong_dominance_?.35:.48;
            else if(o.owner[y]==0&&after>6&&until_tick>8)s*=.72;
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
        Choice offense,economy,affinity;
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
