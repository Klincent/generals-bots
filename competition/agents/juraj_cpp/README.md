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
