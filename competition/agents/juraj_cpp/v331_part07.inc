
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
