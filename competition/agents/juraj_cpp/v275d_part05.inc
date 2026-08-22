    Action hunter_gate_castle(const Observation&o,int hunter,bool&found){
        found=false;if(castles_built_>=1||hunter<0)return pass();int base=dist_[cell_id_[hunter]][cell_id_[general_]],best=-1,bx=-1,bdisc=0;
        for(int x:id_cell_)if(o.owner[x]==1&&o.type[x]==1&&articulation_[x]&&dist_[cell_id_[hunter]][cell_id_[x]]+dist_[cell_id_[x]][cell_id_[general_]]<=base+1){
            int cost=castle_cost(x,o);if(o.army[x]<cost+5)continue;int alt=distance_avoiding(hunter,general_,x);int gain=alt>=INF?1000:alt-base;
            if(gain>=4&&gain>best){best=gain;bx=x;bdisc=alt>=INF;}}
        if(bx>=0){found=true;++castles_built_;++hunter_gate_castles_;hunter_gate_disconnects_+=bdisc;castle_build_turns_.push_back(o.turn);return {2,row(bx),col(bx),0,0};}return pass();
    }
    void select_hunter_raider(const Observation&o){
        if(hunter_raider_>=0&&o.owner[hunter_raider_]==1&&o.army[hunter_raider_]>=8)return;
        int target=!hunter_breadcrumbs_.empty()?hunter_breadcrumbs_.front():(hunter_stack_history_.empty()?-1:hunter_stack_history_.front().cell);
        double best=-1e100;int bx=-1;
        for(int x:id_cell_)if(legal_source(o,x)&&x!=general_&&dist_[cell_id_[x]][cell_id_[general_]]>1){double s=o.army[x]*10-(target>=0?dist_[cell_id_[x]][cell_id_[target]]*5:0)+(o.army[x]>=12?100:0);if(s>best){best=s;bx=x;}}
        if(bx>=0){hunter_raider_=bx;if(hunter_raider_selected_turn_<0){hunter_raider_selected_turn_=o.turn;hunter_raider_selected_army_=o.army[bx];}hunter_raider_path_.push_back(bx);}
    }
    Action hunter_counterattack(const Observation&o,bool&found){
        found=false;if(hunter_signature_score_<.55||hunter_stack_history_.empty())return pass();strategy_=HUNTER_COUNTERATTACK;++hunter_mode_turns_;
        bool hunter_visible=!visible_enemy_stacks_.empty();int hunter=hunter_visible?visible_enemy_stacks_.front().first:hunter_stack_history_.back().cell,harmy=hunter_visible?visible_enemy_stacks_.front().second:hunter_stack_history_.back().army,heta=dist_[cell_id_[hunter]][cell_id_[general_]];
        // Hunter will advance into unfavorable combat: take a certain source kill now.
        if(hunter_visible)for(int d=0;d<4;++d){int x=neighbor(hunter,d);if(legal_source(o,x)&&o.army[x]-1>harmy){found=true;++hunter_convoy_kills_;return move(x,hunter,0);}}
        int hop=next_hop_[cell_id_[hunter]][cell_id_[general_]],next=hop>=0?id_cell_[hop]:-1;
        if(next>=0&&o.owner[next]==1&&o.army[next]>harmy+3){found=true;intentional_hold_=true;strategy_=HUNTER_KILL_ZONE;++hunter_kill_zone_holds_;return pass();}
        if(hunter_visible&&next>=0)for(int d=0;d<4;++d){int x=neighbor(next,d);if(!legal_source(o,x)||x==hunter)continue;Action block=move(x,next,0),advance=move(hunter,next,0);Sim after=simulate(o,block,advance);
            if(after.owner[next]==1&&after.army[next]>=3){found=true;strategy_=HUNTER_KILL_ZONE;++hunter_kill_zone_holds_;return block;}}
        bool gate=false;if(heta<=10){Action wall=hunter_gate_castle(o,hunter,gate);if(gate){found=true;return wall;}}
        select_hunter_raider(o);
        if(hunter_raider_<0)return pass();
        // A close conveyor with no located kill target is not a race we can
        // responsibly ignore; hand control to deterministic V2.2 interception.
        if(hunter_visible&&heta<=5&&enemy_general_<0)return pass();
        if(o.army[hunter_raider_]<6)return pass();
        int local=o.army[general_];for(int d=0;d<4;++d){int x=neighbor(general_,d);if(x>=0&&o.owner[x]==1)local+=std::max(0,o.army[x]-1);}
        int target=enemy_general_;
        if(target<0){
            // Continue the locally revealed one-army chain before routing to
            // older sightings; this is the actual road back to Hunter's feed.
            for(int d=0;d<4;++d){int y=neighbor(hunter_raider_,d);if(y>=0&&last_owner_[y]==2&&last_army_[y]<=3&&std::find(hunter_raider_path_.begin(),hunter_raider_path_.end(),y)==hunter_raider_path_.end()&&(target<0||dist_[cell_id_[y]][cell_id_[general_]]>dist_[cell_id_[target]][cell_id_[general_]]))target=y;}
            if(target<0&&!hunter_stack_history_.empty()){double best=-1e100;int origin=hunter_stack_history_.front().cell;
                for(int x:id_cell_)if(enemy_score_[x]>0){double s=-8.0*dist_[cell_id_[origin]][cell_id_[x]]+2.0*dist_[cell_id_[general_]][cell_id_[x]]+enemy_score_[x]*.001;if(s>best){best=s;target=x;}}}
            if(target<0)for(int b:hunter_breadcrumbs_)if(o.owner[b]!=1){target=b;break;}
            if(target<0&&!hunter_breadcrumbs_.empty())target=hunter_breadcrumbs_.front();
        }
        int reta=target>=0?dist_[cell_id_[hunter_raider_]][cell_id_[target]]:INF;
        bool race_safe=(o.turn<800&&local>=harmy+5)||heta>reta+2;
        if(target>=0&&race_safe){int source=hunter_raider_,nh=next_hop_[cell_id_[source]][cell_id_[target]];if(nh>=0){int y=id_cell_[nh];if(o.owner[y]!=2||o.army[source]-1>o.army[y]){found=true;++hunter_raider_progress_moves_;if(o.owner[y]==2&&o.army[y]<=3)++hunter_breadcrumb_moves_;hunter_raider_=y;hunter_raider_path_.push_back(y);return move(source,y,0);}}}
        return pass();
    }

    struct Choice { double score=-1e100; Action action{}; bool valid=false; };
    double source_value(const Observation&,int x)const {
        double v=(x==general_?180:0)+(known_castle_[x]?70:0)+(articulation_[x]?65:0)+(degree_[x]>=3?18:0);
        if(general_>=0&&dist_[cell_id_[x]][cell_id_[general_]]<=1)v+=55;
        if(x==main_stack_)v+=strategy_>=GENERAL_KNOWN_PREPARE?100:35;
        return v;
    }
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
        else if(o.owner[y]==0){
            s+=240+std::max(0,10-last_seen_[y])*4;
            if(until_tick<=5)s+=220;else if(until_tick<=10)s+=150;else if(until_tick<=20)s+=90;
            if(o.turn<300)s+=55;else if(o.turn<400)s+=30;
            if(land_behind_)s+=150;
            if(land_deficit_)s+=200;
            if(severe_land_deficit_)s+=400;
            if(enemy_general_<0&&turns_since_search_progress_>=3)s+=turns_since_search_progress_>=5?260:150;
            int openings=0;for(int d=0;d<4;++d){int z=neighbor(y,d);if(z>=0&&passable_[z]&&o.owner[z]!=1&&o.owner[z]!=2)++openings;}
            s+=openings*55+room_[y]*.8;
        }
        else s-=35-(o.army[y]>1?10:0);
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
