        int rear=0,excess=0,atk=0,def=0;for(int x:id_cell_)if(o.owner[x]==1){if(is_rear_low_value(o,x)){rear+=o.army[x];excess+=std::max(0,o.army[x]-1);}else{int ed=std::min({row(x),h_-1-row(x),col(x),w_-1-col(x)});if(ed<=1&&o.army[x]>=8&&active_affinity_exception(o,x))++active_edge_exemptions_;}if(dist_[cell_id_[x]][cell_id_[attack]]<=5)atk+=o.army[x];if(dist_[cell_id_[x]][cell_id_[defense]]<=3)def+=o.army[x];}
        rear_army_total_=rear;rear_excess_army_=excess;if(enemy_general_>=0&&(affinity_snapshots_.empty()||o.turn-affinity_snapshots_.back().turn>=50))affinity_snapshots_.push_back({o.turn,o.my_army,rear,atk,def});
    }

    int affinity_target()const{return enemy_general_>=0?enemy_general_:(contact_anchor_>=0?contact_anchor_:-1);}
    bool active_affinity_exception(const Observation&o,int x)const{
        int t=affinity_target();if(x==general_||x==front_stack_||x==contact_staging_cell_||known_castle_[x]||articulation_[x])return true;
        if(t>=0&&dist_[cell_id_[x]][cell_id_[t]]<=6)return true;
        for(auto e:visible_enemy_stacks_)if(dist_[cell_id_[x]][cell_id_[e.first]]<=4)return true;
        if(enemy_general_<0&&(strategy_==SEARCH_GENERAL||strategy_==QUALIFIER_PROBE)){int best=static_cast<int>(std::max_element(enemy_score_.begin(),enemy_score_.end())-enemy_score_.begin());if(enemy_score_[best]>0&&dist_[cell_id_[x]][cell_id_[best]]<=5)return true;int unseen=0;for(int d=0;d<4;++d){int y=neighbor(x,d);if(y>=0&&last_seen_[y]<0)++unseen;}if(unseen>=2&&o.owner[x]==1)return true;}
        return general_>=0&&dist_[cell_id_[x]][cell_id_[general_]]<=2;
    }
    double compute_dynamic_affinity(const Observation&o,int x)const{
        double a=static_affinity_[x];int t=affinity_target();
        if(t>=0){int dt=dist_[cell_id_[x]][cell_id_[t]],base=dist_[cell_id_[general_]][cell_id_[t]];double force=enemy_general_>=0?7.0:3.5;a-=dt*force;if(dist_[cell_id_[general_]][cell_id_[x]]+dt<=base+2)a+=enemy_general_>=0?90:42;if(dt<=6)a+=enemy_general_>=0?115:55;if(dt>base+2)a-=enemy_general_>=0?58:32;}
        int enemy_distance=INF;for(int z:id_cell_)if(o.owner[z]==2)enemy_distance=std::min(enemy_distance,dist_[cell_id_[x]][cell_id_[z]]);if(enemy_distance<INF)a+=std::max(0,9-enemy_distance)*7;
        for(auto e:visible_enemy_stacks_){int d=dist_[cell_id_[x]][cell_id_[e.first]];a+=std::max(0,7-d)*(required_defense_>0?8:3);}
        if(x==contact_staging_cell_)a+=110;
        if(x==front_stack_)a+=75;
        if(enemy_general_>=0&&x==enemy_general_)a+=240;
        int ds=t>=0?next_hop_[cell_id_[general_]][cell_id_[t]]:-1;if(ds>=0)a-=dist_[cell_id_[x]][ds]*(required_defense_>0?4.5:1.8);
        if(enemy_general_<0){int best=static_cast<int>(std::max_element(enemy_score_.begin(),enemy_score_.end())-enemy_score_.begin());if(enemy_score_[best]>0)a-=dist_[cell_id_[x]][cell_id_[best]]*(strategy_==SEARCH_GENERAL?4.5:1.5);}
        if(old_staging_cell_>=0&&x==old_staging_cell_&&x!=contact_staging_cell_)a-=25;
        if(dominance_)a+=t>=0?std::max(0,10-dist_[cell_id_[x]][cell_id_[t]])*3:0;
        if(active_affinity_exception(o,x))a+=45;
        return a;
    }
    void rebuild_dynamic_affinity(const Observation&o){
        for(int x:id_cell_)dynamic_affinity_[x]=compute_dynamic_affinity(o,x);
        int rear=*std::min_element(id_cell_.begin(),id_cell_.end(),[&](int a,int b){return static_affinity_[a]<static_affinity_[b];}),enemy=enemy_general_;
        bool event=o.turn%100==0||contact_staging_cell_!=last_field_stage_||enemy!=last_field_enemy_;if(event&&field_traces_.size()<20){field_traces_.push_back({o.turn,rear,old_staging_cell_,contact_staging_cell_,front_stack_,enemy,dynamic_affinity_[rear],old_staging_cell_>=0?dynamic_affinity_[old_staging_cell_]:0,contact_staging_cell_>=0?dynamic_affinity_[contact_staging_cell_]:0,front_stack_>=0?dynamic_affinity_[front_stack_]:0,enemy>=0?dynamic_affinity_[enemy]:0});last_field_stage_=contact_staging_cell_;last_field_enemy_=enemy;}
    }
    double dynamic_affinity(const Observation&,int x)const{return dynamic_affinity_[x];}
    bool is_rear_low_value(const Observation&o,int x)const{
        if(o.owner[x]!=1||o.army[x]<=1||x==general_||known_castle_[x]||articulation_[x]||active_affinity_exception(o,x))return false;
        for(auto e:visible_enemy_stacks_)if(dist_[cell_id_[x]][cell_id_[e.first]]<=5)return false;
        int t=affinity_target();if(t<0)return false;
        int base=dist_[cell_id_[general_]][cell_id_[t]],dt=dist_[cell_id_[x]][cell_id_[t]];
        int ed=std::min({row(x),h_-1-row(x),col(x),w_-1-col(x)}),corner=std::min({row(x)+col(x),row(x)+w_-1-col(x),h_-1-row(x)+col(x),h_-1-row(x)+w_-1-col(x)});
        return dt>base+2&&(ed<=1||corner<=2||degree_[x]==1||terminal_depth_[x]>0);
    }

    void update_hunter_model(const Observation&o){
        double evidence=0;
        if(!visible_enemy_stacks_.empty()){
            auto s=visible_enemy_stacks_.front();int dg=dist_[cell_id_[s.first]][cell_id_[general_]];
            if(hunter_first_stack_cell_<0){hunter_first_stack_cell_=s.first;hunter_first_stack_army_=s.second;hunter_first_stack_distance_=dg;}
            bool dominant=visible_enemy_stacks_.size()==1||s.second>=2*std::max(1,visible_enemy_stacks_[1].second);
            bool adjacent=false,crumb=false,closer=false;
            if(!hunter_stack_history_.empty()){
                auto p=hunter_stack_history_.back();adjacent=dist_[cell_id_[p.cell]][cell_id_[s.first]]==1;closer=dg<p.distance_to_general;
                if(adjacent&&o.owner[p.cell]==2&&o.army[p.cell]<=2){crumb=true;if(std::find(hunter_breadcrumbs_.begin(),hunter_breadcrumbs_.end(),p.cell)==hunter_breadcrumbs_.end())hunter_breadcrumbs_.push_back(p.cell);}
            }
            if(hunter_stack_history_.empty()||hunter_stack_history_.back().cell!=s.first)hunter_stack_history_.push_back({o.turn,s.first,s.second,dg});
            evidence=(s.second>=8?.18:0)+(dominant?.18:0)+(adjacent?.20:0)+(crumb?.38:0)+(closer?.10:0);
            if(crumb&&dominant&&adjacent)hunter_signature_score_=std::max(hunter_signature_score_,.68);
        }
        double observed=std::clamp(evidence,0.0,1.0);hunter_signature_score_=.88*hunter_signature_score_+.12*observed;
        hunter_signature_max_=std::max(hunter_signature_max_,hunter_signature_score_);
        if(hunter_signature_score_>=.55&&hunter_trigger_turn_<0)hunter_trigger_turn_=o.turn;
        if(hunter_trigger_turn_>=0)hunter_signature_score_=std::max(hunter_signature_score_,.58);
