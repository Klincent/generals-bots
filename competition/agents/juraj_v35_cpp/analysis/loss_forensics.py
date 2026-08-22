#!/usr/bin/env python3
"""Turn deterministic full-state loss traces into a reproducible audit table.

The classifications are deliberately conservative.  They describe observable
state/action facts and never infer an internal candidate reason that was not
emitted by the production agent.
"""
import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path

import numpy as np


DIRS = ((-1, 0), (1, 0), (0, -1), (0, 1))


def telemetry(row):
    stderr = row.get("stderr", "")
    m = re.search(r"^\[v35_land\](.*)$", stderr, re.M)
    land = {int(k): int(v) for k, v in re.findall(r"(\d+):(\d+)", m.group(1) if m else "")}
    m = re.search(r"^\[v35_actions\].*?defense=(\d+).*?pass=(\d+)$", stderr, re.M)
    defense, passes = map(int, m.groups()) if m else (0, 0)
    return land, defense, passes


def cells(mask):
    return [tuple(x) for x in np.argwhere(mask)]


def adjacent(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1


def visible(own, cell):
    r, c = cell
    if own[r, c]:
        return True
    return any(0 <= r + dr < own.shape[0] and 0 <= c + dc < own.shape[1]
               and own[r + dr, c + dc] for dr, dc in DIRS)


def analyse(game, trace):
    seat, enemy = game["candidate_seat"], 1 - game["candidate_seat"]
    frames = trace["frames"]
    land, defense_total, passes = telemetry(game)
    pass_rate = passes / max(1, game["turns"])
    early = land.get(100, 10**9) < 30 and pass_rate > .05
    first_contact = first_threat = first_killer_visible = None
    final_window_threat = None
    enemy_general_known = False
    favorable_general = False
    general_armies = []
    last_actions = []
    killer_path = []
    final_enemy_advantage = 0
    intercept_available = False
    counterattack = False
    for f in frames:
        army = np.asarray(f["armies"])
        ownership = np.asarray(f["ownership"], dtype=bool)
        generals = np.asarray(f["generals"], dtype=bool)
        own, foe = ownership[seat], ownership[enemy]
        our_generals = cells(generals & own)
        enemy_generals = cells(generals & foe)
        if not our_generals:
            continue
        general = our_generals[0]
        general_armies.append([f["turn"], int(army[general])])
        visible_enemies = [x for x in cells(foe) if visible(own, x)]
        if visible_enemies and first_contact is None:
            first_contact = f["turn"]
        if enemy_generals and visible(own, enemy_generals[0]):
            enemy_general_known = True
            eg = enemy_generals[0]
            for x in cells(own):
                if adjacent(x, eg) and army[x] - 1 > army[eg]:
                    favorable_general = True
        threats = [x for x in visible_enemies
                   if abs(x[0] - general[0]) + abs(x[1] - general[1]) <= 5
                   and army[x] >= max(6, army[general] // 2)]
        if threats and first_threat is None:
            first_threat = f["turn"]
        if threats:
            threat = max(threats, key=lambda x: army[x])
            killer_path.append([f["turn"], [int(threat[0]), int(threat[1])],
                                int(army[threat])])
            final_enemy_advantage = int(army[threat] - army[general])
            # A local interceptor can legally enter the threat cell and survive.
            if f["turn"] >= game["turns"] - 30:
                if final_window_threat is None:
                    final_window_threat = f["turn"]
                intercept_available |= any(adjacent(x, threat) and army[x] - 1 > army[threat]
                                           for x in cells(own))
        action = f["actions"][seat]
        if f["turn"] >= game["turns"] - 30:
            last_actions.append(action)
        if enemy_generals:
            eg = enemy_generals[0]
            counterattack |= any(abs(x[0]-eg[0]) + abs(x[1]-eg[1]) <= 3
                                 and army[x] > army[eg] + 3 for x in cells(own))
    if killer_path:
        first_killer_visible = killer_path[0][0]
    last_general = general_armies[-30:]
    last_defensive = sum(a[0] == 0 for a in last_actions)  # moves, upper bound
    warning = None if final_window_threat is None else game["turns"] - final_window_threat
    if early:
        cause = "EARLY_STALL"
        evidence = f"land100={land.get(100)}; PASS={pass_rate:.1%}"
    elif favorable_general:
        cause = "MISSED_ENEMY_GENERAL_KILL"
        evidence = "visible adjacent favorable general capture existed"
    elif intercept_available and warning is not None and warning >= 2:
        cause = "INTERCEPT_AVAILABLE_NOT_USED"
        evidence = f"legal winning adjacent interceptor observed; {warning}-turn warning"
    elif counterattack and enemy_general_known:
        cause = "MISSED_COUNTERATTACK"
        evidence = "known enemy general had a nearby stronger friendly stack"
    elif warning is not None and warning <= 1:
        cause = "THREAT_DETECTED_TOO_LATE"
        evidence = f"first qualifying visible general threat only {warning} turn(s) before death"
    elif warning is not None and final_enemy_advantage > 0:
        cause = "DEFENSE_UNDERCOMMITTED"
        evidence = f"visible threat warning={warning}; final threat-general margin={final_enemy_advantage}"
    else:
        cause = "ECONOMICALLY_OUTPLAYED"
        evidence = (f"no locally winning interceptor/counter-race observed; "
                    f"land100={land.get(100)}")
    return {"seed": game["seed"], "seat": seat, "turn": game["turns"],
            "land50": land.get(50), "land100": land.get(100),
            "land150": land.get(150), "land200": land.get(200),
            "pass_count": passes, "pass_rate": round(pass_rate, 6),
            "early_stall": early, "first_contact": first_contact,
            "first_general_threat": first_threat,
            "first_killing_stack_visible": "not reconstructable: stacks have no stable identity",
            "qualifying_visible_threat_path_last30": killer_path[-30:],
            "general_army_last30": last_general,
            "defense_actions_total": defense_total,
            "move_actions_last30_upper_bound": last_defensive,
            "legal_interceptor_existed": intercept_available,
            "counterattack_race_existed": counterattack,
            "enemy_general_known": enemy_general_known,
            "favorable_enemy_general_capture": favorable_general,
            "stale_packet_objective": "not observable from protocol trace",
            "castle_funding_interference": "not established by state/action trace",
            "primary_cause": cause, "evidence": evidence}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--games", type=Path, required=True)
    p.add_argument("--traces", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    games = [json.loads(x) for x in a.games.read_text().splitlines()]
    losses = [x for x in games if x.get("result") == "loss"]
    rows = []
    for game in losses:
        path = a.traces / f"trace-{game['seed']}-{game['candidate_seat']}.json"
        rows.append(analyse(game, json.loads(path.read_text())))
    counts = Counter(r["primary_cause"] for r in rows)
    result = {"schema": 1, "losses": len(rows), "counts": dict(counts), "games": rows,
              "limitations": [
                  "Candidate reason/class/tier and rejected alternatives are not emitted by production.",
                  "Last-30 move count is an upper bound, not an internal defense-reason count.",
                  "Stale objectives and castle budget causality are not inferred without internal traces."]}
    a.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"losses": len(rows), "counts": counts}, indent=2, default=dict))


if __name__ == "__main__":
    main()
