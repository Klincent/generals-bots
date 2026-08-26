# Juraj V3.5 analytical rebuild

V3.5 is a deterministic C++17 agent. It reuses only the competition protocol and
safe graph primitives, not V3.4's strategic candidate-scoring selector. There is
no model, learned pack, or runtime randomness.

## Hierarchy and requirement map

`main.cpp::Agent::act` is an explicit pipeline: observed `World Model` →
`OpponentModel`/`Belief` → persistent castle plan → `Budget`/funding forecasts →
packet/logistics constraints → tiered candidates → `schedule`. Candidate utility
is compared only inside a tier; tier number is lexicographically dominant.

* **A / castles:** `plan_castles` exhaustively chooses C1+C2 jointly. Eligibility
  precedes a tuple ordered by sequential cost, deadline/distance, graph value,
  and cell IDs. `forecast` supplies remaining cost, feeder capacity, feasibility,
  and latest safe funding start. C1/C2 deadlines are 150/250; C3 is optional.
* **B / production:** `ProductionState` has hysteretic healthy/soft/severe states.
  Capturable neutral cells immediately before a production tick are tier 3 unless
  terminal or hard-feasibility work exists.
* **C / budgets:** `Budget` names general, reaction, C1, C2, expansion, search,
  front/war, and genuinely free allocations.
* **D / logistics:** `Packet` has a persistent role, target, assignment/event
  version, idle count, and path. `route_allowed` rejects worsening potential and
  2/3/4 loops. Rear/edge/dead-end surplus is scheduled in tier 2 and moves FULL-1;
  there is no speculative HALF or random flip.
* **E / contact:** first meaningful contact increments the event version and
  creates a global war budget. Safe remote surplus is routed toward the observed
  front by decreasing graph ETA.
* **F / search:** `Belief` legally eliminates observed impossible cells and
  back-projects observed enemy flow toward upstream source regions.
* **G–J / opponent:** `OpponentModel` maintains independent confidence for all
  ten requested archetypes with decay, evidence-dependent update rate, and
  hysteresis through the strong threshold. `adaptation` implements an explicit
  response for every archetype without replacing castle/survival invariants.
* **I / reaction:** visible packet activity and response ratios feed opponent
  evidence; trace output records the selected exploit. Rich probe correlation is
  intentionally a first-iteration partial item.
* **K / scheduler:** tier 0 terminal/survival, tier 1 hard feasibility, tier 2
  mobilization/logistics/exploits, tier 3 production/JIT development, tier 4
  optional expansion/search.
* **L / events:** contact currently increments `event_`; packet reversals require
  an event-version change plus a named reason. Additional event sources remain.
* **M / telemetry:** compact `[v35_plan]`, `[v35_castles]`, `[v35_production]`,
  `[v35_logistics]`, `[v35_cycles]`, `[v35_front]`, `[v35_opponent]`,
  `[v35_reaction]`, `[v35_search]`, and `[v35_timing]` records go to stderr.
* **N:** `test_core.cpp` contains twenty deterministic behavioral assertions.
* **O/P:** the benchmark workflow uses exact V3.4 and paired seats. Synthetic
  core scenarios test archetype reachability without claiming reference bots
  have a style not established by their source.
* **Q:** named enums/structs and header-isolated pure functions keep policy
  testable and board work bounded by 441-cell all-pairs BFS at initialization.

## Known first-iteration limitations

Castle re-planning after invalidation, packet identity across merges, reaction
probe matching, distinct front clustering, detailed +10/+25/+50 concentration
snapshots, and a real-game benchmark result are not yet complete. The first
implementation deliberately exposes these gaps rather than hiding them behind
scores. Tactical safety is conservative and ends in protocol-safe PASS on any
internal exception.
