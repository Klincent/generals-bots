# Final superbot results

## 2026-08-31 — deterministic final competition policy

- **Branch:** `codex/final-superbot`
- **Baseline:** `5043c64ed62ad48f5aa2fa6690ac73795601fe75`
- **Policy:** selective edge/rear picker, late decisive muster and general hunt, overdue castle funding, captured-castle recapture, visible-doomstack defensive muster, and existing V3.5 expansion/front/threat infrastructure. All final thresholds are compiled constants; environment overrides were removed.
- **Tests/build:** core, agent recovery, picker lifecycle/economics, muster/castle/general-capture, protocol, and release build passed.
- **Focused telemetry:** picker scenario completed 1/1 route in 18 moves, delivered 56 army, and had 0 aborts. Focused decisions remained below 60 ms.
- **Paired smoke benchmark:** seeds `41000..41002`, both seats, exact `5043c64ed62ad48f5aa2fa6690ac73795601fe75` baseline: **4 W / 0 D / 2 L**, score **66.67%**, paired bootstrap 95% CI **[50%, 100%]**, seat-0/seat-1 **66.67% / 66.67%**, **0 errors**, and **0 illegal actions**. Mean game length was 557.5 turns. Decision round-trip latency was p50 1.063 ms, p95 1.184 ms, p99 1.199 ms, max 28.407 ms. This six-game result is smoke evidence only and is far too small to establish competitive superiority.
- **Known weaknesses:** only a small valid paired smoke result was completed; no broad diverse-opponent suite was completed locally; DoomGuard depends on visible concentrations; late attack muster is strongest after finding the enemy general; conservative picker gates can defer harvesting.
- **Decision:** final submission candidate under explicit competitive uncertainty.

## 2026-08-31 — radical-superbot front-pressure finalist

- **Branch:** `codex/radical-superbot`
- **Exact baseline:** `ea42416c` (`codex/final-superbot`).
- **Change:** when the enemy general remains hidden, a bot holding both a land lead and at least 1.35x the opponent's army now enters the existing gather/launch pipeline against the primary live front after turn 350. Emergency defense, castle deadlines, and severe production deficits still pre-empt this mode.
- **Evaluation harness repair:** agent directories are resolved to `run.sh`, missing executables fail before games start, and the repository root is exported through `PYTHONPATH`. This fixes the two concrete false-benchmark failures observed during this run (executing a directory and failing to import `generals`).
- **Diverse screen, frozen pre-change final-superbot, seeds `42000..42005`, both seats:** versus exact e50123 champion **6/2/4, 58.33%**; picker9 DoomGuard **4/6/2, 58.33%**; evolution4 champion `2260b6f1` **4/4/4, 50.00%**; castle-edge-hardening **10/1/1, 87.50%**. Aggregate: **24/13/11, 63.54% score**, zero errors and zero illegal actions. This diagnoses draw/late-conversion behavior as the largest remaining opportunity, especially against picker and evolution families.
- **Paired candidate screen, untouched seeds `43000..43003`, both seats, versus exact e50123:** **3/2/3, 50.00%**, paired bootstrap 95% CI **[18.75%, 75.00%]**, zero errors, zero illegal actions, p50 **1.053 ms**, maximum **20.536 ms**. This small screen establishes runtime safety but is statistically inconclusive; it does not establish superiority.
- **Known weaknesses:** the requested 60% promotion threshold was not established on an adequately large unseen pool; front pressure is deliberately gated and may be rare; opponent-relative seat asymmetry remains large; games often reach the 1200-turn cap.
- **Decision:** strongest runtime-clean finalist available in this run, but **PROMISING / UNCONFIRMED**, not a statistically confirmed improvement.
