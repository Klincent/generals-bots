#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <functional>
#include <limits>
#include <numeric>
#include <queue>
#include <random>
#include <string>
#include <tuple>
#include <utility>
#include <vector>

using Clock = std::chrono::steady_clock;

struct Observation {
    int turn = 0, my_land = 0, my_army = 0, opp_land = 0, opp_army = 0;
    std::vector<int> type, owner, army;
};

struct Action {
    int kind = 1, row = 0, col = 0, dir = 0, split = 0;
};

class Agent {
    static constexpr int INF = 1000000;
    static constexpr std::array<int, 4> DR{{-1, 1, 0, 0}};
    static constexpr std::array<int, 4> DC{{0, 0, -1, 1}};
    enum Mode { EXPANSION, ECONOMY, CONSOLIDATION, ATTACK, DEFENSE, SCOUTING, DEATHTOUCH, MODE_COUNT };
    enum Strategy { OPENING, EXPAND, SEARCH_GENERAL, CONTACT, GENERAL_KNOWN_PREPARE,
                    GENERAL_KNOWN_ATTACK, DEATHTOUCH_PREPARE, DEATHTOUCH_ATTACK, FORTRESS_DRAW,
                    QUALIFIER_PROBE, QUALIFIER_FEINT, QUALIFIER_EXPLOIT, MULTI_FRONT_PRESSURE,
                    GENERAL_CONTAINMENT, DEATHTOUCH_FORK, GENERAL_DEFENSE_ALERT,
                    STRATEGY_COUNT };

    int player_id_, h_, w_, n_, turn_ = 0, general_ = -1, enemy_general_ = -1;
    int castles_built_ = 0, enemy_castle_events_ = 0, found_enemy_turn_ = -1;
    Clock::time_point process_start_ = Clock::now();
    std::vector<char> passable_, articulation_, known_castle_, possible_enemy_castle_;
    std::vector<int> cell_id_, id_cell_, degree_, component_, room_, last_owner_, last_army_, last_seen_;
    std::vector<int> castle_first_, castle_owner_, enemy_score_;
    std::vector<std::vector<int>> dist_, next_hop_;
    std::vector<std::array<int, 5>> observation_history_;
    std::vector<Observation> full_observation_history_;
    std::vector<int> my_land_hist_, my_army_hist_, opp_land_hist_, opp_army_hist_;
    std::vector<std::pair<int, int>> visible_enemy_stacks_, important_enemy_stacks_;
    std::array<double, MODE_COUNT> mode_{{.35, .08, .12, .12, .08, .20, .05}};
    std::vector<double> decision_ms_;
    int land50_ = -1;
    int expected_opp_production_ = 0, known_opp_combat_losses_ = 0;
    int opponent_unexplained_delta_ = 0, suspected_enemy_builds_ = 0;
    Strategy strategy_ = OPENING;
    int main_stack_ = -1, defense_lower_ = 0, defense_expected_ = 0, defense_upper_ = 0;
    int opp_land50_ = -1, my_army50_ = -1, opp_army50_ = -1;
    std::array<int,4> approach_turn_{{-1,-1,-1,-1}};
    std::vector<int> castle_build_turns_;
    std::mt19937_64 rng_;
    std::uniform_real_distribution<double> unit_{0.0, 1.0};
    unsigned long long strategic_flip_opportunities_ = 0, strategic_flips_taken_ = 0;
    unsigned long long split_flip_opportunities_ = 0, split_flips_taken_ = 0;
    unsigned long long movement_decisions_ = 0, all_moves_ = 0, half_moves_ = 0;
    std::array<unsigned long long,STRATEGY_COUNT> half_by_mode_{};
    unsigned long long half_from_general_ = 0, half_from_castle_ = 0;
    unsigned long long half_from_choke_ = 0, half_from_main_ = 0, half_from_feeder_ = 0;
    struct StackSighting { int turn, cell, army, distance_to_general; };
    struct Probe { int turn, cell, army, land_delta, army_delta, defender, defender_army, defender_dir; };
    std::vector<StackSighting> largest_enemy_history_;
    std::vector<Probe> probe_history_;
    double qualifier_defense_score_ = .18;
    int required_defense_ = 0, defense_alert_turns_ = 0, meta_turns_ = 0;
    int feint_actions_ = 0, intercept_actions_ = 0, fork_actions_ = 0;

    bool flip10() { return unit_(rng_) < 0.10; }

    bool inside(int r, int c) const { return r >= 0 && r < h_ && c >= 0 && c < w_; }
    int cell(int r, int c) const { return r * w_ + c; }
    int row(int x) const { return x / w_; }
    int col(int x) const { return x % w_; }
    int neighbor(int x, int d) const {
        int r = row(x) + DR[d], c = col(x) + DC[d];
        return inside(r, c) ? cell(r, c) : -1;
    }
    int direction(int a, int b) const {
        for (int d = 0; d < 4; ++d) if (neighbor(a, d) == b) return d;
        return 0;
    }

    void initialise(const Observation& o) {
        passable_.assign(n_, false);
        cell_id_.assign(n_, -1);
        degree_.assign(n_, 0); component_.assign(n_, -1); room_.assign(n_, 0);
        articulation_.assign(n_, false); known_castle_.assign(n_, false);
        possible_enemy_castle_.assign(n_, false); castle_first_.assign(n_, -1);
        castle_owner_.assign(n_, 0); last_owner_.assign(n_, 0); last_army_.assign(n_, 0);
        last_seen_.assign(n_, -1); enemy_score_.assign(n_, 0);

        // At turn zero competition mode has no castles.  Both visible mountains
        // (2) and structures in fog (5) are therefore original mountains.
        for (int x = 0; x < n_; ++x) {
            passable_[x] = o.type[x] != 2 && o.type[x] != 5;
            if (passable_[x]) { cell_id_[x] = static_cast<int>(id_cell_.size()); id_cell_.push_back(x); }
            if (o.type[x] == 4 && o.owner[x] == 1) general_ = x;
        }
        const int p = static_cast<int>(id_cell_.size());
        std::vector<std::vector<int>> adj(p);
        for (int x : id_cell_) for (int d = 0; d < 4; ++d) {
            int y = neighbor(x, d); if (y >= 0 && passable_[y]) adj[cell_id_[x]].push_back(cell_id_[y]);
        }
        for (int x : id_cell_) degree_[x] = static_cast<int>(adj[cell_id_[x]].size());

        // Connected components and all-pairs BFS distances/first hops.  With at
        // most 441 cells this is useful real work yet remains far below 8.5 s.
        int cc = 0;
        for (int start : id_cell_) if (component_[start] < 0) {
            std::queue<int> q; q.push(start); component_[start] = cc;
            while (!q.empty()) { int x=q.front(); q.pop(); for(int d=0;d<4;++d){int y=neighbor(x,d);if(y>=0&&passable_[y]&&component_[y]<0){component_[y]=cc;q.push(y);}} }
            ++cc;
        }
        dist_.assign(p, std::vector<int>(p, INF)); next_hop_.assign(p, std::vector<int>(p, -1));
        for (int si = 0; si < p; ++si) {
            std::queue<int> q; q.push(si); dist_[si][si] = 0;
            while (!q.empty()) {
                int u=q.front(); q.pop();
                for (int v : adj[u]) if (dist_[si][v] == INF) {
                    dist_[si][v] = dist_[si][u] + 1;
                    next_hop_[si][v] = (u == si ? v : next_hop_[si][u]); q.push(v);
                }
            }
        }
        // Radius-seven local room scores, matching the spawn generator metric.
        for (int x : id_cell_) for (int y : id_cell_)
            if (dist_[cell_id_[x]][cell_id_[y]] <= 7 && x != y) ++room_[x];

        // Tarjan articulation points identify genuine graph chokepoints.
        std::vector<int> disc(p, -1), low(p), parent(p, -1); int timer = 0;
        std::function<void(int)> dfs = [&](int u) {
            disc[u]=low[u]=timer++; int children=0;
            for(int v:adj[u]) if(disc[v]<0){parent[v]=u;++children;dfs(v);low[u]=std::min(low[u],low[v]);if(parent[u]<0&&children>1)articulation_[id_cell_[u]]=true;if(parent[u]>=0&&low[v]>=disc[u])articulation_[id_cell_[u]]=true;}else if(v!=parent[u])low[u]=std::min(low[u],disc[v]);
        };
        for (int i=0;i<p;++i) if(disc[i]<0) dfs(i);

        // Official placement: walking distance >=17 and radius-seven room gap
        // <=5. Uniform sampling inside that fair set means no sharper claim is valid.
        if (general_ >= 0) {
            for (int x : id_cell_) {
                int d = dist_[cell_id_[general_]][cell_id_[x]];
                if (d >= 17 && std::abs(room_[x] - room_[general_]) <= 5)
                    enemy_score_[x] = 1000 + 10*d + room_[x];
            }
            if (*std::max_element(enemy_score_.begin(), enemy_score_.end()) == 0)
                for (int x:id_cell_) if(dist_[cell_id_[general_]][cell_id_[x]]>=17) enemy_score_[x]=500;
        }
    }

    bool visible_type(int t) const { return t == 1 || t == 2 || t == 3 || t == 4; }
    void update_memory(const Observation& o) {
        turn_ = o.turn; visible_enemy_stacks_.clear();
        observation_history_.push_back({o.turn,o.my_land,o.my_army,o.opp_land,o.opp_army});
        full_observation_history_.push_back(o);
        if (!opp_army_hist_.empty()) {
            int expected = 0;
            if (o.turn % 50 == 0) expected += opp_land_hist_.back();
            if (o.turn % 2 == 0) {
                expected += 1;  // the enemy general
                expected += static_cast<int>(std::count(castle_owner_.begin(), castle_owner_.end(), 2));
            }
            expected_opp_production_ += expected;
            int known_loss = 0;
            for (int x : id_cell_) {
                if (last_seen_[x] == o.turn - 1 && last_owner_[x] == 2 &&
                    visible_type(o.type[x]) && o.owner[x] == 2 && o.army[x] < last_army_[x])
                    known_loss += last_army_[x] - o.army[x];
            }
            known_opp_combat_losses_ += known_loss;
            opponent_unexplained_delta_ = o.opp_army - opp_army_hist_.back() - expected + known_loss;
            // A build costs at least 35.  Treat a matching unexplained drop as
            // evidence, not certainty: fogged combat or movement can confound it.
            if (opponent_unexplained_delta_ <= -35) ++suspected_enemy_builds_;
        }
        my_land_hist_.push_back(o.my_land); my_army_hist_.push_back(o.my_army);
        opp_land_hist_.push_back(o.opp_land); opp_army_hist_.push_back(o.opp_army);
        if (o.turn == 50) { land50_ = o.my_land; opp_land50_=o.opp_land; my_army50_=o.my_army; opp_army50_=o.opp_army; }
        for (int x=0;x<n_;++x) {
            bool visible = visible_type(o.type[x]);
            // A structure-in-fog on initially passable ground can only be a built castle.
            if (o.type[x] == 5 && passable_[x]) {
                if (!known_castle_[x]) { known_castle_[x]=true; castle_first_[x]=o.turn; }
                possible_enemy_castle_[x] = last_owner_[x] != 1; castle_owner_[x] = possible_enemy_castle_[x] ? 2 : 1;
            }
            if (o.type[x] == 3) {
                if (!known_castle_[x]) { known_castle_[x]=true; castle_first_[x]=o.turn; if(o.owner[x]==2)++enemy_castle_events_; }
                castle_owner_[x] = o.owner[x]; possible_enemy_castle_[x] = o.owner[x] == 2;
            }
            if (visible) {
                last_owner_[x]=o.owner[x]; last_army_[x]=o.army[x]; last_seen_[x]=o.turn;
                if (o.type[x] == 4 && o.owner[x] == 1) general_=x;
                if (o.type[x] == 4 && o.owner[x] == 2) { enemy_general_=x; if(found_enemy_turn_<0)found_enemy_turn_=o.turn; }
                if (o.owner[x] != 2 || o.type[x] != 4) enemy_score_[x]=0;
                if (o.owner[x]==2) visible_enemy_stacks_.push_back({x,o.army[x]});
            }
        }
        std::sort(visible_enemy_stacks_.begin(), visible_enemy_stacks_.end(), [](auto a,auto b){return a.second>b.second;});
        for (auto s:visible_enemy_stacks_) if(s.second>=4) {
            auto it=std::find_if(important_enemy_stacks_.begin(),important_enemy_stacks_.end(),[&](auto z){return z.first==s.first;});
            if(it==important_enemy_stacks_.end())important_enemy_stacks_.push_back(s);else it->second=s.second;
        }
        update_enemy_scores(o); update_modes(o); update_qualifier_model(o);
        update_strategy(o);
    }

    void update_strategy(const Observation& o) {
        main_stack_=-1;
        double best=-1e100;
        int target=enemy_general_;
        if(target<0&&!enemy_score_.empty()) target=static_cast<int>(std::max_element(enemy_score_.begin(),enemy_score_.end())-enemy_score_.begin());
        for(int x:id_cell_) if(o.owner[x]==1&&o.army[x]>1) {
            int d=(target>=0?dist_[cell_id_[x]][cell_id_[target]]:0);
            double utility=o.army[x]*8.0-degree_[x]*.3-d*1.5+(known_castle_[x]?5:0);
            if(utility>best){best=utility;main_stack_=x;}
        }
        if(o.turn<55) strategy_=OPENING;
        else if(enemy_general_>=0) {
            int d=main_stack_>=0?dist_[cell_id_[main_stack_]][cell_id_[enemy_general_]]:INF;
            int seen=(last_seen_[enemy_general_]>=0?last_army_[enemy_general_]:1);
            int hidden=std::max(0,o.opp_army-seen);
            defense_lower_=seen; defense_expected_=seen+hidden/std::max(3,d+2); defense_upper_=seen+hidden;
            int arrival=main_stack_>=0?std::max(0,o.army[main_stack_]-1):0;
            bool confident=arrival>defense_expected_+std::max(3,d/2)||o.turn>=740;
            int adjacent=0;for(int d2=0;d2<4;++d2){int z=neighbor(enemy_general_,d2);if(z>=0&&o.owner[z]==1&&o.army[z]>1)++adjacent;}
            if(o.turn>=800&&adjacent>=2)strategy_=DEATHTOUCH_FORK;
            else if(o.turn>=800)strategy_=DEATHTOUCH_ATTACK;
            else if(!confident&&qualifier_defense_score_>.48)strategy_=GENERAL_CONTAINMENT;
            else strategy_=o.turn>=700?DEATHTOUCH_PREPARE:(confident?GENERAL_KNOWN_ATTACK:GENERAL_KNOWN_PREPARE);
            if(main_stack_>=0) for(int i=0;i<4;++i) if(approach_turn_[i]<0&&d<=std::array<int,4>{{10,5,2,1}}[i]) approach_turn_[i]=o.turn;
        } else if(!visible_enemy_stacks_.empty()) strategy_=CONTACT;
        else strategy_=o.turn<300?EXPAND:(o.turn>=700?DEATHTOUCH_PREPARE:SEARCH_GENERAL);
        if(required_defense_>0){strategy_=GENERAL_DEFENSE_ALERT;++defense_alert_turns_;return;}
        if(enemy_general_<0&&qualifier_defense_score_>.58)strategy_=QUALIFIER_EXPLOIT;
        else if(main_stack_>=0&&qualifier_defense_score_>.48&&strategy_==CONTACT)strategy_=QUALIFIER_FEINT;
        else if(main_stack_>=0&&qualifier_defense_score_>.32&&strategy_==SEARCH_GENERAL)strategy_=QUALIFIER_PROBE;
        if(strategy_>=QUALIFIER_PROBE&&strategy_<=DEATHTOUCH_FORK)++meta_turns_;
    }

    void update_qualifier_model(const Observation& o) {
        required_defense_=0; double evidence=0;
        if(!visible_enemy_stacks_.empty()){
            auto s=visible_enemy_stacks_.front();int dg=general_>=0?dist_[cell_id_[s.first]][cell_id_[general_]]:INF;
            largest_enemy_history_.push_back({o.turn,s.first,s.second,dg});
            if(largest_enemy_history_.size()>12)largest_enemy_history_.erase(largest_enemy_history_.begin());
            if(dg<=8){required_defense_=s.second+std::max(3,(8-dg)/2)+4;evidence+=.28;}
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

    Action immediate_tactics(const Observation& o, bool& found) {
        found=true;
        // Any ordinary capture of a revealed general, or any legal post-800 touch.
        if(enemy_general_>=0) for(int d=0;d<4;++d){int x=neighbor(enemy_general_,d);if(!legal_source(o,x))continue;int m=o.army[x]-1;if(o.turn>=800||m>o.army[enemy_general_])return move(x,enemy_general_);}

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
        Choice offense,economy;
        int next_tick=((o.turn/50)+1)*50, until_tick=next_tick-o.turn;
        int candidate_peak=*std::max_element(enemy_score_.begin(),enemy_score_.end());
        for(int x:id_cell_) if(legal_source(o,x)) for(int d=0;d<4;++d) {
            int y=neighbor(x,d); if(y<0||!passable_[y])continue;
            double all=score_variant(o,x,y,0,until_tick,candidate_peak), half=score_variant(o,x,y,1,until_tick,candidate_peak);
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
        }
        // Interior forces are feeders: when no good frontier action exists, route
        // the most efficient one toward the main stack or its attack path.
        if(main_stack_>=0)for(int x:id_cell_)if(x!=main_stack_&&legal_source(o,x)&&o.owner[x]==1){int hop=next_hop_[cell_id_[x]][cell_id_[main_stack_]];if(hop>=0){int y=id_cell_[hop];double s=o.army[x]*7.0-dist_[cell_id_[x]][cell_id_[main_stack_]]*5+source_value(o,x)*.1;if(s>economy.score)economy={s,move(x,y,source_value(o,x)>60&&o.army[x]>=6),true};}}
        if(!offense.valid)return economy.valid?economy.action:pass();
        if(!economy.valid)return offense.action;
        bool prefer_offense=offense.score>economy.score;
        ++strategic_flip_opportunities_; if(flip10()){prefer_offense=!prefer_offense;++strategic_flips_taken_;}
        Action chosen=prefer_offense?offense.action:economy.action;
        if(strategy_==QUALIFIER_FEINT)++feint_actions_;
        if(strategy_==DEATHTOUCH_FORK||(chosen.kind==0&&chosen.split&&cell(chosen.row,chosen.col)==main_stack_&&qualifier_defense_score_>.48))++fork_actions_;
        return chosen;
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
        Action fallback=pass(), result=fallback; bool tactical=false;
        result=immediate_tactics(o,tactical);
        if(!tactical)result=defense_emergency(o,tactical);
        if(!tactical)result=high_confidence_capture(o,tactical);
        if(!tactical&&Clock::now()<hard-std::chrono::milliseconds(5)){
            Action build=maybe_build(o); result=build.kind==2?build:choose_strategic(o);
        }
        // Final legality guard always leaves time for a protocol-safe pass.
        if(result.kind==0){int x=cell(result.row,result.col),y=neighbor(x,result.dir);if(!inside(result.row,result.col)||y<0||!passable_[y]||o.owner[x]!=1||o.army[x]<=1)result=fallback;}
        if(result.kind==0){++movement_decisions_;if(result.split){++half_moves_;++half_by_mode_[strategy_];int x=cell(result.row,result.col);if(x==general_)++half_from_general_;if(known_castle_[x])++half_from_castle_;if(articulation_[x])++half_from_choke_;if(x==main_stack_)++half_from_main_;else ++half_from_feeder_;}else ++all_moves_;}
        auto end=Clock::now();decision_ms_.push_back(std::chrono::duration<double,std::milli>(end-begin).count());return result;
    }
    void report() const {
        if (decision_ms_.empty()) return;
        std::vector<double> t=decision_ms_;std::sort(t.begin(),t.end());double mean=std::accumulate(t.begin(),t.end(),0.0)/t.size();auto pct=[&](double p){return t[std::min(t.size()-1,static_cast<size_t>(std::ceil(p*t.size())-1))];};
        double sf=strategic_flip_opportunities_?100.0*strategic_flips_taken_/strategic_flip_opportunities_:0, pf=split_flip_opportunities_?100.0*split_flips_taken_/split_flip_opportunities_:0, hp=movement_decisions_?100.0*half_moves_/movement_decisions_:0;
        std::fprintf(stderr,"[juraj_metrics] player=%d turns=%zu land50=%d opp_land50=%d army50=%d opp_army50=%d enemy_general_found=%d found_turn=%d approach10=%d approach5=%d approach2=%d approach1=%d castles_built=%d moves=%llu all=%llu half=%llu half_pct=%.3f strategic_flip_opportunities=%llu strategic_flips=%llu strategic_flip_pct=%.3f split_flip_opportunities=%llu split_flips=%llu split_flip_pct=%.3f half_general=%llu half_castle=%llu half_choke=%llu half_main=%llu half_feeder=%llu qualifier_score=%.3f meta_turns=%d defense_alert_turns=%d feints=%d intercepts=%d forks=%d probes=%zu mean_ms=%.4f p95_ms=%.4f p99_ms=%.4f max_ms=%.4f\n",player_id_,decision_ms_.size(),land50_,opp_land50_,my_army50_,opp_army50_,enemy_general_>=0,found_enemy_turn_,approach_turn_[0],approach_turn_[1],approach_turn_[2],approach_turn_[3],castles_built_,movement_decisions_,all_moves_,half_moves_,hp,strategic_flip_opportunities_,strategic_flips_taken_,sf,split_flip_opportunities_,split_flips_taken_,pf,half_from_general_,half_from_castle_,half_from_choke_,half_from_main_,half_from_feeder_,qualifier_defense_score_,meta_turns_,defense_alert_turns_,feint_actions_,intercept_actions_,fork_actions_,probe_history_.size(),mean,pct(.95),pct(.99),t.back());
    }
};

constexpr std::array<int,4> Agent::DR;
constexpr std::array<int,4> Agent::DC;

static bool read_grid(std::vector<int>& g) { for(int&x:g)if(std::scanf("%d",&x)!=1)return false;return true; }

int main() {
    int player,h,w;if(std::scanf("%d %d %d",&player,&h,&w)!=3)return 0;Agent agent(player,h,w);Observation o;o.type.resize(h*w);o.owner.resize(h*w);o.army.resize(h*w);
    while(std::scanf("%d %d %d %d %d",&o.turn,&o.my_land,&o.my_army,&o.opp_land,&o.opp_army)==5){if(!read_grid(o.type)||!read_grid(o.owner)||!read_grid(o.army))break;Action a=agent.act(o);std::printf("%d %d %d %d %d\n",a.kind,a.row,a.col,a.dir,a.split);std::fflush(stdout);}agent.report();return 0;
}
