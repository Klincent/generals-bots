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
