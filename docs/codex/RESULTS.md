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

## 2026-08-31 — final diverse-opponent evidence and package verification

- **Candidate policy:** exact gameplay source from `ea42416c`; no strategic
  thresholds were changed after the smoke benchmark.
- **Diverse paired screen:** seeds `42000..42005`, both seats, against four
  historical families: exact e50123 champion **6 W / 2 D / 4 L (58.33%)**;
  picker9 DoomGuard **4/6/2 (58.33%)**; evolution4 champion `2260b6f1`
  **4/4/4 (50.00%)**; castle-edge-hardening **10/1/1 (87.50%)**. Aggregate:
  **24 W / 13 D / 11 L, 63.54% score**, with **0 errors** and **0 illegal
  actions**. These 48 games are useful diversity evidence, not proof of
  external-leaderboard strength.
- **Rejected follow-ups:** hidden-general pressure scored **3/2/3 (50.00%)**
  against exact e50123 on seeds `43000..43003`, then **2/6/4 (41.67%)**
  against the frozen final policy on seeds `45000..45005`. The pressure change
  was rejected; the packaged gameplay remains the stronger frozen policy.
- **Harness hardening:** paired benchmarks now accept agent directories,
  validate their `run.sh` before starting, and export the repository root via
  `PYTHONPATH`, preventing the two observed false runner failures.
- **Final validation:** all focused tests and the release build pass. The ZIP
  contains exactly `main.cpp`, `core.hpp`, `build.sh`, and `run.sh`; extraction
  into `/tmp/final-superbot-verify` followed by `bash build.sh` succeeds without
  repository headers or runtime files.
- **Artifact:** `submissions/final-superbot.zip`, SHA256
  `5eaaf799328bdf39fb9cd4d2ae2cfb0a795eb0cb73d019122747ecbc1ac8a9ca`.
- **Known weaknesses:** DoomGuard requires visible concentration; general hunt
  is more decisive after locating the enemy general; conservative picker gates
  can leave some rear mass idle; and the diverse screen still has wide
  uncertainty and cannot model the unknown external opponent distribution.

## 2026-08-31 — final local revalidation

- Re-ran the complete focused test suite and release build from the frozen
  `codex/final-superbot` policy; all checks passed.
- Re-extracted `submissions/final-superbot.zip` into a clean temporary directory,
  confirmed its four files are byte-identical to the agent sources, and built it
  successfully with only those files present.
- Recomputed artifact SHA256:
  `5eaaf799328bdf39fb9cd4d2ae2cfb0a795eb0cb73d019122747ecbc1ac8a9ca`.
- No gameplay policy changed after the 48-game diverse-opponent screen.
