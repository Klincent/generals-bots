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
                    HUNTER_COUNTERATTACK, HUNTER_KILL_ZONE,
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
