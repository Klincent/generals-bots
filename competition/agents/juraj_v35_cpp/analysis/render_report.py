#!/usr/bin/env python3
"""Render the measured A/B and loss-forensics JSON as a Markdown appendix."""
import argparse
import json
from pathlib import Path


def score(rows, key):
    pts = {"win": 1, "draw": .5, "loss": 0}
    w = sum(x[key] == "win" for x in rows)
    d = sum(x[key] == "draw" for x in rows)
    l = sum(x[key] == "loss" for x in rows)
    return w, d, l, 100 * (w + .5*d) / len(rows)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--ab", type=Path, required=True)
    p.add_argument("--forensics", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    ab, forensic = json.loads(a.ab.read_text()), json.loads(a.forensics.read_text())
    rows = ab["matches"]
    cw, cd, cl, cs = score(rows, "C")
    rw, rd, rl, rs = score(rows, "R")
    if rs - cs >= 2.5 and ab["net_points"] > 0:
        decision = "KEEP"
    elif rs - cs < -2.5:
        decision = "REVERT"
    else:
        decision = "UNPROVEN"
    lines = [
        "## Recovery exact-seed A/B (used diagnostic seeds; not fresh validation)", "",
        "- Variant C: `ad9515c92cad83a20825a3a7fe69cc70b4ec1f88`.",
        "- Variant R: `67672295b590b8d2ba6962ce30905c6bc7a6d0a3`.",
        "- Exact V3.4: `2ed9e8bbcf76b36c5276013afc356118fccc8b6e`.",
        "- Used range: `22050..22099`, 50 maps / 100 paired-seat games.",
        "- Both local variants were materialized with `git archive` at the exact commit; "
        "the baseline, engine, truncation, seat order, and `seed * 0x9E3779B1 + 0x35` "
        "RNG derivation were identical.", "",
        "| Variant | W | D | L | Score |", "|---|---:|---:|---:|---:|",
        f"| C | {cw} | {cd} | {cl} | {cs:.2f}% |",
        f"| R | {rw} | {rd} | {rl} | {rs:.2f}% |", "",
        "### Match-by-match flip matrix", "", "| C to R | Games |",
        "|---|---:|",
    ]
    for flip, n in sorted(ab["flip_matrix"].items()):
        lines.append(f"| {flip} | {n} |")
    lines += ["", f"Recovery added **{ab['net_points']:+.1f} points**: "
              f"{ab['improved']} improved, {ab['regressed']} regressed, and "
              f"{ab['unchanged']} unchanged games.", "",
              "| Seat | Net points | Improved | Regressed |", "|---:|---:|---:|---:|"]
    for seat, x in sorted(ab["by_seat"].items()):
        lines.append(f"| {seat} | {x['delta']:+.1f} | {x['improved']} | {x['regressed']} |")
    lines += ["", "### Early-stall causal transitions", "",
              "| C to R | Games | Net points | Improved | Regressed |",
              "|---|---:|---:|---:|---:|"]
    for transition, x in sorted(ab["stall_transitions"].items()):
        lines.append(f"| {transition} | {x['games']} | {x['points_delta']:+.1f} | "
                     f"{x['improved']} | {x['regressed']} |")
    recommendation = ("Prefer the simpler castle-only C candidate; recovery produced one "
                      "improvement and one regression and did not cure an early-stall game."
                      if decision == "UNPROVEN" else "Apply the decision rule above.")
    lines += ["", f"**Recovery recommendation: {decision}.** {recommendation} The mandatory "
              "live castle-cost fix remains required regardless of this decision.", "",
              "## Phase-2 loss forensics", "",
              "The table audits all 37 losses from the deterministic R replay. Classifications "
              "are based on protocol-visible state/action facts; the tooling explicitly marks "
              "internal candidate/objective facts that production does not emit as unobservable.", "",
              "| Seed | Seat | Turn | Early stall | Primary cause | Evidence |",
              "|---:|---:|---:|:---:|---|---|"]
    for x in forensic["games"]:
        lines.append(f"| {x['seed']} | {x['seat']} | {x['turn']} | "
                     f"{'yes' if x['early_stall'] else 'no'} | {x['primary_cause']} | "
                     f"{x['evidence']} |")
    lines += ["", "### Primary-cause counts", "", "| Cause | Losses |",
              "|---|---:|"]
    for cause, n in sorted(forensic["counts"].items(), key=lambda x: (-x[1], x[0])):
        lines.append(f"| {cause} | {n} |")
    recurring = [(c, n) for c, n in forensic["counts"].items() if n >= 5]
    lines += ["", "Recurring observed classes (at least five losses): " +
              (", ".join(f"**{c} ({n})**" for c, n in sorted(recurring)) or "none") + ".",
              "No gameplay correction is implemented here. A class count alone does not satisfy "
              "the required local-correction and Agent-test gates.", "",
              "### Protected ranges", "",
              "`22100..22119` and `22150..22199` remain reserved for later fresh validation. "
              "No seed in `30000..30499` was used.", ""]
    a.output.write_text("\n".join(lines))


if __name__ == "__main__":
    main()
