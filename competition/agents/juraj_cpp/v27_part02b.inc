    struct FieldTrace {int turn,rear,old_stage,stage,front,enemy;double ar,ao,as,af,ae;};
    std::vector<FieldTrace> field_traces_;
    int old_staging_cell_ = -1, last_field_stage_ = -1, last_field_enemy_ = -1;
    bool land_deficit_ = false, severe_land_deficit_ = false;
    long long land_deficit_turns_ = 0, severe_land_deficit_turns_ = 0;
    long long neutral_expansion_moves_ = 0, neutral_expansion_before_300_ = 0;
    long long neutral_expansion_before_400_ = 0, neutral_captures_10_before_tick_ = 0;
    long long rear_surplus_moves_ = 0, rear_surplus_army_moved_ = 0;
    int pending_rear_source_ = -1, pending_rear_dest_ = -1;
    struct ProductionSnapshot { int turn, my_land, opp_land, my_army, opp_army; };
    std::vector<ProductionSnapshot> production_snapshots_;

    bool flip10() { return unit_(rng_) < 0.10; }

    bool inside(int r, int c) const { return r >= 0 && r < h_ && c >= 0 && c < w_; }
    int cell(int r, int c) const { return r * w_ + c; }
    int row(int x) const { return x / w_; }
    int col(int x) const { return x % w_; }
    int neighbor(int x, int d) const {
        int r = row(x) + DR[d], c = col(x) + DC[d];
