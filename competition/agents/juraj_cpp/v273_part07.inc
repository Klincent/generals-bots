        double best=-1;int bx=-1;
        for(int x:id_cell_)if(o.owner[x]==1&&o.type[x]==1){int cost=castle_cost(x,o);if(o.army[x]<cost+12)continue;int danger=INF;for(auto e:visible_enemy_stacks_)danger=std::min(danger,dist_[cell_id_[x]][cell_id_[e.first]]);if(danger<6)continue;double s=(articulation_[x]?40:0)+room_[x]-.7*dist_[cell_id_[general_]][cell_id_[x]]-.5*cost;if(s>best){best=s;bx=x;}}
        if(bx>=0&&best>0){++castles_built_;castle_build_turns_.push_back(o.turn);return {2,row(bx),col(bx),0,0};}return pass();
    }
    Action maybe_contact_castle(const Observation&o){
        if(!contact_established_||contact_anchor_<0||contact_castle_built_||hunter_trigger_turn_>=0||castles_built_>=2)return pass();
        if(severe_land_deficit_&&castles_built_>=1)return pass();
        for(int x:id_cell_)if(known_castle_[x]&&o.owner[x]==1){int d=dist_[cell_id_[x]][cell_id_[contact_anchor_]];if(d>=2&&d<=4){contact_castle_built_=true;contact_staging_cell_=x;return pass();}}
        if(o.turn-first_contact_turn_<4)return pass();
        double best=-1e100;int bx=-1,bc=0,bd=0;
        for(int x:id_cell_)if(o.owner[x]==1&&o.type[x]==1){int d=dist_[cell_id_[x]][cell_id_[contact_anchor_]];if(d<2||d>4)continue;int cost=castle_cost(x,o);if(o.army[x]<cost+8)continue;int danger=INF;for(auto e:visible_enemy_stacks_)danger=std::min(danger,dist_[cell_id_[x]][cell_id_[e.first]]);if(danger<=2)continue;double s=degree_[x]*24+room_[x]+(articulation_[x]?70:0)-d*8;if(s>best){best=s;bx=x;bc=cost;bd=d;}}
        if(bx<0)return pass();
        bool second=castles_built_==1;contact_castle_built_=true;contact_staging_cell_=bx;contact_castle_turn_=o.turn;++contact_castles_built_;++castles_built_;castle_build_turns_.push_back(o.turn);if(second){second_castle_turn_=o.turn;second_castle_cost_=bc;second_castle_attack_utility_=best;second_castle_defense_utility_=degree_[bx]*10+(articulation_[bx]?35:0);second_castle_distance_to_front_=bd;}return {2,row(bx),col(bx),0,0};
    }
    Action maybe_second_castle(const Observation&o){
        if(!contact_established_||castles_built_!=1||hunter_trigger_turn_>=0||o.turn>900)return pass();
        if(land_behind_)return pass();
        int front=enemy_general_>=0?enemy_general_:contact_anchor_;if(front<0)return pass();
        bool first_far=true;for(int x:id_cell_)if(known_castle_[x]&&o.owner[x]==1&&dist_[cell_id_[x]][cell_id_[front]]<=6)first_far=false;
        if(!enemy_castle_response_pending_&&!strong_dominance_&&!(dominance_&&first_far))return pass();
        double best=-1e100,ba=0,bd=0;int bx=-1,bc=0,bdf=0,axis=dist_[cell_id_[general_]][cell_id_[front]];
        for(int x:id_cell_)if(o.owner[x]==1&&o.type[x]==1){int df=dist_[cell_id_[x]][cell_id_[front]];if(df<2||df>6)continue;if(dist_[cell_id_[general_]][cell_id_[x]]+df>axis+3)continue;int cost=castle_cost(x,o);if(o.army[x]<cost+10)continue;int danger=INF;for(auto e:visible_enemy_stacks_)danger=std::min(danger,dist_[cell_id_[x]][cell_id_[e.first]]);if(danger<=2)continue;
            double au=130-df*12+degree_[x]*12+room_[x]*.25,du=75-dist_[cell_id_[x]][cell_id_[general_]]*2+(articulation_[x]?45:0)+degree_[x]*7,score=au+du-cost*1.35;if(score>best){best=score;bx=x;bc=cost;ba=au;bd=du;bdf=df;}}
        if(bx<0)return pass();
        ++castles_built_;castle_build_turns_.push_back(o.turn);second_castle_turn_=o.turn;second_castle_cost_=bc;second_castle_attack_utility_=ba;second_castle_defense_utility_=bd;second_castle_distance_to_front_=bdf;enemy_castle_response_pending_=false;return {2,row(bx),col(bx),0,0};
    }

public:
    Agent(int player_id,int h,int w):player_id_(player_id),h_(h),w_(w),n_(h*w){
        const char* seed=std::getenv("JURAJ_RNG_SEED");
        if(seed){char* end=nullptr;unsigned long long v=std::strtoull(seed,&end,10);if(end==seed)v=0;rng_.seed(v);}
        else {std::random_device rd;auto t=std::chrono::high_resolution_clock::now().time_since_epoch().count();std::seed_seq seq{rd(),rd(),static_cast<unsigned>(t),static_cast<unsigned>(t>>32)};rng_.seed(seq);}
    }
    Action act(const Observation& o) {
        auto begin=Clock::now();
        auto hard=o.turn==0 ? process_start_+std::chrono::milliseconds(8500)
                            : begin+std::chrono::milliseconds(120);
        if (o.turn==0) initialise(o);
        update_memory(o);
        intentional_hold_=false;
        if(enemy_general_<0&&turns_since_search_progress_>=3)++exploration_tempo_boost_turns_;
        bool production_valid=false;Action production_fallback=find_safe_neutral_capture(o,production_valid);
        pending_affinity_source_=pending_affinity_dest_=pending_affinity_sink_=-1;
        pending_rear_source_=pending_rear_dest_=-1;
        pending_frontier_feed_source_=pending_frontier_feed_dest_=-1;
        Action fallback=pass(), result=fallback; bool tactical=false;
        result=immediate_tactics(o,tactical);
        if(!tactical)result=hunter_counterattack(o,tactical);
        if(!tactical)result=defense_emergency(o,tactical);
        if(!tactical)result=high_confidence_capture(o,tactical);
        bool deadline_guard=false,legality_guard=false,strategic_empty=false;
        if(!tactical&&Clock::now()<hard-std::chrono::milliseconds(5)){
            Action build=maybe_contact_castle(o);if(build.kind!=2)build=maybe_second_castle(o);if(build.kind!=2)build=maybe_build(o);result=build.kind==2?build:choose_strategic(o);
        }else if(!tactical)deadline_guard=true;
        strategic_empty=result.kind==1&&!intentional_hold_;bool used_productive_fallback=false;
