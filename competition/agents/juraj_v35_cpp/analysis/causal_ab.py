#!/usr/bin/env python3
"""Compare two paired_benchmark outputs game-for-game (used seeds only)."""
import argparse
import json
import re
from pathlib import Path


POINTS = {"win": 1.0, "draw": 0.5, "loss": 0.0}


def load(path):
    return {(r["seed"], r["candidate_seat"]): r
            for r in map(json.loads, Path(path).read_text().splitlines())}


def telemetry(row):
    stderr = row.get("stderr", "")
    land_match = re.search(r"^\[v35_land\](.*)$", stderr, re.M)
    land = {int(t): int(v) for t, v in re.findall(r"(\d+):(\d+)",
                                                  land_match.group(1) if land_match else "")}
    actions = re.search(r"^\[v35_actions\].*?pass=(\d+)$", stderr, re.M)
    passes = int(actions.group(1)) if actions else 0
    turns = row.get("turns", 0)
    rate = passes / turns if turns else 0.0
    return {"land50": land.get(50), "land100": land.get(100),
            "land150": land.get(150), "land200": land.get(200),
            "passes": passes, "pass_rate": rate,
            "early_stall": land.get(100, 10**9) < 30 and rate > .05}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--castle", required=True)
    p.add_argument("--recovery", required=True)
    p.add_argument("--output", required=True)
    a = p.parse_args()
    c, r = load(a.castle), load(a.recovery)
    if c.keys() != r.keys():
        raise SystemExit("C/R game keys differ")
    flips, transitions, seat = {}, {}, {0: {"delta": 0, "improved": 0, "regressed": 0},
                                       1: {"delta": 0, "improved": 0, "regressed": 0}}
    rows = []
    for key in sorted(c):
        cr, rr = c[key], r[key]
        flip = f"{cr['result']}->{rr['result']}"
        flips[flip] = flips.get(flip, 0) + 1
        delta = POINTS[rr["result"]] - POINTS[cr["result"]]
        ct, rt = telemetry(cr), telemetry(rr)
        transition = ("early-stall" if ct["early_stall"] else "healthy") + "->" + (
            "early-stall" if rt["early_stall"] else "healthy")
        bucket = transitions.setdefault(transition, {"games": 0, "points_delta": 0,
                                                       "improved": 0, "regressed": 0})
        bucket["games"] += 1
        bucket["points_delta"] += delta
        bucket["improved"] += delta > 0
        bucket["regressed"] += delta < 0
        s = seat[key[1]]
        s["delta"] += delta
        s["improved"] += delta > 0
        s["regressed"] += delta < 0
        rows.append({"seed": key[0], "seat": key[1], "C": cr["result"],
                     "R": rr["result"], "delta": delta, "transition": transition,
                     "C_telemetry": ct, "R_telemetry": rt})
    total = sum(x["delta"] for x in rows)
    out = {"games": len(rows), "flip_matrix": flips, "net_points": total,
           "score_point_change": total / len(rows),
           "improved": sum(x["delta"] > 0 for x in rows),
           "regressed": sum(x["delta"] < 0 for x in rows),
           "unchanged": sum(x["delta"] == 0 for x in rows),
           "by_seat": seat, "stall_transitions": transitions, "matches": rows}
    Path(a.output).write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k != "matches"}, indent=2))


if __name__ == "__main__":
    main()
