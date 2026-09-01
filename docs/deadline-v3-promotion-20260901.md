# Rear-belief logistics V3 promotion — 2026-09-01

Frozen baseline: `1394df5ac506fb43795993e25cc46ba2abe1f7d4`.
Candidate patch workflow source: rear-belief logistics V3.

## Matched fresh holdout, exact same seeds/opponents

| Opponent | V3 | Frozen |
| --- | ---: | ---: |
| picker9 | 3W/2D/3L = 50.000% | 2W/3D/3L = 43.750% |
| aggressive rusher | 2W/5D/1L = 56.250% | 2W/5D/1L = 56.250% |
| evolution4 | 3W/2D/3L = 50.000% | 3W/2D/3L = 50.000% |
| castle-edge | 4W/3D/1L = 68.750% | 4W/1D/3L = 56.250% |
| aggregate | 12W/12D/8L = 56.250% | 11W/11D/10L = 51.5625% |

V3 improvement on the matched 32-game set: +4.6875 percentage points of score. Both candidates had 0 errors and 0 illegal actions. V3 improved picker9 and castle-edge, tied frozen against rusher and evolution4, and therefore passes the deadline promotion gate.

V3 tested-candidate holdout run: `33484149374`.
Frozen matched-baseline run: `33488087283`.
Tested V3 artifact: `9791384582`.
Submission archive inside that artifact contains exactly: `main.cpp`, `core.hpp`, `build.sh`, `run.sh`.

Promotion decision: V3 is the new submission champion pending only a non-blocking 64-game robustness extension on fresh seeds 46500+.
