# V3.5 competition hardening report

## Freeze and safety

* Starting submitted champion: `4f0fac768a8fc4479d45347a3ecbdbfedd6aef05`, protected by annotated tag `v35-champion-70fresh`.
* Historical V3.4: `2ed9e8bbcf76b36c5276013afc356118fccc8b6e`.
* Protected `30000..30499` was not used. No submission archive was created.

## Forensics and controls

The completed Phase-2 evidence remains 67/6/27 on seeds 22150..22199. The archived classifier identifies 12 early stalls, 11 undercommitted defenses, and four missed intercepts. The richer questions cannot be answered reliably from the checked-in aggregate JSON: it contains no per-turn board ownership/army/castle snapshots for all losses. Inventing castle opportunity and ahead/conversion labels would therefore be misleading. Future runs now emit live opportunity, replanning, build timing, and ROI telemetry so these categories are measurable.

## Implemented layers

The castle layer searches every currently owned plain cell, uses the engine's exact live price, estimates transport work, safety/front distance, production through turn 900, positional value, opportunity cost, and marginal cost for later castles. It replans by current castle count; no C1/C2 dependency or expired deadline remains. Terminal captures and general defense remain tier 0, while worthwhile builds are tier 1.

Opening selection adds frontier access value and trajectory-based stall detection. Defense observes approaching stacks one step sooner and permits time-equal choke staging. Conversion allocates a war budget when materially ahead and makes a confirmed-general route hard priority without overriding survival.

## Validation status

Deterministic C++ behavioral tests pass (30 core checks plus agent recovery scenarios), including the ten requested castle cases. Builds pass without warnings affecting correctness.

A causal replay was attempted for seeds 22050..22051. The host initially lacked NumPy/JAX, then editable installation was blocked because Python 3.14 has no compatible pygame/SDL setup; a `PYTHONPATH` retry terminated before producing game rows. Consequently no W/D/L, castle-timing comparison, fresh 222xx result, or honest loss classification is reported. **No 222xx seed was consumed.** The frozen gameplay was not modified after this validation attempt.

Run the predeclared validation in the documented CPython 3.12 sandbox:

```bash
PYTHONPATH=. python competition/agents/juraj_v35_cpp/paired_benchmark.py \
  --candidate competition/agents/juraj_v35_cpp/run.sh \
  --baseline competition/agents/juraj_cpp/run.sh --start 22200 --seeds 50 \
  --output artifacts/fresh-v34
PYTHONPATH=. python competition/agents/juraj_v35_cpp/proxy_suite.py \
  --candidate competition/agents/juraj_v35_cpp/run.sh --start 22250 --seeds 20 \
  --output artifacts/fresh-proxies
```

The proxy suite is equal-weighted. Its main limitation is repository style skew: three independent expanders are available, but no external submitted rush/turtle bot is archived here.
