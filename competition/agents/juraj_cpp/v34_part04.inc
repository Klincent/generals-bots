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
        raw[ATTACK]+=visible_enemy_stacks_.empty()?0:3; raw[SCOUTING]+=land_v>0?1.5:0;
        int pressure=0;
        for(auto s:visible_enemy_stacks_) if(general_>=0&&dist_[cell_id_[general_]][cell_id_[s.first]]<=6) pressure+=s.second;
        raw[ATTACK]+=pressure*.15; raw[DEFENSE]+=(o.my_land>o.opp_land?1.5:0);
        raw[DEATHTOUCH]+=(o.turn>=700?3:0)+(o.turn>=800?5:0);
        double sum=std::accumulate(raw.begin(),raw.end(),0.0);
        for(int i=0;i<MODE_COUNT;++i) mode_[i]=.75*mode_[i]+.25*raw[i]/sum;
        double norm=std::accumulate(mode_.begin(),mode_.end(),0.0); for(double&v:mode_)v/=norm;
    }

    int castle_cost(int x, const Observation& o) const {
        int cost=35;
        for(int s:id_cell_) {
            bool own_structure=(s==general_)||(known_castle_[s]&&(o.owner[s]==1||castle_owner_[s]==1));
            if (!own_structure) continue;
            int md=std::abs(row(x)-row(s))+std::abs(col(x)-col(s)); cost+=std::max(0,14-2*md);
        }
        return cost;
    }

    // Visible-board one-turn simulator. It mirrors build-before-moves, chase /
    // reinforce / smaller-source ordering, all-but-one/half rounding, strict
    // attack comparison and ties leaving zero armies with unchanged ownership.
    struct Sim { std::vector<int> owner, army; };
    int move_amount(const Sim&s,const Action&a)const{int z=s.army[cell(a.row,a.col)];return std::max(0,std::min(a.split?z/2:z-1,z-1));}
    bool sim_valid(const Sim&s,int who,const Action&a)const{if(a.kind!=0||!inside(a.row,a.col))return false;int x=cell(a.row,a.col),y=neighbor(x,a.dir);return y>=0&&passable_[y]&&s.owner[x]==who&&move_amount(s,a)>0;}
    void sim_apply(Sim&s,int who,const Action&a)const{if(!sim_valid(s,who,a))return;int x=cell(a.row,a.col),y=neighbor(x,a.dir),m=move_amount(s,a);s.army[x]-=m;if(s.owner[y]==who)s.army[y]+=m;else{int old=s.army[y];s.army[y]=std::abs(old-m);if(m>old)s.owner[y]=who;}}
    int sim_first(const Sim&s,const Action&a,const Action&b)const{
        if (a.kind!=0&&b.kind==0) return 2;
        if (b.kind!=0&&a.kind==0) return 1;
        int as=cell(a.row,a.col),bs=cell(b.row,b.col),ad=neighbor(as,a.dir),bd=neighbor(bs,b.dir);
        bool ac=ad==bs,bc=bd==as;if(ac!=bc)return bc?2:1;
        bool ar=ad>=0&&s.owner[ad]==1,br=bd>=0&&s.owner[bd]==2;if(ar!=br)return br?2:1;
        return s.army[bs]<s.army[as]?2:1;
    }
    Sim simulate(const Observation&o,const Action&mine,const Action&theirs)const{Sim s{o.owner,o.army};int f=sim_first(s,mine,theirs);if(f==1){sim_apply(s,1,mine);sim_apply(s,2,theirs);}else{sim_apply(s,2,theirs);sim_apply(s,1,mine);}return s;}

    Action move(int x,int y,int split=0) const { return {0,row(x),col(x),direction(x,y),split}; }
    Action pass() const { return {1,0,0,0,0}; }
    bool legal_source(const Observation&o,int x)const{return x>=0&&o.owner[x]==1&&o.army[x]>1;}
    bool overconcentrated(const Observation&o)const{return main_stack_>=0&&(o.army[main_stack_]>=std::max(80,(3*o.my_army+9)/10)||(enemy_general_>=0&&dist_[cell_id_[main_stack_]][cell_id_[enemy_general_]]>5&&o.army[main_stack_]>o.opp_army));}

    Action immediate_tactics(const Observation& o, bool& found) {
        found=true;
        // Any ordinary capture of a revealed general, or any legal post-800 touch.
        if(enemy_general_>=0) for(int d=0;d<4;++d){int x=neighbor(enemy_general_,d);if(!legal_source(o,x))continue;int m=o.army[x]-1;if(o.turn>=800||m>o.army[enemy_general_]){if(hunter_trigger_turn_>=0)++hunter_general_kill_attempts_;return move(x,enemy_general_);}}

        // Protect the general from an immediately visible capture/touch. First
        // eliminate the source if possible, else reinforce from the safest stack.
        if(general_>=0) for(int d=0;d<4;++d){int e=neighbor(general_,d);if(e<0||o.owner[e]!=2||o.army[e]<=1)continue;bool threat=o.turn>=800||(o.army[e]-1>o.army[general_]);if(!threat)continue;
            for(int d2=0;d2<4;++d2){int x=neighbor(e,d2);if(legal_source(o,x)&&o.army[x]-1>o.army[e])return move(x,e);}
            for(int d2=0;d2<4;++d2){int x=neighbor(general_,d2);if(legal_source(o,x)&&x!=e)return move(x,general_);}
        }
        found=false;return pass();
    }

    Action high_confidence_capture(const Observation&o,bool&found)const{
        double best=-1;Action ans=pass();found=false;
        for(int x:id_cell_)if(legal_source(o,x))for(int d=0;d<4;++d){int y=neighbor(x,d);if(y<0||o.owner[y]!=2)continue;int m=o.army[x]-1;if(m<=o.army[y])continue;double sc=100+o.army[y]*3+(o.type[y]==3?250:0);if(sc>best){best=sc;ans=move(x,y);}}
        if(best>=250)found=true;
        return ans;
    }

    Action defense_emergency(const Observation& o,bool& found) {
        found=false;if(required_defense_<=0||general_<0||visible_enemy_stacks_.empty())return pass();
        auto attacker=visible_enemy_stacks_.front();int e=attacker.first;
        // Prefer eliminating the moving source, which also defeats a post-800 touch.
        for(int d=0;d<4;++d){int x=neighbor(e,d);if(legal_source(o,x)&&o.army[x]-1>o.army[e]){found=true;++intercept_actions_;return move(x,e);}}
        // If the garrison is below the near-term requirement, an adjacent
        // feeder is the only reinforcement guaranteed to arrive this turn.
        if(o.turn<760&&o.army[general_]<required_defense_){int bx=-1;
            for(int d=0;d<4;++d){int x=neighbor(general_,d);if(legal_source(o,x)&&x!=e&&(bx<0||o.army[x]>o.army[bx]))bx=x;}
            if(bx>=0){found=true;++intercept_actions_;return move(bx,general_,0);}
        }
        int hop=next_hop_[cell_id_[e]][cell_id_[general_]];
        int intercept=o.turn>=700?e:(hop>=0?id_cell_[hop]:general_);
        double best=-1;Action ans=pass();
        for(int x:id_cell_)if(legal_source(o,x))for(int d=0;d<4;++d){int y=neighbor(x,d);if(y<0||o.owner[y]!=1)continue;
            bool useful=y==general_||y==intercept||dist_[cell_id_[y]][cell_id_[intercept]]<dist_[cell_id_[x]][cell_id_[intercept]];
            if(!useful)continue;
            if(o.owner[y]==2&&o.army[x]-1<=o.army[y])continue;
            double s=o.army[x]*8-dist_[cell_id_[y]][cell_id_[intercept]]*12+source_value(o,x)*.2;
            if(o.turn>=700)s+=o.army[x]*8-dist_[cell_id_[y]][cell_id_[e]]*25;
            if(x==general_&&o.army[general_]<required_defense_)s-=1000;
            if(s>best){best=s;ans=move(x,y,0);}}
        if(best>-1){found=true;++intercept_actions_;}return ans;
    }

    int distance_avoiding(int start,int goal,int blocked)const{
        if(start==blocked||goal==blocked)return INF;
        std::vector<int>d(n_,INF);std::queue<int>q;d[start]=0;q.push(start);
        while(!q.empty()){int x=q.front();q.pop();for(int k=0;k<4;++k){int y=neighbor(x,k);if(y>=0&&y!=blocked&&passable_[y]&&d[y]==INF){d[y]=d[x]+1;q.push(y);}}}return d[goal];
    }
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
