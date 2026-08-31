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
