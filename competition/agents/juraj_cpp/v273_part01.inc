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
    int hard_defense_alerts_ = 0, watch_zone_sightings_ = 0;
    int watch_zone_alerts_ = 0, watch_zone_ignored_ = 0;
    int main_stack_idle_turns_ = 0, main_stack_idle_max_ = 0;
    int main_stack_progress_moves_ = 0, overconcentrated_turns_ = 0;
    int overconcentrated_idle_turns_ = 0, max_main_stack_army_ = 0;
    double max_main_stack_fraction_pct_ = 0;
    unsigned long long reverse_candidates_rejected_ = 0, two_cycle_detections_ = 0;
    unsigned long long short_cycle_detections_ = 0, dead_end_escape_moves_ = 0;
    unsigned long long repeated_cell_penalties_ = 0;
    int max_main_stack_recent_revisits_ = 0;
    std::vector<std::pair<int,int>> recent_significant_edges_;
    std::vector<int> recent_main_stack_positions_;
    int trace_discovery_turn_ = -1, trace_main_army_ = 0, trace_main_distance_ = -1;
    std::vector<int> discovery_main_path_;
    struct HunterSighting { int turn, cell, army, distance_to_general; };
    std::vector<HunterSighting> hunter_stack_history_;
    std::vector<int> hunter_breadcrumbs_, hunter_raider_path_;
    double hunter_signature_score_ = 0, hunter_signature_max_ = 0;
    int hunter_trigger_turn_ = -1, hunter_mode_turns_ = 0, hunter_raider_ = -1;
    int hunter_raider_selected_turn_ = -1, hunter_raider_selected_army_ = 0;
    int hunter_raider_progress_moves_ = 0, hunter_breadcrumb_moves_ = 0;
    int hunter_kill_zone_holds_ = 0, hunter_convoy_kills_ = 0;
    int hunter_gate_castles_ = 0, hunter_gate_disconnects_ = 0;
    int hunter_general_found_turn_ = -1, hunter_general_kill_attempts_ = 0;
    int hunter_first_stack_cell_ = -1, hunter_first_stack_army_ = 0, hunter_first_stack_distance_ = -1;
    bool contact_established_ = false, contact_castle_built_ = false;
    int first_contact_turn_ = -1, contact_anchor_ = -1, contact_staging_cell_ = -1, front_stack_ = -1;
    int contact_pressure_turns_ = 0, contact_idle_turns_ = 0, contact_idle_max_ = 0;
    int front_stack_moves_ = 0, remote_relocation_moves_ = 0, contact_castle_turn_ = -1;
    int contact_castles_built_ = 0, front_feeder_moves_ = 0, enemy_frontier_captures_ = 0;
    int dominance_mode_turns_ = 0, strong_dominance_turns_ = 0, max_largest_contact_distance_ = 0;
    bool dominance_ = false, strong_dominance_ = false;
    std::vector<int> front_stack_path_, contact_anchor_history_;
    std::vector<std::string> contact_action_trace_;
    std::vector<double> static_affinity_, dynamic_affinity_;
    std::vector<int> terminal_depth_;
    bool enemy_castle_response_pending_ = false;
    int enemy_castle_response_triggers_ = 0, second_castle_turn_ = -1, second_castle_cost_ = 0;
    double second_castle_attack_utility_ = 0, second_castle_defense_utility_ = 0;
    int second_castle_distance_to_front_ = -1;
    long long rear_army_total_ = 0, rear_excess_army_ = 0, rear_evacuated_army_ = 0;
    int rear_to_attack_moves_ = 0, rear_to_defense_moves_ = 0, edge_evacuations_ = 0;
    int corner_evacuations_ = 0, dead_end_evacuations_ = 0, active_edge_exemptions_ = 0;
    int affinity_moves_ = 0;double affinity_gain_total_ = 0;
    int pending_affinity_source_ = -1, pending_affinity_dest_ = -1, pending_affinity_sink_ = -1;
    struct AffinitySnapshot {int turn,total,rear,attack,defense;};
    struct EvacuationTrace {int turn,cell,army,dest,sink;double affinity;};
    std::vector<AffinitySnapshot> affinity_snapshots_;
    std::vector<EvacuationTrace> evacuation_traces_;
    struct FieldTrace {int turn,rear,old_stage,stage,front,enemy;double ar,ao,as,af,ae;};
    std::vector<FieldTrace> field_traces_;
    int old_staging_cell_ = -1, last_field_stage_ = -1, last_field_enemy_ = -1;
    bool land_deficit_ = false, severe_land_deficit_ = false;
    bool land_behind_ = false, production_emergency_ = false, intentional_hold_ = false;
    long long land_deficit_turns_ = 0, severe_land_deficit_turns_ = 0;
    long long neutral_expansion_moves_ = 0, neutral_expansion_before_300_ = 0;
    long long neutral_expansion_before_400_ = 0, neutral_captures_10_before_tick_ = 0;
    long long rear_surplus_moves_ = 0, rear_surplus_army_moved_ = 0;
    int pending_rear_source_ = -1, pending_rear_dest_ = -1;
    struct ProductionSnapshot { int turn, my_land, opp_land, my_army, opp_army; };
    std::vector<ProductionSnapshot> production_snapshots_;
    long long passes_total_=0,passes_intentional_hold_=0,passes_no_movable_army_=0;
    long long passes_no_safe_action_=0,passes_deadline_guard_=0,passes_legality_guard_=0;
    long long passes_strategic_empty_=0,passes_replaced_expansion_=0,passes_replaced_frontier_feed_=0;
    long long frontier_feed_moves_=0;
    long long production_emergency_turns_=0,normal_offense_actions_=0,normal_search_actions_=0;
    long long normal_economy_actions_=0,neutral_capture_actions_=0,productive_fallback_actions_=0;
    int turns_since_search_progress_=0,consecutive_low_info_contact_=0;
    long long exploration_tempo_boost_turns_=0,contact_repetition_penalties_=0;
    long long search_progress_actions_=0,meaningful_fog_reveal_actions_=0;
    int pending_frontier_feed_source_=-1,pending_frontier_feed_dest_=-1;

    bool flip10() { return unit_(rng_) < 0.10; }

    bool inside(int r, int c) const { return r >= 0 && r < h_ && c >= 0 && c < w_; }
    int cell(int r, int c) const { return r * w_ + c; }
    int row(int x) const { return x / w_; }
    int col(int x) const { return x % w_; }
    int neighbor(int x, int d) const {
        int r = row(x) + DR[d], c = col(x) + DC[d];
        return inside(r, c) ? cell(r, c) : -1;
