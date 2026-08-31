# Final superbot results

## 2026-08-31 — deterministic final competition policy

- **Branch:** `codex/final-superbot`
- **Baseline:** `5043c64ed62ad48f5aa2fa6690ac73795601fe75`
- **Policy:** selective edge/rear picker, late decisive muster and general hunt, overdue castle funding, captured-castle recapture, visible-doomstack defensive muster, and existing V3.5 expansion/front/threat infrastructure. All final thresholds are compiled constants; environment overrides were removed.
- **Tests/build:** core, agent recovery, picker lifecycle/economics, muster/castle/general-capture, protocol, and release build passed.
- **Focused telemetry:** picker scenario completed 1/1 route in 18 moves, delivered 56 army, and had 0 aborts. Focused decisions remained below 60 ms.
- **Paired benchmark attempt:** seeds `41000..41002`, both seats, exact baseline. INVALID: 0 valid games / 6 harness dependency errors (`generals` unavailable to the Python 3.14 subprocess). A dependency repair was attempted, but no clean rerun completed in the execution window. No W/D/L or score is claimed; no illegal action was observed by the focused protocol tests.
- **Known weaknesses:** no valid local diverse paired result; DoomGuard depends on visible concentrations; late attack muster is strongest after finding the enemy general; conservative picker gates can defer harvesting.
- **Decision:** final submission candidate under explicit competitive uncertainty.
