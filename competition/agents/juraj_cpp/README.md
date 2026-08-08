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
