# juraj_cpp baseline

`juraj_cpp` is a stateful C++17 competition agent.  It reconstructs the static
map from the first fogged observation, analyses the passable-cell graph, keeps a
last-seen world model and economic ledger, estimates the enemy general's spawn
distribution and opponent mode, and selects moves through a strict tactical then
strategic priority system.

The implementation deliberately distinguishes an original mountain from a
castle subsequently shown as `structure-in-fog`: competition maps begin with no
castles, so a structure on a cell that was passable at turn zero is a castle.

Build and run:

```bash
bash competition/agents/juraj_cpp/build.sh
python3 competition/matchup.py \
  competition/agents/juraj_cpp/run.sh \
  competition/agents/expander_cpp/run.sh --mode competition --seed 1
```

Standard output is reserved for protocol actions.  A single metrics line is
written to standard error when stdin closes; it reports decision timing and
match-level counters for benchmark collection.

## V2 strategy

V2 identifies a main offensive stack and routes interior feeder armies toward
it. An explicit strategic state machine switches from expansion/search to
attack preparation as soon as the enemy general is known, limits construction
to one castle, and values direct approach progress before Deathtouch.

Every non-forced strategic move scores both meaningful engine split variants.
The evaluation accounts for combat, armies left at both endpoints, general,
castle and chokepoint defense, main-stack integrity, feeder efficiency, and
visible counterattacks. Immediate wins and forced defenses remain deterministic.

One persistent `std::mt19937_64` independently inverts 10% of legitimate
offense-versus-economy choices and 10% of non-dominated split choices. Set
`JURAJ_RNG_SEED` (an empty value deterministically means zero) to reproduce a
benchmark; otherwise entropy and a high-resolution clock seed each process.
End-of-match stderr metrics include both opportunity/flip rates, split usage,
land and army at turn 50, discovery/approach turns, and timing percentiles.

## V2.1 qualification meta

The agent tracks the largest visible enemy stack and deterministically enters a
general-defense alert when a dangerous linear attacker approaches within eight
walking steps. It prefers source capture and interception over passive
over-garrisoning. A smoothed qualifier-defense score combines interception,
concentrated army, and sacrificed land tempo. When observations support that
model, route scoring permits short detours, probes and feints tax the defender,
and containment or two-prong Deathtouch pressure replaces a losing head-on ram.
The original V2 policy remains the fallback when the opponent ignores probes.

## V2.4 Hunter counterattack

A behavioral signature recognizes Hunter's dominant linear conveyor and its
one-army breadcrumb trail. A persistent compact raider follows that trail back
toward the weak feeding general while deterministic kill-zone moves exploit
Hunter's unsafe advance. When affordable, an owned articulation castle can be
built as an impassable gate in Hunter's route. These dedicated actions are not
randomized; ordinary opponents continue through the V2.3 policy.

## V2.5 contact logistics

First contact is persistent even after fog returns. A proximity-weighted front
stack, a staging cell two to four steps behind contact, and at most one extra
forward castle redirect interior logistics toward the known war. Remote neutral
expansion is discounted while front pressure is idle or our land/army advantage
is dominant, while safe weak-frontier captures and relocation of remote large
stacks receive priority. Hunter's dedicated counterattack still runs first.

## V2.6 spatial affinity

A turn-zero geometry/graph affinity field penalizes rear edges, corners and
terminal branches while rewarding room, junctions, chokepoints and the likely
enemy direction. Cheap dynamic front, attack-corridor and interception bonuses
then override that prior wherever an edge is genuinely useful. Excess rear army
flows toward whichever of the attack and defense networks is under its target
allocation. Exact-cost second castles are allowed on useful dual-purpose axes
under dominance or in response to a newly observed enemy castle.

## V2.6.1 dynamic potential

Static affinity is terrain-only except for a very weak opening direction prior.
Every observation rebuilds a fresh potential field from the current contact,
front, staging cell, visible enemy territory/stacks, defense corridor, strategic
mode and—once revealed—the dominant enemy-general attractor. Search candidates,
fog-revealing scouts, qualifier probes and Hunter breadcrumbs remain governed by
their independent probability/search models rather than terrain affinity.

## V2.7 production-first expansion

Affinity no longer casts a vote in action selection. Neutral frontier captures
receive persistent production value, larger bonuses shortly before turn-50
ticks, and explicit land-deficit/severe-deficit priority. Contact-side discounts
apply only after turn 400 when the agent already leads land by at least 25%.
Rear cleanup is now a narrow deterministic rule: only excess above the mandatory
one-unit production residue is routed from safe rear edges, corners, and terminal
branches toward an explicit attack or defense sink. Search, Hunter, contact,
tactical, and castle systems remain intact; ordinary second castles are deferred
during a severe land deficit.

## V2.7.1 productive pass fallback

Passing is audited and is now a last resort. A cheap neutral-capture fallback is
precomputed before deeper strategy; otherwise idle turns feed high-capacity
expansion frontiers, continue general-search/attack routing, or relocate useful
surplus. Land parity is monitored before the stronger deficit thresholds, and
recent 20-turn land growth raises frontier-feed urgency when the production gap
is worsening. Intentional Hunter kill-zone holds remain deterministic and are
reported separately from no-army, unsafe, deadline, legality, and empty-strategy
passes.

## V2.7.2 hybrid strategy

The V2.6.1 offense/search/contact-versus-economy competition is again the
primary selector; land status contributes moderate scores rather than forcing
early expansion. A hysteretic production emergency starts only below 65% land
(or below 75% with a worsening 20-turn trend) and remains active until 85%
recovery. Frontier feeding is otherwise restricted to productive fallback, so
the V2.7.1 pass protection cannot displace a valid normal strategic action.
Rear-surplus cleanup remains explicit and affinity-free.

## V2.7.3 exploration tempo

Before the enemy general is known, three turns without neutral capture,
meaningful fog revelation, or progress toward the best spawn candidate add a
moderate search/expansion score bonus. Repeated low-information harassment of
the same contact front receives a mild diminishing-return penalty, while major
combat, castles, new corridors, qualifier/Hunter tactics, and all known-general
conversion remain exempt. The soft land-behind bonus is slightly stronger, but
production emergency and productive fallback retain their V2.7.2 placement.

## V2.7.5 selective logistics and castles

The V2.7.3 selector remains authoritative.  A rate-limited edge-surplus
candidate may move all but one army from a safe inactive boundary stack of at
least eight only toward an existing front, search, or main-stack objective; it
can displace routine feeding but not tactical, Hunter, search, or attack play.
Ordinary castles now choose exact-cost-minimum useful sites (within a two-army
price band).  Optional proactive castles begin no earlier than turn 250 and
require economic parity, post-build reserve, a forward graph position, and no
Hunter indication or production emergency.  Castle and edge-action telemetry
is emitted separately for qualification regression auditing.

## V3.0 experimental static-route production architecture

V3 precomputes immutable nine-sector distance fields, up to three general-rooted
route branches, articulation breakthrough values, sector route load, and a
probability-weighted interpretation of the unchanged enemy-general candidate
model. Two cheap, separated route hubs are planned at initialization. The
opening controller values broad neutral frontiers and feeds those planned hubs
only after the initial expansion wave.

Split selection is deterministic: `FULL-1` is the road/feed default, while
`HALF` is used only when both resulting packets have independent route or
frontier work. A short strategic packet history rejects no-progress cycles of
length two through four and penalizes longer repeats. Existing tactical,
general-search, qualifier, Hunter, contact, and known-general conversion layers
retain priority. `JURAJ_V3_SPLIT=full|naive|smart` and
`JURAJ_V3_CASTLES=0|1|2|3` expose the requested ablations; `JURAJ_V3_TRACE=1`
prints action labels to stderr only.

## V3.1 stabilization

V3.1 keeps the static-route opening but makes route movement full-first: smart
half moves require a large source, a substantial moved frontier, and a distinct
high-value secondary branch. Planned castle sites are restricted to the
general's reachable component, receive persistent full-force funding after turn
90, and can build through ordinary contact at their exact live cost. A
hysteretic pre-trigger Hunter suspicion state suppresses optional splits and
castle spending while consolidating a distant mobile stack toward interception;
the confirmed Hunter thresholds and tactical implementation are unchanged.
Funding checkpoints, castle-miss reasons, split source/value statistics, and
Hunter entry-board snapshots are reported to stderr.

## V3.2 early warning and C1 optionality

V3.2 adds a lightweight warning confidence below the unchanged Hunter
confirmation threshold. It combines existing signature evidence with repeated
dominant-stack concentration, proximity, route-consistent movement, and closing
history; hysteresis makes warning logistics deterministic and reversible.
Warning suppresses optional route splits and discourages sending the largest
mobile packet farther from the general without stopping broad expansion.

C1 funding remains persistent, but ordinary construction now waits until turn
140 unless post-build army superiority, local safety, general garrison, and
Hunter-warning checks justify an exceptional early build. Telemetry separates
first funding/buildability from construction, records delay reasons and tactical
use of the funded stack, and reports warning evidence/activation lead times.

## V3.3 generic approaching-force reaction

V3.3 adds an opponent-agnostic logistics constraint for a repeatedly observed,
meaningful concentrated enemy stack whose static graph distance to our general
is decreasing.  The bounded score uses only visible force size, enemy army
concentration, graph proximity, closing rate, persistence, and the position and
strength of our largest useful reaction stack; it does not consume any Hunter
classification state.

Activation requires at least two compatible observations, positive closing,
at least eight enemy army, at least 12% visible concentration, and score 0.55.
The score clears below 0.30 for five turns and unseen evidence decays by 0.90,
0.72, or 0.45 according to age.  While active, ordinary route production keeps
small productive packets moving but protects the primary reaction stack,
suppresses optional HALF, and can consolidate along existing high-load routes.
C1/C2 builds are delayed only when post-build nearby/reaction capacity is
insufficient for the observed force.  Detailed activation and economic-cost
telemetry is emitted on stderr under `[v33_approach]`.

## V3.3.1 approach intervention fixes

V3.3.1 leaves the V3.3 detector unchanged and fixes only its intervention
semantics. Reaction adequacy now requires both sufficient force and plausible
graph positioning; an inadequately positioned reaction stack is hard-rejected
from ordinary outward production moves. A funded castle whose build is delayed
for reaction safety no longer accepts additional castle-feed actions that turn.
Telemetry separately reports candidate penalties, hard rejections, final
selected-action changes, castle delays, and funded-site feed suppressions.

## V3.4 rear logistics and three planned castles

V3.4 converts surplus on safe, inactive rear cells into mobile army while
leaving one army to retain each territory. Small two-, three-, and four-army
piles qualify through aggregate branch/sector surplus; local graph-distance
danger checks protect threatened cells. Rear-drain actions use FULL-1 toward an
attack or defense sink and compete with ordinary economy at a bounded cadence,
rather than existing only as unused candidate telemetry.

The static turn-zero castle program now plans C1, C2, and C3 with sequential
cost estimates and branch/sector diversity. Persistent funding targets the
established C1 and C2 windows plus a C3 window beginning at turn 300. Contact or
enemy-general discovery no longer cancels later plans, while immediate defense,
site danger, and inadequate post-build reaction capacity can still delay them.
`[v34_logistics]` and `[v34_castles]` stderr records expose drain sources,
evacuated army, distance progress, and each castle's funding/build outcome.

After the enemy general is known, V3.4 enters an opponent-agnostic mass
mobilization phase. Safe ordinary rear stacks are ranked by moved army times
static graph progress, so large stranded forces move before marginal economy
packets. At least half of the eligible discovery-time surplus is progressively
committed to the known attack corridor unless general defense or an inadequate
approach-threat reaction force requires the army first. Mobilized-unit credits
follow packets as they merge, preventing repeated hops from being counted as
newly committed army. `[v34_mobilization]` reports discovery-time eligibility,
attack/defense commitments, attack-network concentration, large-stack idle
counts, and +10/+25/+50/+100 snapshots.
