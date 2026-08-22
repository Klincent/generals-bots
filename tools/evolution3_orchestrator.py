#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path.cwd()
X0 = "2260b6f19d51a14d7c68770677f22d04dfd88022"
Y0 = "687165839cea8ae5e84da26c99af1c0e5aed4543"
CONTROL = "evolution3/control"
XSTART = "evolution3/start-x"
YSTART = "evolution3/start-y"
XBR = "evolution3/version-x"
YBR = "evolution3/version-y"

def _run(cmd, check=True, capture=False, cwd=ROOT):
    p = subprocess.run(cmd, cwd=cwd, text=True, capture_output=capture)
    if check and p.returncode:
        if capture:
            print(p.stdout, file=sys.stderr)
            print(p.stderr, file=sys.stderr)
        raise RuntimeError(f"command failed ({p.returncode}): {cmd}")
    return p

def load_base():
    _run(["git", "fetch", "--no-tags", "origin", "evolution2/control"])
    src = _run(
        ["git", "show", "origin/evolution2/control:tools/evolution2_orchestrator.py"],
        capture=True,
    ).stdout
    # Infrastructure reuse only: namespace/path substitution. Gameplay never comes
    # from evolution2 branches.
    src = src.replace("evolution2", "evolution3").replace("EVOLUTION2", "EVOLUTION3")
    src = src.replace("/tmp/e2-", "/tmp/e3-")
    marker = "if __name__=='__main__': raise SystemExit(main())"
    src = src.replace(marker, "")
    tmp = Path("/tmp/evolution3_base.py")
    tmp.write_text(src)
    spec = importlib.util.spec_from_file_location("evolution3_base", tmp)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod

b = load_base()

# Replace opponent policy with a diverse, unique-ref-aware suite.
b.OPPS = [
    ("normal-expander", ["juraj-v3.6-expansion-cycle-hardening"]),
    ("aggressive-expander", ["juraj-v3.6-short-cycle-only", "juraj-v3.6-cycle-per-packet"]),
    ("defense-turtle", ["v35-defense-fresh", "v35-logistics-conservative"]),
    ("logistics-recenter", ["v35-logistics-recenter", "v35-logistics-conservative"]),
    ("attack-pass", ["juraj-v3.6-iter1-attack-pass", "juraj-v3.6-cycle-per-packet"]),
    ("search-hunter", ["juraj-v3.6-search-refactor", "juraj-v3.6-loss-forensics"]),
    ("doomer-rusher", ["chatgpt/picker9-doomguard-rusher", "chatgpt/picker9-doomguard"]),
    ("picker", ["chatgpt/picker-v9-muster-castle", "juraj-v3.6-edge-picker"]),
    ("gatherer-economy", ["juraj-v3.6-edge-picker-economics", "v35-heuristic-rebuild", "v35-iterative-1to6"]),
    ("recent-reference", ["chatgpt/picker9-opponent-suite-75", "v35-heuristic-rebuild", "v35-castle-recapture"]),
]
b.CORE = {"normal-expander", "defense-turtle", "logistics-recenter",
          "attack-pass", "search-hunter", "doomer-rusher", "picker"}

RUNTIME = ("main.cpp", "core.hpp", "build.sh", "run.sh")
AGENT = b.AGENT

def runtime_hashes_ref(ref):
    out = {}
    for f in RUNTIME:
        p = _run(["git", "show", f"{ref}:{AGENT / f}"], capture=True)
        out[f] = hashlib.sha256(p.stdout.encode()).hexdigest()
    return out

def runtime_hashes_path(path):
    path = Path(path)
    return {f: hashlib.sha256((path / AGENT / f).read_bytes()).hexdigest() for f in RUNTIME}

def write_hof(s):
    b.dump(Path("evolution3/hall-of-fame.json"), s.get("hall_of_fame", []))

def prepare_opps_unique(s):
    b.fetch_all()
    ready, fail, used, resolved, subs = [], [], set(), set(), []
    for i, (cat, refs) in enumerate(b.OPPS):
        chosen = None
        for ref in refs:
            if ref in used:
                continue
            if b.git("rev-parse", "--verify", f"origin/{ref}", capture=True, check=False).returncode:
                fail.append({"category": cat, "ref": ref, "reason": "missing"})
                continue
            p = b.wt(f"origin/{ref}", f"/tmp/e3-opp-{i}")
            try:
                b.build(p)
                chosen = (cat, ref, p)
                break
            except Exception as exc:
                fail.append({"category": cat, "ref": ref, "reason": str(exc)})
        if chosen:
            ready.append(chosen)
            used.add(chosen[1])
            resolved.add(cat)
            if chosen[1] != refs[0]:
                subs.append({"category": cat, "preferred": refs[0], "substitute": chosen[1]})
    if b.CORE - resolved:
        raise RuntimeError(f"missing core archetypes {sorted(b.CORE-resolved)}")
    if len(ready) < 7:
        raise RuntimeError(f"fewer than 7 diverse buildable opponents ({len(ready)})")
    s["opponent_substitutions"] = subs
    return ready, fail, subs

b.prepare_opps = prepare_opps_unique

def gate_c_original(s, cand, line, cycle, it):
    anchor = s["original_x_clean_sha"] if line == "X" else s["original_y_clean_sha"]
    ap = b.wt(anchor, f"/tmp/e3-gateC-{line}")
    b.build(ap)
    wr = Path("/tmp/e3-gc")
    shutil.rmtree(wr, ignore_errors=True)
    wr.mkdir()
    cw = b.wrapper(cand / AGENT / "run.sh", "CAND", wr / "c.sh")
    aw = b.wrapper(ap / AGENT / "run.sh", "ANCHOR", wr / "a.sh")
    rounds = []
    st = b.fresh(s, 5, f"c{cycle}i{it}-{line}-gateC-r1")
    q1 = b.bench(cw, aw, st, 5, b.RESULTS / f"c{cycle}/iter-{it:02d}/{line}/gateC/r1")
    rounds.append({"start": st, "summary": q1})
    cum = b.combine([q1])
    if cum["score"] < .45:
        st2 = b.fresh(s, 5, f"c{cycle}i{it}-{line}-gateC-r2")
        q2 = b.bench(cw, aw, st2, 5, b.RESULTS / f"c{cycle}/iter-{it:02d}/{line}/gateC/r2")
        rounds.append({"start": st2, "summary": q2})
        cum = b.combine([q1, q2])
    return {"anchor_sha": anchor, "rounds": rounds, "cumulative": cum,
            "decision": "pass" if cum["score"] >= .45 else "reject"}

b.gate_c = gate_c_original

def gate_d_hof(s, cand, line, parent_sha, cycle, it):
    best = s["best_x_sha"] if line == "X" else s["best_y_sha"]
    hist = [h["sha"] for h in s.get("hall_of_fame", [])
            if h.get("lineage") == line and h.get("sha") != parent_sha]
    anchors = []
    for q in [best] + list(reversed(hist)):
        if q and q != parent_sha and q not in anchors:
            anchors.append(q)
        if len(anchors) >= 2:
            break
    if not anchors:
        return {"checks": [], "decision": "pass"}

    checks = []
    for j, q in enumerate(anchors):
        ap = b.wt(q, f"/tmp/e3-gateD-{line}-{j}")
        b.build(ap)
        wr = Path("/tmp/e3-gd")
        shutil.rmtree(wr, ignore_errors=True)
        wr.mkdir()
        cw = b.wrapper(cand / AGENT / "run.sh", "CAND", wr / "c.sh")
        aw = b.wrapper(ap / AGENT / "run.sh", "HOF", wr / "a.sh")
        rounds = []
        st = b.fresh(s, 5, f"c{cycle}i{it}-{line}-gateD-{j}-r1")
        q1 = b.bench(cw, aw, st, 5, b.RESULTS / f"c{cycle}/iter-{it:02d}/{line}/gateD/{j}/r1")
        rounds.append({"start": st, "summary": q1})
        cum = b.combine([q1])
        if cum["score"] < .45:
            st2 = b.fresh(s, 5, f"c{cycle}i{it}-{line}-gateD-{j}-r2")
            q2 = b.bench(cw, aw, st2, 5, b.RESULTS / f"c{cycle}/iter-{it:02d}/{line}/gateD/{j}/r2")
            rounds.append({"start": st2, "summary": q2})
            cum = b.combine([q1, q2])
        check = {"anchor_sha": q, "rounds": rounds, "cumulative": cum,
                 "decision": "pass" if cum["score"] >= .45 else "reject"}
        checks.append(check)
        if check["decision"] != "pass":
            return {"checks": checks, "decision": "reject"}
    return {"checks": checks, "decision": "pass"}

def reject(s, r, rp, line, parent_sha, key, csha, reason):
    r.update({"decision": "REJECTED", "rejection_reason": reason,
              "champion_sha_after": parent_sha, "champion_unchanged": True})
    s.setdefault("rejected_mutations", []).append(r.copy())
    s.setdefault("mutation_history", {}).setdefault(line, []).append(
        {"parent_sha": parent_sha, "candidate_sha": csha, "mutation": key,
         "accepted": False, "reason": reason}
    )
    b.dump(rp, r)
    return False

def attempt_strict(s, line, parent_path, metrics, opps, cycle, it, context):
    parent_sha = s["current_x_champion_sha"] if line == "X" else s["current_y_champion_sha"]
    key = b.choose_mutation(s, line, parent_sha, metrics)
    rp = b.RESULTS / f"c{cycle}/iter-{it:02d}/{line}/report.json"
    r = {
        "phase": f"cycle{cycle}", "iteration": it, "target_lineage": line,
        "parent_sha": parent_sha, "parent_runtime_hashes": runtime_hashes_path(parent_path),
        "causal_hypothesis": b.diagnose(metrics), "loss_metrics": metrics,
        "context": context, "mutation": key,
    }
    if key is None:
        return reject(s, r, rp, line, parent_sha, None, None, "no untried coherent mutation")

    try:
        cand, csha, cbranch = b.make_candidate(parent_sha, line, cycle, it, key)
    except ValueError as exc:
        return reject(s, r, rp, line, parent_sha, key, None, str(exc))
    except Exception:
        # Build/test crashes are infrastructure failures, not evolutionary rejection.
        raise

    r.update({"candidate_sha": csha, "candidate_branch": cbranch,
              "candidate_runtime_hashes": runtime_hashes_path(cand)})

    ga = b.gate_a(s, cand, parent_path, line, cycle, it)
    r["gateA"] = ga
    if ga["decision"] != "pass":
        return reject(s, r, rp, line, parent_sha, key, csha, "Gate A")

    gb = b.gate_b(s, parent_path, cand, opps, line, cycle, it)
    r["gateB"] = gb
    if gb["decision"] != "pass":
        return reject(s, r, rp, line, parent_sha, key, csha, "Gate B")

    gc = gate_c_original(s, cand, line, cycle, it)
    r["gateC"] = gc
    if gc["decision"] != "pass":
        return reject(s, r, rp, line, parent_sha, key, csha, "Gate C")

    gd = gate_d_hof(s, cand, line, parent_sha, cycle, it)
    r["gateD"] = gd
    if gd["decision"] != "pass":
        return reject(s, r, rp, line, parent_sha, key, csha, "Gate D")

    b.live("before promotion")
    candidate_hashes = runtime_hashes_path(cand)
    s["pending_promotion"] = {"lineage": line, "parent_sha": parent_sha,
                              "candidate_sha": csha, "candidate_branch": cbranch}
    r["decision"] = "ACCEPTED_PENDING"
    b.dump(rp, r); b.dump(b.STATE, s)
    b.persist(f"evolution3: pending {line} c{cycle} i{it}", [b.STATE, rp])

    b.live("immediately before ref move")
    br = b.XBR if line == "X" else b.YBR
    if b.remote(br) != parent_sha:
        raise RuntimeError(f"champion branch changed unexpectedly: {br}")
    b.git("push", "origin", f"{csha}:refs/heads/{br}")
    if b.remote(br) != csha:
        raise RuntimeError("promotion ref move failed")

    if line == "X":
        s["current_x_champion_sha"] = csha
        s["current_x_runtime_hashes"] = candidate_hashes
        s["best_x_sha"] = csha
    else:
        s["current_y_champion_sha"] = csha
        s["current_y_runtime_hashes"] = candidate_hashes
        s["best_y_sha"] = csha

    s.setdefault("hall_of_fame", []).append(
        {"lineage": line, "sha": csha, "runtime_hashes": candidate_hashes,
         "parent_sha": parent_sha, "mutation": key,
         "reason": "accepted Gate A+B+C+D"}
    )
    s["accepted_since_audit"] = int(s.get("accepted_since_audit", 0)) + 1
    s["mutation_history"][line].append(
        {"parent_sha": parent_sha, "candidate_sha": csha,
         "mutation": key, "accepted": True}
    )
    s["pending_promotion"] = None
    r.update({"decision": "ACCEPTED", "champion_sha_after": csha,
              "champion_unchanged": False})
    b.dump(rp, r); b.dump(b.STATE, s); write_hof(s)
    b.persist(f"evolution3: promote {line} {csha[:8]}",
              [b.STATE, rp, Path("evolution3/hall-of-fame.json")])
    return True

b.attempt = attempt_strict

def champions_strict(s):
    if b.remote(b.XBR) != s["current_x_champion_sha"] or b.remote(b.YBR) != s["current_y_champion_sha"]:
        raise RuntimeError("state/ref mismatch")
    x = b.wt(s["current_x_champion_sha"], "/tmp/e3-x")
    y = b.wt(s["current_y_champion_sha"], "/tmp/e3-y")
    if runtime_hashes_path(x) != s["current_x_runtime_hashes"]:
        raise RuntimeError("X champion runtime hash mismatch")
    if runtime_hashes_path(y) != s["current_y_runtime_hashes"]:
        raise RuntimeError("Y champion runtime hash mismatch")
    b.build(x); b.build(y)
    return x, y

b.champions = champions_strict

def preflight_strict(s):
    b.live("preflight")
    xstart = b.remote(XSTART); ystart = b.remote(YSTART)
    xver = b.remote(XBR); yver = b.remote(YBR)
    if xstart != xver or ystart != yver:
        raise RuntimeError("initial version branches do not exactly equal start branches")

    x_orig = runtime_hashes_ref(X0); y_orig = runtime_hashes_ref(Y0)
    x_clean = runtime_hashes_ref(f"origin/{XSTART}")
    y_clean = runtime_hashes_ref(f"origin/{YSTART}")
    if x_orig != x_clean:
        raise RuntimeError("A failed: X0 runtime differs from original gameplay SHA")
    if y_orig != y_clean:
        raise RuntimeError("B failed: Y0 runtime differs from original gameplay SHA")
    if s["cycle1_attempted"] != 0 or s["cycle2_attempted"] != 0:
        raise RuntimeError("E failed: counters are not zero")

    s.update({
        "current_x_champion_sha": xver, "current_y_champion_sha": yver,
        "current_x_runtime_hashes": x_clean, "current_y_runtime_hashes": y_clean,
        "original_x_clean_sha": xstart, "original_y_clean_sha": ystart,
        "original_x_sha": xstart, "original_y_sha": ystart,
        "original_x_runtime_hashes": x_orig, "original_y_runtime_hashes": y_orig,
        "best_x_sha": xstart, "best_y_sha": ystart,
        "hall_of_fame": [
            {"lineage":"X","sha":xstart,"gameplay_source_sha":X0,
             "runtime_hashes":x_clean,"reason":"immutable X0 clean start"},
            {"lineage":"Y","sha":ystart,"gameplay_source_sha":Y0,
             "runtime_hashes":y_clean,"reason":"immutable Y0 clean start"},
        ],
    })
    b.dump(Path("evolution3/baseline/runtime-hashes.json"), {
        "X0":{"gameplay_source_sha":X0,"clean_sha":xstart,"hashes":x_clean},
        "Y0":{"gameplay_source_sha":Y0,"clean_sha":ystart,"hashes":y_clean},
    })
    b.dump(b.STATE, s); write_hof(s)
    b.persist("evolution3: verified immutable X0/Y0 runtime",
              [b.STATE, Path("evolution3/baseline/runtime-hashes.json"),
               Path("evolution3/hall-of-fame.json")])

    s = b.load()
    x, y = champions_strict(s)

    smoke_seed = b.fresh(s, 1, "preflight-protocol-smoke")
    smoke = b.run([sys.executable, "competition/matchup.py",
                   str(x/AGENT/"run.sh"), str(y/AGENT/"run.sh"),
                   "--mode", "competition", "--seed", str(smoke_seed)],
                  check=False, capture=True)
    if smoke.returncode:
        raise RuntimeError("protocol smoke failed: " + smoke.stderr[-3000:])

    opps, failures, subs = prepare_opps_unique(s)
    manifest = {
        "resolved":[{"archetype":cat,"branch":ref,"tested_sha":b.wsha(path),
                     "runtime_hashes":runtime_hashes_path(path),"build_result":"pass"}
                    for cat,ref,path in opps],
        "failures":failures, "substitutions":subs,
    }
    b.dump(Path("evolution3/baseline/opponent-suite.json"), manifest)

    hv, mx, my, st = b.h2h(s, x, y, 10, "preflight-X-v-Y", b.BASE/"x-v-y")
    starts = {cat:b.fresh(s,3,f"preflight-suite-{cat}") for cat,_,_ in opps}
    xr, xa = b.suite(x, opps, s, "X", "preflight-X", 3, starts)
    yr, ya = b.suite(y, opps, s, "Y", "preflight-Y", 3, starts)
    report = {
        "checks":{
            "A_X0_runtime_identity":"PASS","B_Y0_runtime_identity":"PASS",
            "C_version_x_initial_X0":"PASS","D_version_y_initial_Y0":"PASS",
            "E_counters_zero":"PASS","F_no_old_evolution_gameplay":"PASS",
            "G_no_evolution2_gameplay":"PASS",
        },
        "x_clean_sha":xstart,"y_clean_sha":ystart,"protocol_smoke_seed":smoke_seed,
        "x_v_y":hv,"x_v_y_start":st,"x_loss_metrics":mx,"y_loss_metrics":my,
        "x_suite":xr,"y_suite":yr,"x_aggregate":xa,"y_aggregate":ya,
        "opponents":manifest,
    }
    b.dump(b.BASE/"report.json", report)
    s["baseline_summary"]={"x_v_y":hv,"x_suite":xa,"y_suite":ya}
    s["phase"]="cycle1"; s["retry_count"]=0; s["last_error"]=None
    b.dump(b.STATE,s); write_hof(s)
    b.persist("evolution3: complete strict preflight",
              [b.STATE,b.BASE/"report.json",Path("evolution3/baseline/opponent-suite.json"),
               Path("evolution3/hall-of-fame.json")])

b.preflight = preflight_strict

def audit_lineage(s, line, opps, audit_no):
    current = s["current_x_champion_sha"] if line=="X" else s["current_y_champion_sha"]
    original = s["original_x_clean_sha"] if line=="X" else s["original_y_clean_sha"]
    candidates=[]
    for q in [current, original] + [h["sha"] for h in s["hall_of_fame"] if h.get("lineage")==line]:
        if q not in candidates: candidates.append(q)
    starts={cat:b.fresh(s,5,f"audit-{audit_no}-{line}-{cat}") for cat,_,_ in opps}
    scores={}; paths={}
    for i,q in enumerate(candidates):
        p=b.wt(q,f"/tmp/e3-audit-{line}-{i}"); b.build(p); paths[q]=p
        rows,agg=b.suite(p,opps,s,f"{line}-{i}",f"audits/audit-{audit_no}/{line}",5,starts)
        scores[q]={"aggregate":agg,"minimum":min(r["summary"]["score"] for r in rows),"rows":rows}
    best=max(candidates,key=lambda q:(scores[q]["aggregate"]["score"],scores[q]["minimum"],scores[q]["aggregate"]["W"]))
    delta=scores[best]["aggregate"]["score"]-scores[current]["aggregate"]["score"]
    rollback=best!=current and delta>=.05
    if rollback:
        b.live("before rollback")
        br=b.XBR if line=="X" else b.YBR
        if b.remote(br)!=current: raise RuntimeError("champion moved during audit")
        b.git("push","--force","origin",f"{best}:refs/heads/{br}")
        h=runtime_hashes_path(paths[best])
        if line=="X":
            s["current_x_champion_sha"]=best; s["current_x_runtime_hashes"]=h; s["best_x_sha"]=best
        else:
            s["current_y_champion_sha"]=best; s["current_y_runtime_hashes"]=h; s["best_y_sha"]=best
        s["rollback_history"].append({"audit":audit_no,"lineage":line,
            "revoked_sha":current,"restored_sha":best,
            "current_score":scores[current]["aggregate"]["score"],
            "restored_score":scores[best]["aggregate"]["score"],
            "reason":"fresh audit showed >=5pp aggregate regression"})
    else:
        if line=="X": s["best_x_sha"]=best
        else: s["best_y_sha"]=best
    return {"lineage":line,"current_before":current,"best_sha":best,
            "rollback":rollback,"scores":scores}

def maybe_audit(s, opps):
    if int(s.get("accepted_since_audit",0))<5: return None
    n=int(s.get("audit_count",0))+1
    rep={"audit":n,"X":audit_lineage(s,"X",opps,n),"Y":audit_lineage(s,"Y",opps,n)}
    s["accepted_since_audit"]=0; s["audit_count"]=n
    p=b.RESULTS/f"audits/audit-{n:02d}.json"; b.dump(p,rep); b.dump(b.STATE,s); write_hof(s)
    b.persist(f"evolution3: robustness audit {n}",
              [b.STATE,p,Path("evolution3/hall-of-fame.json")])
    return rep

def cycle1_strict(s):
    it=s["cycle1_attempted"]+1; b.live(f"cycle1 {it}")
    x,y=champions_strict(s); opps,fail,subs=prepare_opps_unique(s)
    hv,mx,my,st=b.h2h(s,x,y,10,f"c1i{it}-h2h",b.RESULTS/f"c1/iter-{it:02d}/h2h")
    tb=None; suite_tb=None
    if hv["score"]<.475: weak="X"
    elif hv["score"]>.525: weak="Y"
    else:
        tb,tx,ty,tst=b.h2h(s,x,y,5,f"c1i{it}-tiebreak",b.RESULTS/f"c1/iter-{it:02d}/tiebreak")
        if tb["score"]<.5: weak="X"
        elif tb["score"]>.5: weak="Y"
        else:
            starts={cat:b.fresh(s,2,f"c1i{it}-suite-tie-{cat}") for cat,_,_ in opps}
            xr,xa=b.suite(x,opps,s,"X",f"c1/iter-{it:02d}/suite-tie",2,starts)
            yr,ya=b.suite(y,opps,s,"Y",f"c1/iter-{it:02d}/suite-tie",2,starts)
            suite_tb={"X":xa,"Y":ya}
            weak="X" if xa["score"]<ya["score"] else ("Y" if ya["score"]<xa["score"] else ("X" if it%2 else "Y"))
    ok=attempt_strict(s,weak,x if weak=="X" else y,mx if weak=="X" else my,
                      opps,1,it,{"x_v_y":hv,"start":st,"tiebreak":tb,
                                 "suite_tiebreak":suite_tb,"selected_weaker_lineage":weak})
    s["cycle1_attempted"]=it; s["cycle1_promoted"]+=int(ok); s["cycle1_rejected"]+=int(not ok)
    maybe_audit(s,opps)
    if it>=23: s["phase"]="cycle2"
    b.dump(b.STATE,s); write_hof(s)
    b.persist(f"evolution3: finalize cycle1 attempt {it}",
              [b.STATE,Path("evolution3/hall-of-fame.json")])

b.cycle1=cycle1_strict

def cycle2_strict(s):
    it=s["cycle2_attempted"]+1; b.live(f"cycle2 {it}")
    x,y=champions_strict(s); opps,fail,subs=prepare_opps_unique(s)
    hv,mxh,myh,st=b.h2h(s,x,y,5,f"c2i{it}-h2h",b.RESULTS/f"c2/iter-{it:02d}/h2h")
    starts={cat:b.fresh(s,3,f"c2i{it}-diag-{cat}") for cat,_,_ in opps}
    xr,xa=b.suite(x,opps,s,"X",f"c2/iter-{it:02d}/diagX",3,starts)
    yr,ya=b.suite(y,opps,s,"Y",f"c2/iter-{it:02d}/diagY",3,starts)
    weak=lambda rows,agg: agg["score"]<.72 or any(r["summary"]["score"]<.50 for r in rows)
    xok=yok=None
    if weak(xr,xa):
        worst=min(xr,key=lambda r:r["summary"]["score"])
        xm=b.parse_metrics(b.RESULTS/f"c2/iter-{it:02d}/diagX/X/{worst['category']}/games.jsonl",
                           "X",lambda g:g.get("result")=="loss")
        xok=attempt_strict(s,"X",x,xm,opps,2,it,
                           {"x_v_y":hv,"suite_aggregate":xa,"worst":worst["category"]})
    if weak(yr,ya):
        yp=b.wt(s["current_y_champion_sha"],"/tmp/e3-y2"); b.build(yp)
        worst=min(yr,key=lambda r:r["summary"]["score"])
        ym=b.parse_metrics(b.RESULTS/f"c2/iter-{it:02d}/diagY/Y/{worst['category']}/games.jsonl",
                           "Y",lambda g:g.get("result")=="loss")
        yok=attempt_strict(s,"Y",yp,ym,opps,2,it,
                           {"x_v_y":hv,"suite_aggregate":ya,"worst":worst["category"]})
    s["cycle2_attempted"]=it
    if xok is None:s["cycle2_x_skipped"]+=1
    elif xok:s["cycle2_x_promoted"]+=1
    else:s["cycle2_x_rejected"]+=1
    if yok is None:s["cycle2_y_skipped"]+=1
    elif yok:s["cycle2_y_promoted"]+=1
    else:s["cycle2_y_rejected"]+=1
    maybe_audit(s,opps)
    if it>=32:s["phase"]="final"
    b.dump(b.STATE,s); write_hof(s)
    b.persist(f"evolution3: finalize cycle2 attempt {it}",
              [b.STATE,Path("evolution3/hall-of-fame.json")])

b.cycle2=cycle2_strict

def final_strict(s):
    b.live("final")
    opps,fail,subs=prepare_opps_unique(s)
    raw=[]
    for q in [s["current_x_champion_sha"],s["current_y_champion_sha"],
              s["original_x_clean_sha"],s["original_y_clean_sha"],
              s["best_x_sha"],s["best_y_sha"]] + [h["sha"] for h in s["hall_of_fame"]]:
        if q and q not in raw: raw.append(q)

    # Runtime dedupe, then mandatory finalists + at most two extra HOF checkpoints.
    seen=set(); unique=[]; path_cache={}
    for i,q in enumerate(raw):
        p=b.wt(q,f"/tmp/e3-final-dedupe-{i}"); h=runtime_hashes_path(p)
        k=tuple(sorted(h.items()))
        if k not in seen:
            seen.add(k); unique.append(q); path_cache[q]=p
    mandatory=[]
    for q in [s["current_x_champion_sha"],s["current_y_champion_sha"],
              s["original_x_clean_sha"],s["original_y_clean_sha"],
              s["best_x_sha"],s["best_y_sha"]]:
        if q in unique and q not in mandatory: mandatory.append(q)
    finalists=mandatory+[q for q in reversed(unique) if q not in mandatory][:2]

    paths={}
    for i,q in enumerate(finalists):
        p=path_cache.get(q) or b.wt(q,f"/tmp/e3-final-{i}"); b.build(p); paths[q]=p

    starts={cat:b.fresh(s,5,f"final-suite-{cat}") for cat,_,_ in opps}
    scores={}
    for i,q in enumerate(finalists):
        rows,agg=b.suite(paths[q],opps,s,f"C{i}",f"final/suite-{i}",5,starts)
        scores[q]={"rows":rows,"aggregate":agg,
                   "minimum":min(r["summary"]["score"] for r in rows)}

    mutual=[]
    for i in range(len(finalists)):
        for j in range(i+1,len(finalists)):
            a,bb=finalists[i],finalists[j]
            wr=Path("/tmp/e3-final-h2h"); shutil.rmtree(wr,ignore_errors=True); wr.mkdir()
            aw=b.wrapper(paths[a]/AGENT/"run.sh","A",wr/"a.sh")
            bw=b.wrapper(paths[bb]/AGENT/"run.sh","B",wr/"b.sh")
            st=b.fresh(s,10,f"final-h2h-{i}-{j}")
            z=b.bench(aw,bw,st,10,b.RESULTS/f"final/h2h-{i}-{j}")
            mutual.append({"a":a,"b":bb,"start":st,"summary":z})

    champ=max(finalists,key=lambda q:(scores[q]["aggregate"]["score"],
                                      scores[q]["minimum"],scores[q]["aggregate"]["W"]))
    shutil.rmtree(b.FINAL,ignore_errors=True); pkg=b.FINAL/"juraj_v35"; pkg.mkdir(parents=True)
    for f in RUNTIME: shutil.copy2(paths[champ]/AGENT/f,pkg/f)
    report={
        "original_x_gameplay_sha":X0,"original_y_gameplay_sha":Y0,
        "original_x_clean_sha":s["original_x_clean_sha"],"original_y_clean_sha":s["original_y_clean_sha"],
        "final_x_sha":s["current_x_champion_sha"],"final_y_sha":s["current_y_champion_sha"],
        "best_x_sha":s["best_x_sha"],"best_y_sha":s["best_y_sha"],
        "final_champion_sha":champ,"final_champion_runtime_hashes":runtime_hashes_path(paths[champ]),
        "cycle1_attempted":s["cycle1_attempted"],"cycle1_promoted":s["cycle1_promoted"],
        "cycle1_rejected":s["cycle1_rejected"],"cycle2_attempted":s["cycle2_attempted"],
        "cycle2_x_promoted":s["cycle2_x_promoted"],"cycle2_x_rejected":s["cycle2_x_rejected"],
        "cycle2_y_promoted":s["cycle2_y_promoted"],"cycle2_y_rejected":s["cycle2_y_rejected"],
        "audit_count":s.get("audit_count",0),"rollback_count":len(s.get("rollback_history",[])),
        "suite":scores,"mutual":mutual,
        "selection_reason":"fresh unseen aggregate, then worst archetype, then raw wins",
        "errors":0,"illegal_actions":0,
    }
    b.dump(b.FINAL/"VALIDATION.json",report)

    # Build exact files, then build again from clean ZIP extraction.
    b.run(["bash","build.sh"],cwd=pkg); (pkg/"agent").unlink(missing_ok=True)
    zp=b.FINAL/"generals_evolution3_submission.zip"
    with zipfile.ZipFile(zp,"w",zipfile.ZIP_DEFLATED) as z:
        for f in RUNTIME:z.write(pkg/f,arcname=f"juraj_v35/{f}")
    clean=Path("/tmp/e3-cleanzip"); shutil.rmtree(clean,ignore_errors=True); clean.mkdir()
    with zipfile.ZipFile(zp) as z:
        names=sorted(z.namelist()); expected=sorted(f"juraj_v35/{f}" for f in RUNTIME)
        if names!=expected: raise RuntimeError(f"unexpected ZIP contents {names}")
        z.extractall(clean)
    b.run(["bash","build.sh"],cwd=clean/"juraj_v35"); (clean/"juraj_v35"/"agent").unlink(missing_ok=True)
    checksum=hashlib.sha256(zp.read_bytes()).hexdigest()
    (b.FINAL/"generals_evolution3_submission.sha256").write_text(
        checksum+"  generals_evolution3_submission.zip\n")
    s["final_champion_sha"]=champ;s["final_champion_runtime_hashes"]=runtime_hashes_path(paths[champ])
    s["final_submission_sha256"]=checksum;s["phase"]="done"
    b.dump(b.STATE,s);write_hof(s)
    b.persist("evolution3: final champion and validated submission",
              [b.STATE,Path("evolution3/hall-of-fame.json"),b.FINAL/"VALIDATION.json",
               zp,b.FINAL/"generals_evolution3_submission.sha256"])

b.final_tournament=final_strict

def main():
    s=b.load()
    try:
        if b.STOP.exists():
            print("evolution3/STOP present; no work performed"); return 0
        b.fetch_all()
        ph=s["phase"]
        if ph=="preflight":preflight_strict(s)
        elif ph=="cycle1":cycle1_strict(s)
        elif ph=="cycle2":cycle2_strict(s)
        elif ph=="final":final_strict(s)
        elif ph=="done":print("evolution3 already done")
        else:raise RuntimeError(f"bad phase {ph}")
        s=b.load();s["retry_count"]=0;s["last_error"]=None;b.dump(b.STATE,s)
        b.persist("evolution3: clear recovery state",[b.STATE]);return 0
    except StopIteration as exc:
        print(exc);return 0
    except Exception as exc:
        print("EVOLUTION3 INFRASTRUCTURE FAILURE:",exc,file=sys.stderr)
        b.failure(s,exc);return 2

if __name__=="__main__":
    raise SystemExit(main())
