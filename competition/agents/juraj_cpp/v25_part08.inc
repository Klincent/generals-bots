            if(s<=-1e90)continue;
            int strategic_target=enemy_general_>=0?enemy_general_:static_cast<int>(std::max_element(enemy_score_.begin(),enemy_score_.end())-enemy_score_.begin());
            bool pressure=o.owner[y]==2||(strategic_target>=0&&enemy_score_[strategic_target]>0&&
                dist_[cell_id_[y]][cell_id_[strategic_target]]<dist_[cell_id_[x]][cell_id_[strategic_target]]);
            Choice& bucket=pressure?offense:economy;
            if(s>bucket.score){bucket={s,move(x,y,split),true};}
        }
        // Interior forces are feeders: when no good frontier action exists, route
        // the most efficient one toward the main stack or its attack path.
        bool stop_feeding=enemy_general_>=0&&overconcentrated(o)&&dist_[cell_id_[main_stack_]][cell_id_[enemy_general_]]>5;
        if(main_stack_>=0&&!stop_feeding)for(int x:id_cell_)if(x!=main_stack_&&legal_source(o,x)&&o.owner[x]==1){int hop=next_hop_[cell_id_[x]][cell_id_[main_stack_]];if(hop>=0){int y=id_cell_[hop];double s=o.army[x]*7.0-dist_[cell_id_[x]][cell_id_[main_stack_]]*5+source_value(o,x)*.1;if(s>economy.score)economy={s,move(x,y,source_value(o,x)>60&&o.army[x]>=6),true};}}
        int feed_target=contact_staging_cell_>=0?contact_staging_cell_:front_stack_;
        if(contact_established_&&feed_target>=0)for(int x:id_cell_)if(x!=feed_target&&x!=front_stack_&&legal_source(o,x)){int hop=next_hop_[cell_id_[x]][cell_id_[feed_target]];if(hop>=0){int y=id_cell_[hop];double s=o.army[x]*6.0-dist_[cell_id_[x]][cell_id_[feed_target]]*9+(dominance_?180:80);if(s>economy.score)economy={s,move(x,y,0),true};}}
        if(enemy_general_>=0&&(main_stack_idle_turns_>=2||overconcentrated(o))&&economy.valid){double factor=until_tick<=8?.65:.48;economy.score*=factor;}
        if(contact_established_&&contact_idle_turns_>=5&&economy.valid){int x=cell(economy.action.row,economy.action.col),y=neighbor(x,economy.action.dir);if(y>=0&&dist_[cell_id_[y]][cell_id_[contact_anchor_]]>8)economy.valid=false;}
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
            }
            if(x==main_stack_||o.army[x]>=std::max(20,o.my_army/10)){recent_significant_edges_.push_back({x,y});if(recent_significant_edges_.size()>8)recent_significant_edges_.erase(recent_significant_edges_.begin());}
        }
        if(enemy_general_>=0){if(progress){main_stack_idle_turns_=0;++main_stack_progress_moves_;}else{++main_stack_idle_turns_;if(over)++overconcentrated_idle_turns_;}main_stack_idle_max_=std::max(main_stack_idle_max_,main_stack_idle_turns_);}
    }
    void update_contact_metrics(const Observation&o,const Action&a,bool forced_defense){
        if(!contact_established_)return;
        std::string cls="OTHER";bool progress=false;
        if(forced_defense){cls="DEFENSE";}
        else if(a.kind==2&&o.turn==contact_castle_turn_){cls="FRONT_CASTLE";progress=true;}
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
    }

    Action maybe_build(const Observation& o) {
        // Strategic break-even exceeds raw 70 turns: require 180 useful turns,
        // ample post-build garrison, distance from structures, and a chokepoint
        // or high-room logistics site. Never build near deathtouch/truncation.
        if(castles_built_>=1||enemy_general_>=0||o.turn<120||o.turn>620||1200-o.turn<180||mode_[ATTACK]>.30)return pass();
        double best=-1;int bx=-1;
        for(int x:id_cell_)if(o.owner[x]==1&&o.type[x]==1){int cost=castle_cost(x,o);if(o.army[x]<cost+12)continue;int danger=INF;for(auto e:visible_enemy_stacks_)danger=std::min(danger,dist_[cell_id_[x]][cell_id_[e.first]]);if(danger<6)continue;double s=(articulation_[x]?40:0)+room_[x]-.7*dist_[cell_id_[general_]][cell_id_[x]]-.5*cost;if(s>best){best=s;bx=x;}}
        if(bx>=0&&best>0){++castles_built_;castle_build_turns_.push_back(o.turn);return {2,row(bx),col(bx),0,0};}return pass();
    }
    Action maybe_contact_castle(const Observation&o){
        if(!contact_established_||contact_anchor_<0||contact_castle_built_||hunter_trigger_turn_>=0||castles_built_>=2)return pass();
        for(int x:id_cell_)if(known_castle_[x]&&o.owner[x]==1){int d=dist_[cell_id_[x]][cell_id_[contact_anchor_]];if(d>=2&&d<=4){contact_castle_built_=true;contact_staging_cell_=x;return pass();}}
        if(o.turn-first_contact_turn_<4)return pass();
        double best=-1e100;int bx=-1;
        for(int x:id_cell_)if(o.owner[x]==1&&o.type[x]==1){int d=dist_[cell_id_[x]][cell_id_[contact_anchor_]];if(d<2||d>4)continue;int cost=castle_cost(x,o);if(o.army[x]<cost+8)continue;int danger=INF;for(auto e:visible_enemy_stacks_)danger=std::min(danger,dist_[cell_id_[x]][cell_id_[e.first]]);if(danger<=2)continue;double s=degree_[x]*24+room_[x]+(articulation_[x]?70:0)-d*8;if(s>best){best=s;bx=x;}}
        if(bx<0)return pass();
        contact_castle_built_=true;contact_staging_cell_=bx;contact_castle_turn_=o.turn;++contact_castles_built_;++castles_built_;castle_build_turns_.push_back(o.turn);return {2,row(bx),col(bx),0,0};
    }

public:
    Agent(int player_id,int h,int w):player_id_(player_id),h_(h),w_(w),n_(h*w){
