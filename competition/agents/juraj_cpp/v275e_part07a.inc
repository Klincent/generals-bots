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
    Action maybe_contact_castle(const Observation&o){
        if(!contact_established_||contact_anchor_<0||contact_castle_built_||hunter_trigger_turn_>=0||castles_built_>=2)return pass();
        if(severe_land_deficit_&&castles_built_>=1)return pass();
        for(int x:id_cell_)if(known_castle_[x]&&o.owner[x]==1){int d=dist_[cell_id_[x]][cell_id_[contact_anchor_]];if(d>=2&&d<=4){contact_castle_built_=true;contact_staging_cell_=x;return pass();}}
        if(o.turn-first_contact_turn_<4)return pass();
        struct C{int x,cost,d;double utility;};std::vector<C> cs;int min_cost=INF;
        for(int x:id_cell_)if(o.owner[x]==1&&o.type[x]==1){int d=dist_[cell_id_[x]][cell_id_[contact_anchor_]];if(d<2||d>4)continue;int cost=castle_cost(x,o);if(o.army[x]<cost+8)continue;int danger=INF;for(auto e:visible_enemy_stacks_)danger=std::min(danger,dist_[cell_id_[x]][cell_id_[e.first]]);if(danger<=2)continue;double u=degree_[x]*24+room_[x]+(articulation_[x]?70:0)-d*8;cs.push_back({x,cost,d,u});min_cost=std::min(min_cost,cost);}
        double best=-1e100;int bx=-1,bc=0,bd=0;for(auto c:cs){
            // Preserve the known-good V2.7.3 contact-castle choice as soon as
            // Hunter-like evidence exists; changing this early blocker was the
            // source of the rejected Hunter regression.
            if(hunter_signature_score_<.05&&c.cost>min_cost+2)continue;
            if(c.utility>best){best=c.utility;bx=c.x;bc=c.cost;bd=c.d;}}
        if(bx<0)return pass();
        bool second=castles_built_==1;contact_castle_built_=true;contact_staging_cell_=bx;contact_castle_turn_=o.turn;++contact_castles_built_;++castles_built_;castle_build_turns_.push_back(o.turn);record_castle(o,bx,bc,min_cost,"contact");if(second){second_castle_turn_=o.turn;second_castle_cost_=bc;second_castle_attack_utility_=best;second_castle_defense_utility_=degree_[bx]*10+(articulation_[bx]?35:0);second_castle_distance_to_front_=bd;}return {2,row(bx),col(bx),0,0};
    }
    Action maybe_second_castle(const Observation&o){
        if(castles_built_!=1||o.turn>700||first_castle_turn_<0||o.turn-first_castle_turn_<150||land_behind_||o.my_army<o.opp_army||!proactive_castle_health(o))return pass();
        int front=enemy_general_>=0?enemy_general_:(contact_anchor_>=0?contact_anchor_:static_cast<int>(std::max_element(enemy_score_.begin(),enemy_score_.end())-enemy_score_.begin()));if(front<0)return pass();
        bool first_far=true;for(int x:id_cell_)if(known_castle_[x]&&o.owner[x]==1&&dist_[cell_id_[x]][cell_id_[front]]<=6)first_far=false;
        if(!enemy_castle_response_pending_&&!strong_dominance_&&!dominance_&&!first_far)return pass();
        struct C{int x,cost,df;double au,du,utility;};std::vector<C> cs;int min_cost=INF,axis=dist_[cell_id_[general_]][cell_id_[front]];
        for(int x:id_cell_)if(o.owner[x]==1&&o.type[x]==1){int df=dist_[cell_id_[x]][cell_id_[front]];if(df<2||df>6)continue;if(dist_[cell_id_[general_]][cell_id_[x]]+df>axis+3)continue;int cost=castle_cost(x,o);if(o.army[x]<cost+10)continue;int danger=INF;for(auto e:visible_enemy_stacks_)danger=std::min(danger,dist_[cell_id_[x]][cell_id_[e.first]]);if(danger<=2)continue;
            if(1200-o.turn<2*cost+100||o.my_army-cost<o.opp_army*9/10)continue;
            double au=130-df*12+degree_[x]*12+room_[x]*.25,du=75-dist_[cell_id_[x]][cell_id_[general_]]*2+(articulation_[x]?45:0)+degree_[x]*7;cs.push_back({x,cost,df,au,du,au+du});min_cost=std::min(min_cost,cost);}
        double best=-1e100,ba=0,bd=0;int bx=-1,bc=0,bdf=0;for(auto c:cs)if(c.cost<=min_cost+2&&c.utility>best){best=c.utility;bx=c.x;bc=c.cost;ba=c.au;bd=c.du;bdf=c.df;}
        if(bx<0)return pass();
        ++castles_built_;castle_build_turns_.push_back(o.turn);record_castle(o,bx,bc,min_cost,"second");second_castle_turn_=o.turn;second_castle_cost_=bc;second_castle_attack_utility_=ba;second_castle_defense_utility_=bd;second_castle_distance_to_front_=bdf;enemy_castle_response_pending_=false;return {2,row(bx),col(bx),0,0};
    }

public:
    Agent(int player_id,int h,int w):player_id_(player_id),h_(h),w_(w),n_(h*w){
        const char* seed=std::getenv("JURAJ_RNG_SEED");
        if(seed){char* end=nullptr;unsigned long long v=std::strtoull(seed,&end,10);if(end==seed)v=0;rng_.seed(v);}
        else {std::random_device rd;auto t=std::chrono::high_resolution_clock::now().time_since_epoch().count();std::seed_seq seq{rd(),rd(),static_cast<unsigned>(t),static_cast<unsigned>(t>>32)};rng_.seed(seq);}
    }
