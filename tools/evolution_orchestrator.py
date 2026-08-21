#!/usr/bin/env python3
import json, os, random, re, shlex, shutil, statistics, subprocess, sys, time
from pathlib import Path

ROOT = Path.cwd()
STATE_PATH = ROOT / "evolution/state.json"
RESULTS = ROOT / "evolution/results"
AGENT_REL = Path("competition/agents/juraj_v35_cpp")
BENCH = ROOT / AGENT_REL / "paired_benchmark.py"
START_SHA = "2260b6f19d51a14d7c68770677f22d04dfd88022"
XBR = "evolution/version-x"
YBR = "evolution/version-y"

OPPONENT_REFS = [
    ("champion", "v35-champion-70fresh"),
    ("defense", "v35-defense-fresh"),
    ("heuristic", "v35-heuristic-rebuild"),
    ("logistics", "v35-logistics-recenter"),
    ("attack-pass", "juraj-v3.6-iter1-attack-pass"),
    ("search", "juraj-v3.6-search-refactor"),
    ("expander", "juraj-v3.6-expansion-cycle-hardening"),
    ("doomer", "chatgpt/picker9-doomguard-rusher"),
    ("picker", "chatgpt/picker-v9-muster-castle"),
]

def run(cmd, cwd=ROOT, check=True, capture=False, env=None):
    if isinstance(cmd, str):
        p = subprocess.run(cmd, cwd=cwd, shell=True, text=True,
                           capture_output=capture, env=env)
    else:
        p = subprocess.run([str(x) for x in cmd], cwd=cwd, text=True,
                           capture_output=capture, env=env)
    if check and p.returncode:
        if capture:
            print(p.stdout, file=sys.stderr)
            print(p.stderr, file=sys.stderr)
        raise RuntimeError(f"command failed ({p.returncode}): {cmd}")
    return p

def git(*args, cwd=ROOT, check=True, capture=False):
    return run(["git", *args], cwd=cwd, check=check, capture=capture)

def jload(p):
    return json.loads(Path(p).read_text())

def jdump(p, obj):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")

def fetch_all():
    run("git fetch --no-tags origin '+refs/heads/*:refs/remotes/origin/*'", check=True)

def ref_exists(ref):
    return git("rev-parse", "--verify", f"origin/{ref}", capture=True, check=False).returncode == 0

def worktree(ref, path, branch_mode=False):
    path = Path(path)
    run(["git", "worktree", "remove", "--force", str(path)], check=False)
    shutil.rmtree(path, ignore_errors=True)
    if branch_mode:
        local = "evo-" + ref.split("/")[-1].replace("_", "-")
        run(["git", "branch", "-D", local], check=False)
        git("worktree", "add", "-B", local, str(path), f"origin/{ref}")
    else:
        git("worktree", "add", "--detach", str(path), f"origin/{ref}")
    return path

def worktree_sha(path):
    return git("rev-parse", "HEAD", cwd=path, capture=True).stdout.strip()

def build_agent(path):
    run(["bash", str(path / AGENT_REL / "test.sh")], cwd=path)
    run(["bash", str(path / AGENT_REL / "build.sh")], cwd=path)

def wrapper(run_sh, label, dest):
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        "#!/usr/bin/env bash\nset -euo pipefail\n"
        + f"bash {shlex.quote(str(Path(run_sh).resolve()))} "
          f"2> >(sed -u 's/^/[{label}] /' >&2)\n"
    )
    dest.chmod(0o755)
    return dest

def fresh_start(state, salt=0):
    used = set(state.get("used_seed_starts", []))
    sr = random.SystemRandom()
    for _ in range(1000):
        x = sr.randrange(100000 + salt, 2000000000)
        if all(abs(x-u) > 100 for u in used):
            state.setdefault("used_seed_starts", []).append(x)
            return x
    raise RuntimeError("could not allocate fresh seed range")

def bench(cand_run, base_run, start, seeds, out):
    out = Path(out)
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True, exist_ok=True)
    p = run(
        [sys.executable, str(BENCH),
         "--candidate", str(cand_run),
         "--baseline", str(base_run),
         "--start", str(start),
         "--seeds", str(seeds),
         "--output", str(out)],
        cwd=ROOT, check=False, capture=True
    )
    if not (out / "summary.json").exists():
        raise RuntimeError(f"benchmark produced no summary: {p.stderr[-4000:]}")
    s = jload(out / "summary.json")
    s["returncode"] = p.returncode
    if s.get("errors", 0) or s.get("illegal_actions", 0) or p.returncode:
        raise RuntimeError(f"invalid benchmark: {s}")
    return s

def parse_prefixed_metrics(games_path, label, losing_predicate):
    rows = [json.loads(x) for x in Path(games_path).read_text().splitlines() if x.strip()]
    samples = []
    prefix = f"[{label}] "
    for g in rows:
        if "result" not in g or not losing_predicate(g):
            continue
        sample = {}
        for line in g.get("stderr", "").splitlines():
            if not line.startswith(prefix):
                continue
            z = line[len(prefix):]
            if z.startswith("[v35_land]"):
                land = {}
                for t,v in re.findall(r"(\d+):(-?\d+)", z):
                    land[int(t)] = int(v)
                sample["land"] = land
            elif z.startswith("[v35_actions]"):
                sample["actions"] = {k: float(v) for k,v in re.findall(r"(\w+)=(-?\d+(?:\.\d+)?)", z)}
            elif z.startswith("[v35_pass]"):
                sample["pass"] = {k: float(v) for k,v in re.findall(r"(\w+)=(-?\d+(?:\.\d+)?)", z)}
            elif z.startswith("[v36_picker]"):
                sample["picker"] = {k: float(v) for k,v in re.findall(r"(\w+)=(-?\d+(?:\.\d+)?)", z)}
            elif z.startswith("[v36_muster]"):
                sample["muster"] = {k: float(v) for k,v in re.findall(r"(\w+)=(-?\d+(?:\.\d+)?)", z)}
            elif z.startswith("[v35_doomguard]"):
                sample["doom"] = {k: float(v) for k,v in re.findall(r"(\w+)=(-?\d+(?:\.\d+)?)", z)}
            elif z.startswith("[v35_threat]"):
                sample["threat"] = {k: float(v) for k,v in re.findall(r"(\w+)=(-?\d+(?:\.\d+)?)", z)}
            elif z.startswith("[v35_castle_deadline]"):
                d = {k: v for k,v in re.findall(r"(\w+)=([^\s]+)", z)}
                for k in list(d):
                    if re.fullmatch(r"-?\d+(?:\.\d+)?", d[k]):
                        d[k] = float(d[k])
                sample["castle"] = d
            elif z.startswith("[v35_front]"):
                sample["front"] = {k: float(v) for k,v in re.findall(r"(\w+)=(-?\d+(?:\.\d+)?)", z)}
        sample["turns"] = g.get("turns", 0)
        samples.append(sample)

    def av(section, key, default=0.0):
        vals = [s.get(section, {}).get(key) for s in samples if key in s.get(section, {})]
        return statistics.mean(vals) if vals else default

    def land_av(turn):
        vals = [s.get("land", {}).get(turn) for s in samples if turn in s.get("land", {})]
        return statistics.mean(vals) if vals else 0.0

    castle1_missing = [s for s in samples if s.get("castle", {}).get("c1_build_turn", -1) == -1]
    castle2_missing = [s for s in samples if s.get("castle", {}).get("c2_build_turn", -1) == -1]
    n=max(1,len(samples))
    return {
        "loss_samples": len(samples),
        "turns": statistics.mean([s.get("turns",0) for s in samples]) if samples else 0,
        "land200": land_av(200), "land250": land_av(250), "land400": land_av(400),
        "expansion_actions": av("actions","expansion"),
        "rear_actions": av("actions","rear"),
        "search_actions": av("actions","search"),
        "war_actions": av("actions","war"),
        "passes": av("actions","pass"),
        "no_strategic": av("pass","pass_no_strategic_candidate"),
        "picker_starts": av("picker","starts"),
        "picker_completions": av("picker","completions"),
        "picker_aborts": av("picker","aborts"),
        "picker_blocked": av("picker","blocked_ticks"),
        "picker_mass_rejects": av("picker","mass_rejects"),
        "picker_eff_rejects": av("picker","efficiency_rejects"),
        "muster_windows": av("muster","windows"),
        "muster_harvest": av("muster","harvest_moves"),
        "muster_attack": av("muster","attack_moves"),
        "doom_starts": av("doom","starts"),
        "doom_moves": av("doom","moves"),
        "threats": av("threat","threats_seen_incoming"),
        "contact_turn": av("front","meaningful_contact", -1),
        "c1_missing_rate": len(castle1_missing)/n if samples else 0,
        "c2_missing_rate": len(castle2_missing)/n if samples else 0,
    }

def replace_one(text, pattern, repl_fn):
    out, n = re.subn(pattern, repl_fn, text, count=1)
    return out if n == 1 and out != text else None

def fmt2(x):
    s=f"{x:.2f}"
    if s.startswith("0"): s=s[1:]
    return s

def mutation_candidates(metrics, history):
    keys=[]
    if metrics.get("land200",0) and metrics["land200"] < 55: keys += ["early_expansion"]
    if metrics.get("land250",0) and metrics["land250"] < 68: keys += ["early_expansion","soft_expansion"]
    if metrics.get("c1_missing_rate",0) >= .34: keys += ["castle_c1_earlier"]
    if metrics.get("picker_starts",0) < .5 and metrics.get("picker_mass_rejects",0) >= metrics.get("picker_eff_rejects",0):
        keys += ["picker_mass_lower"]
    if metrics.get("picker_starts",0) < .5 and metrics.get("picker_eff_rejects",0) > 0:
        keys += ["picker_eff_lower"]
    if metrics.get("picker_starts",0) > 0 and metrics.get("picker_completions",0) < .45*metrics.get("picker_starts",0) and metrics.get("picker_blocked",0) > 1:
        keys += ["picker_mass_raise"]
    if metrics.get("muster_windows",0) > 1 and metrics.get("muster_attack",0) < .5:
        keys += ["launch_lower","finish_earlier"]
    if metrics.get("muster_windows",0) < .5 and metrics.get("contact_turn",-1) >= 0 and metrics.get("turns",0) > 350:
        keys += ["muster_start_earlier"]
    if metrics.get("doom_starts",0) < .25 and metrics.get("threats",0) > 1:
        keys += ["doom_more_sensitive","doom_eta_wider"]
    if metrics.get("doom_starts",0) > 2 and metrics.get("threats",0) < metrics.get("doom_starts",0):
        keys += ["doom_less_sensitive"]
    if metrics.get("passes",0) > 8 or metrics.get("no_strategic",0) > 3:
        keys += ["muster_threshold_lower","picker_eff_lower"]
    if metrics.get("muster_attack",0) > 3 and metrics.get("turns",0) < 500:
        keys += ["launch_raise"]
    keys += ["concentration_more","finish_earlier","early_expansion",
             "muster_threshold_lower","picker_eff_lower","launch_lower",
             "doom_more_sensitive","soft_expansion","search_less_precontact"]
    counts={k:history.count(k) for k in set(history)}
    out=[]
    for k in keys:
        if k not in out and counts.get(k,0) < 5:
            out.append(k)
    return out

def apply_mutation(text, key):
    if key == "picker_mass_lower":
        def f(m):
            v=max(8,int(m.group(1))-2)
            return f"edge_picker_threshold_={v}"
        n=replace_one(text, r"edge_picker_threshold_=(\d+)", f)
        return n, "lower picker start mass threshold by 2"
    if key == "picker_mass_raise":
        def f(m):
            v=min(28,int(m.group(1))+2)
            return f"edge_picker_threshold_={v}"
        n=replace_one(text, r"edge_picker_threshold_=(\d+)", f)
        return n, "raise picker start mass threshold by 2 to avoid fragile sweeps"
    if key == "picker_eff_lower":
        def f(m):
            v=max(.9,float(m.group(1))-.10)
            return "edge_picker_min_efficiency_="+str(round(v,2))
        n=replace_one(text, r"edge_picker_min_efficiency_=([0-9.]+)", f)
        return n, "lower picker minimum efficiency by 0.10"
    if key == "muster_threshold_lower":
        def f(m):
            v=max(4,int(m.group(1))-1)
            return f"muster_threshold_={v}"
        n=replace_one(text, r"muster_threshold_=(\d+)", f)
        return n, "harvest one-unit-smaller backline stacks"
    if key == "muster_start_earlier":
        def f(m):
            v=max(240,int(m.group(1))-20)
            return m.group(0).replace(m.group(1),str(v),1)
        n=replace_one(text, r"bool late_muster=picker_enabled_&&enemy_general>=0&&!immediate&&!late_castle_pending&&o\.turn>=(\d+)", f)
        return n, "start known-general late muster 20 turns earlier"
    if key in ("launch_lower","launch_raise"):
        delta=-5 if key=="launch_lower" else 5
        def f(m):
            base=max(65,min(120,int(m.group(1))+delta))
            add=max(5,min(35,int(m.group(2))+delta))
            return f"launch_need=std::max({{{base},eg_army*3+{add},"
        n=replace_one(text, r"launch_need=std::max\(\{(\d+),eg_army\*3\+(\d+),", f)
        desc="lower late-muster launch requirement" if delta<0 else "raise late-muster launch requirement to avoid premature attacks"
        return n, desc
    if key == "finish_earlier":
        def f(m):
            v=max(650,int(m.group(1))-25)
            return f"bool late_finish=o.turn>={v}"
        n=replace_one(text, r"bool late_finish=o\.turn>=(\d+)", f)
        return n, "allow late finisher 25 turns earlier"
    if key in ("doom_more_sensitive","doom_less_sensitive"):
        delta=-2 if key=="doom_more_sensitive" else 2
        def f(m):
            v=max(18,min(36,int(m.group(1))+delta))
            return f"(doom_eta_now<=6?15:{v})/100"
        n=replace_one(text, r"\(doom_eta_now<=6\?15:(\d+)\)/100", f)
        desc="lower DoomGuard concentration floor by 2pp" if delta<0 else "raise DoomGuard concentration floor by 2pp"
        return n, desc
    if key == "doom_eta_wider":
        def f(m):
            v=min(15,int(m.group(1))+1)
            return f"doom_regular&&doom_eta_now<={v}&&"
        n=replace_one(text, r"doom_regular&&doom_eta_now<=(\d+)&&", f)
        return n, "widen DoomGuard detection by one ETA step"
    if key == "concentration_more":
        def f(m):
            v=min(.70,float(m.group(1))+.02)
            return "top3_share<"+fmt2(v)
        n=replace_one(text, r"top3_share<(\.\d+)", f)
        return n, "request concentration at a 2pp higher top-3 share"
    if key == "early_expansion":
        pat=r"production_==ProductionState::SOFT_DEFICIT\?(\.\d+):\(\(!enemy_seen&&o\.turn<=250\)\?(\.\d+):(\.\d+)\)"
        m=re.search(pat,text)
        if m:
            early=min(.48,float(m.group(2))+.01)
            rep=f"production_==ProductionState::SOFT_DEFICIT?{m.group(1)}:((!enemy_seen&&o.turn<=250)?{fmt2(early)}:{m.group(3)})"
            return text[:m.start()]+rep+text[m.end():], "increase HEALTHY pre-contact expansion share by 1pp through t250"
        pat2=r"production_==ProductionState::SOFT_DEFICIT\?(\.\d+):(\.\d+)"
        m=re.search(pat2,text)
        if m:
            base=float(m.group(2)); early=min(.48,base+.02)
            rep=f"production_==ProductionState::SOFT_DEFICIT?{m.group(1)}:((!enemy_seen&&o.turn<=250)?{fmt2(early)}:{m.group(2)})"
            return text[:m.start()]+rep+text[m.end():], "add +2pp HEALTHY pre-contact expansion share through t250"
        return None, ""
    if key == "soft_expansion":
        def f(m):
            v=min(.56,float(m.group(1))+.01)
            return "ProductionState::SOFT_DEFICIT?"+fmt2(v)+":"
        n=replace_one(text, r"ProductionState::SOFT_DEFICIT\?(\.\d+):", f)
        return n, "increase SOFT_DEFICIT expansion share by 1pp"
    if key == "search_less_precontact":
        def f(m):
            v=max(.12,float(m.group(1))-.01)
            return f"!enemy_seen?{fmt2(v)}:{m.group(2)}"
        n=replace_one(text, r"!enemy_seen\?(\.\d+):(\.\d+)", f)
        return n, "reduce pre-contact search share by 1pp"
    if key == "castle_c1_earlier":
        m=re.search(r"forecast\(o\.turn,(\d+),cost1",text)
        if not m: return None,""
        old=int(m.group(1)); new=max(130,old-5)
        out=text.replace(f"forecast(o.turn,{old},cost1",f"forecast(o.turn,{new},cost1",1)
        out=out.replace(f"o.turn>{old}&&castle_build_[0]<0",f"o.turn>{new}&&castle_build_[0]<0",1)
        return (out if out!=text else None), "move first-castle funding deadline 5 turns earlier"
    return None, ""

def diagnose(metrics):
    notes=[]
    if metrics.get("land200",0) and metrics["land200"]<55: notes.append("weak early land growth")
    if metrics.get("picker_starts",0)<.5: notes.append("picker rarely starts")
    if metrics.get("picker_aborts",0)>metrics.get("picker_completions",0): notes.append("picker abort rate exceeds completions")
    if metrics.get("muster_windows",0)>1 and metrics.get("muster_attack",0)<.5: notes.append("late muster harvests but fails to launch")
    if metrics.get("doom_starts",0)<.25 and metrics.get("threats",0)>1: notes.append("DoomGuard misses observed incoming threats")
    if metrics.get("passes",0)>8: notes.append("too many pass actions")
    if metrics.get("c1_missing_rate",0)>=.34: notes.append("first castle frequently missed")
    return notes or ["no single dominant signal; apply conservative concentration/tempo tuning"]

def _gh_json(endpoint):
    repo=os.environ.get("GITHUB_REPOSITORY")
    if not repo or not shutil.which("gh"):
        return None
    p=run(["gh","api","--method","GET",endpoint],capture=True,check=False)
    if p.returncode:
        raise RuntimeError(f"GitHub API check failed: {p.stderr[-1000:]}")
    return json.loads(p.stdout)

def check_actions_for_sha(sha):
    repo=os.environ.get("GITHUB_REPOSITORY")
    if not repo or not shutil.which("gh"):
        return {"checked":False,"reason":"gh unavailable outside Actions"}
    time.sleep(5)
    data=_gh_json(f"repos/{repo}/actions/runs?head_sha={sha}&per_page=50")
    runs=data.get("workflow_runs",[]) if data else []
    checks=[]
    for r in runs:
        rid=r["id"]
        deadline=time.time()+600
        while r.get("status")!="completed" and time.time()<deadline:
            time.sleep(10)
            rr=_gh_json(f"repos/{repo}/actions/runs/{rid}")
            r=rr or r
        if r.get("status")!="completed":
            raise RuntimeError(f"CI run {rid} incomplete after wait")
        conclusion=r.get("conclusion")
        if conclusion in ("failure","cancelled","timed_out","action_required","stale"):
            run(["gh","run","rerun",str(rid),"--repo",repo,"--failed"],check=False,capture=True)
            deadline=time.time()+600
            time.sleep(5)
            while time.time()<deadline:
                rr=_gh_json(f"repos/{repo}/actions/runs/{rid}")
                if rr and rr.get("status")=="completed":
                    r=rr;break
                time.sleep(10)
            conclusion=r.get("conclusion")
            if conclusion!="success":
                raise RuntimeError(f"CI run {rid} remains {conclusion} after rerun")
        jobs=_gh_json(f"repos/{repo}/actions/runs/{rid}/jobs?per_page=100")
        skipped=[j.get("name") for j in (jobs or {}).get("jobs",[]) if j.get("conclusion")=="skipped"]
        failed=[j.get("name") for j in (jobs or {}).get("jobs",[]) if j.get("conclusion") in ("failure","cancelled","timed_out")]
        if failed:
            raise RuntimeError(f"CI run {rid} has failed jobs after rerun: {failed}")
        if skipped:
            raise RuntimeError(f"CI run {rid} has unexpectedly skipped jobs: {skipped}")
        checks.append({"run_id":rid,"workflow":r.get("name"),"conclusion":conclusion,"skipped":[]})
    return {"checked":True,"runs":checks}

def commit_push_lineage(path, remote_branch, message):
    git("config","user.name","github-actions[bot]",cwd=path)
    git("config","user.email","41898282+github-actions[bot]@users.noreply.github.com",cwd=path)
    git("add",str(AGENT_REL/"main.cpp"),cwd=path)
    if git("diff","--cached","--quiet",cwd=path,check=False).returncode == 0:
        raise RuntimeError("mutation produced no staged change")
    git("commit","-m",message,cwd=path)
    git("push","origin",f"HEAD:{remote_branch}",cwd=path)
    sha=worktree_sha(path)
    check_actions_for_sha(sha)
    return sha

def ensure_initial_y(y):
    p=y/AGENT_REL/"main.cpp"
    s=p.read_text()
    marker="((!enemy_seen&&o.turn<=250)?.40:.35)"
    if marker in s:
        return False
    old="production_==ProductionState::SEVERE_DEFICIT?.62:production_==ProductionState::SOFT_DEFICIT?.45:.35"
    new="production_==ProductionState::SEVERE_DEFICIT?.62:production_==ProductionState::SOFT_DEFICIT?.45:((!enemy_seen&&o.turn<=250)?.40:.35)"
    if s.count(old)!=1:
        raise RuntimeError("cannot initialize Y: expected expansion anchor not unique")
    p.write_text(s.replace(old,new))
    build_agent(y)
    commit_push_lineage(y,YBR,"evolution Y1: healthy pre-contact expansion through t250")
    return True

def mutate_lineage(path, label, metrics, state, cycle, target=None, opponent_path=None):
    hist=state.setdefault("mutation_history",{}).setdefault(label,[])
    before=(path/AGENT_REL/"main.cpp").read_text()
    candidates=mutation_candidates(metrics,hist)
    attempts=[]
    for key in candidates:
        mutated,desc=apply_mutation(before,key)
        if not mutated:
            continue
        (path/AGENT_REL/"main.cpp").write_text(mutated)
        try:
            build_agent(path)
        except Exception as e:
            (path/AGENT_REL/"main.cpp").write_text(before)
            attempts.append({"key":key,"accepted":False,"reason":"build/test failed","error":str(e)})
            continue
        if cycle==2 and opponent_path is not None:
            olddir=Path(f"/tmp/evo-old-{label.lower()}")
            run(["git","worktree","remove","--force",str(olddir)],check=False)
            shutil.rmtree(olddir,ignore_errors=True)
            sha=worktree_sha(path)
            git("worktree","add","--detach",str(olddir),sha)
            try:
                build_agent(olddir)
                start=fresh_start(state, 7000 if label=="X" else 9000)
                wr=Path(f"/tmp/wr-target-{label.lower()}")
                shutil.rmtree(wr,ignore_errors=True);wr.mkdir(parents=True)
                oldw=wrapper(olddir/AGENT_REL/"run.sh",f"{label}OLD",wr/"old.sh")
                neww=wrapper(path/AGENT_REL/"run.sh",f"{label}NEW",wr/"new.sh")
                oppw=wrapper(opponent_path/AGENT_REL/"run.sh","OPP",wr/"opp.sh")
                old_s=bench(oldw,oppw,start,3,RESULTS/f"target-{label}-old")
                new_s=bench(neww,oppw,start,3,RESULTS/f"target-{label}-new")
                if new_s["score"] + .08 < old_s["score"]:
                    (path/AGENT_REL/"main.cpp").write_text(before)
                    build_agent(path)
                    attempts.append({"key":key,"accepted":False,"reason":"target regression","old":old_s,"new":new_s})
                    continue
                attempts.append({"key":key,"accepted":True,"description":desc,"old":old_s,"new":new_s})
            finally:
                run(["git","worktree","remove","--force",str(olddir)],check=False)
                shutil.rmtree(olddir,ignore_errors=True)
        else:
            attempts.append({"key":key,"accepted":True,"description":desc})
        hist.append(key)
        branch=XBR if label=="X" else YBR
        sha=commit_push_lineage(path,branch,f"evolution {label} cycle{cycle}: {key} - {desc}")
        return {"key":key,"description":desc,"sha":sha,"attempts":attempts}
    raise RuntimeError(f"no viable mutation for {label}; attempts={attempts}")

def make_lineages():
    fetch_all()
    x=worktree(XBR,"/tmp/evo-x",branch_mode=True)
    y=worktree(YBR,"/tmp/evo-y",branch_mode=True)
    build_agent(x); build_agent(y)
    if ensure_initial_y(y):
        fetch_all()
        y=worktree(YBR,"/tmp/evo-y",branch_mode=True)
        build_agent(y)
    return x,y

def run_h2h(x,y,state,seeds=10,name="h2h"):
    start=fresh_start(state)
    wr=Path("/tmp/evo-wrappers");shutil.rmtree(wr,ignore_errors=True);wr.mkdir(parents=True)
    xw=wrapper(x/AGENT_REL/"run.sh","X",wr/"x.sh")
    yw=wrapper(y/AGENT_REL/"run.sh","Y",wr/"y.sh")
    out=RESULTS/name
    s=bench(xw,yw,start,seeds,out)
    mx=parse_prefixed_metrics(out/"games.jsonl","X",lambda g:g.get("result")=="loss")
    my=parse_prefixed_metrics(out/"games.jsonl","Y",lambda g:g.get("result")=="win")
    return s,mx,my,start,out

def choose_loser(h2h,x,y,state,tag):
    sx=float(h2h["score"])
    if abs(sx-.5)>1e-12:
        return ("X" if sx<.5 else "Y"),None
    start=fresh_start(state,3000)
    wr=Path("/tmp/evo-tiebreak");shutil.rmtree(wr,ignore_errors=True);wr.mkdir(parents=True)
    xw=wrapper(x/AGENT_REL/"run.sh","X",wr/"x.sh")
    yw=wrapper(y/AGENT_REL/"run.sh","Y",wr/"y.sh")
    tb=bench(xw,yw,start,5,RESULTS/f"{tag}-tiebreak")
    return ("X" if tb["score"]<.5 else "Y"),tb

def prepare_opponents():
    fetch_all()
    ready=[]
    unavailable=[]
    for i,(name,ref) in enumerate(OPPONENT_REFS):
        if not ref_exists(ref):
            unavailable.append({"name":name,"ref":ref,"reason":"missing ref"})
            continue
        p=worktree(ref,f"/tmp/evo-opp-{i}",branch_mode=False)
        try:
            build_agent(p)
            ready.append((name,ref,p))
        except Exception as e:
            unavailable.append({"name":name,"ref":ref,"reason":f"build/test failed: {e}"})
            run(["git","worktree","remove","--force",str(p)],check=False)
            shutil.rmtree(p,ignore_errors=True)
    if len(ready)<5:
        raise RuntimeError(f"opponent suite too small: ready={len(ready)} unavailable={unavailable}")
    return ready,unavailable

def suite_for(label,path,opponents,state,iter_no):
    wr=Path(f"/tmp/evo-suite-wrap-{label.lower()}");shutil.rmtree(wr,ignore_errors=True);wr.mkdir(parents=True)
    cw=wrapper(path/AGENT_REL/"run.sh",label,wr/"cand.sh")
    results=[]
    all_metrics=[]
    for idx,(name,ref,opp) in enumerate(opponents):
        ow=wrapper(opp/AGENT_REL/"run.sh","OPP",wr/f"opp-{idx}.sh")
        start=fresh_start(state,10000+idx*100)
        out=RESULTS/f"cycle2/iter-{iter_no:02d}/{label}/{name}"
        s=bench(cw,ow,start,3,out)
        m=parse_prefixed_metrics(out/"games.jsonl",label,lambda g:g.get("result")=="loss")
        results.append({"name":name,"ref":ref,"start":start,"summary":s,"metrics":m})
        if m["loss_samples"]: all_metrics.append(m)
    if all_metrics:
        keys=[k for k,v in all_metrics[0].items() if isinstance(v,(int,float)) and k!="loss_samples"]
        total=sum(m["loss_samples"] for m in all_metrics)
        agg={"loss_samples":total}
        for k in keys:
            agg[k]=sum(m[k]*m["loss_samples"] for m in all_metrics)/max(1,total)
    else:
        agg={"loss_samples":0}
    worst=min(results,key=lambda r:r["summary"]["score"])
    return results,agg,worst

def cycle1(state):
    i=state["cycle1_completed"]+1
    x,y=make_lineages()
    s,mx,my,start,out=run_h2h(x,y,state,10,f"cycle1/iter-{i:02d}/h2h")
    loser,tb=choose_loser(s,x,y,state,f"cycle1/iter-{i:02d}")
    metrics=mx if loser=="X" else my
    path=x if loser=="X" else y
    mutation=mutate_lineage(path,loser,metrics,state,cycle=1)
    report={
        "cycle":1,"iteration":i,"start":start,
        "x_sha_before":worktree_sha(x) if loser!="X" else git("rev-parse","HEAD~1",cwd=x,capture=True).stdout.strip(),
        "y_sha_before":worktree_sha(y) if loser!="Y" else git("rev-parse","HEAD~1",cwd=y,capture=True).stdout.strip(),
        "h2h":s,"tiebreak":tb,"loser":loser,
        "diagnosis":diagnose(metrics),"loss_metrics":metrics,
        "mutation":mutation,
        "x_sha_after":worktree_sha(x),"y_sha_after":worktree_sha(y),
    }
    jdump(RESULTS/f"cycle1/iter-{i:02d}/report.json",report)
    state["cycle1_completed"]=i
    if i>=23:
        state["phase"]="cycle2"
        state["final_x_cycle1"]=worktree_sha(x)
        state["final_y_cycle1"]=worktree_sha(y)
    return report

def cycle2(state):
    i=state["cycle2_completed"]+1
    x,y=make_lineages()
    h,mx,my,start,out=run_h2h(x,y,state,5,f"cycle2/iter-{i:02d}/h2h")
    opponents,unavailable=prepare_opponents()
    xr,xm,xworst=suite_for("X",x,opponents,state,i)
    yr,ym,yworst=suite_for("Y",y,opponents,state,i)
    xmut=mutate_lineage(x,"X",xm,state,cycle=2,target=xworst["name"],opponent_path=next(p for n,r,p in opponents if n==xworst["name"]))
    ymut=mutate_lineage(y,"Y",ym,state,cycle=2,target=yworst["name"],opponent_path=next(p for n,r,p in opponents if n==yworst["name"]))
    report={
        "cycle":2,"iteration":i,"h2h_start":start,"h2h":h,
        "x_suite":xr,"y_suite":yr,"unavailable_opponents":unavailable,
        "x_diagnosis":diagnose(xm),"y_diagnosis":diagnose(ym),
        "x_worst":xworst["name"],"y_worst":yworst["name"],
        "x_mutation":xmut,"y_mutation":ymut,
        "x_sha_after":worktree_sha(x),"y_sha_after":worktree_sha(y)
    }
    jdump(RESULTS/f"cycle2/iter-{i:02d}/report.json",report)
    state["cycle2_completed"]=i
    if i>=32:
        state["phase"]="final"
    return report

def final_tournament(state):
    x,y=make_lineages()
    opponents,unavailable=prepare_opponents()
    bpath=Path("/tmp/evo-baseline")
    run(["git","worktree","remove","--force",str(bpath)],check=False)
    shutil.rmtree(bpath,ignore_errors=True)
    git("worktree","add","--detach",str(bpath),START_SHA)
    build_agent(bpath)
    cands=[("X",x),("Y",y),("BASE",bpath)]
    matrix=[]
    for aidx in range(len(cands)):
        for bidx in range(aidx+1,len(cands)):
            an,ap=cands[aidx];bn,bp=cands[bidx]
            wr=Path(f"/tmp/final-{an}-{bn}");shutil.rmtree(wr,ignore_errors=True);wr.mkdir(parents=True)
            aw=wrapper(ap/AGENT_REL/"run.sh",an,wr/"a.sh")
            bw=wrapper(bp/AGENT_REL/"run.sh",bn,wr/"b.sh")
            start=fresh_start(state,50000+aidx*1000+bidx*100)
            s=bench(aw,bw,start,10,RESULTS/f"final/h2h-{an}-{bn}")
            matrix.append({"a":an,"b":bn,"start":start,"summary":s})
    suite={}
    for cn,cp in cands:
        wr=Path(f"/tmp/final-suite-{cn}");shutil.rmtree(wr,ignore_errors=True);wr.mkdir(parents=True)
        cw=wrapper(cp/AGENT_REL/"run.sh",cn,wr/"cand.sh")
        rows=[]
        for idx,(name,ref,opp) in enumerate(opponents):
            ow=wrapper(opp/AGENT_REL/"run.sh","OPP",wr/f"opp-{idx}.sh")
            start=fresh_start(state,70000+idx*100)
            s=bench(cw,ow,start,5,RESULTS/f"final/{cn}/{name}")
            rows.append({"name":name,"ref":ref,"start":start,"summary":s})
        suite[cn]=rows
    robust={}
    for cn,_ in cands:
        scores=[r["summary"]["score"] for r in suite[cn]]
        robust[cn]={
            "mean_archetype_score":statistics.mean(scores),
            "min_archetype_score":min(scores),
            "raw_wins":sum(r["summary"]["W"] for r in suite[cn]),
            "draws":sum(r["summary"]["D"] for r in suite[cn]),
            "losses":sum(r["summary"]["L"] for r in suite[cn]),
            "games":sum(r["summary"]["games"] for r in suite[cn]),
            "errors":sum(r["summary"]["errors"] for r in suite[cn]),
            "illegal_actions":sum(r["summary"]["illegal_actions"] for r in suite[cn]),
        }
    eligible=[k for k,v in robust.items() if v["errors"]==0 and v["illegal_actions"]==0]
    champion=max(eligible,key=lambda k:(robust[k]["mean_archetype_score"],robust[k]["min_archetype_score"],robust[k]["raw_wins"]))
    champ_path=dict(cands)[champion]
    final_dir=ROOT/"evolution/final"
    shutil.rmtree(final_dir,ignore_errors=True);(final_dir/"juraj_v35").mkdir(parents=True)
    for f in ("main.cpp","core.hpp","build.sh","run.sh"):
        shutil.copy2(champ_path/AGENT_REL/f,final_dir/"juraj_v35"/f)
    validation={
        "start_sha":START_SHA,
        "final_x_sha":worktree_sha(x),
        "final_y_sha":worktree_sha(y),
        "champion":champion,
        "champion_sha":worktree_sha(champ_path),
        "robust":robust,
        "mutual":matrix,
        "suite":suite,
        "unavailable_opponents":unavailable,
        "cycle1_completed":state["cycle1_completed"],
        "cycle2_completed":state["cycle2_completed"],
    }
    jdump(final_dir/"VALIDATION.json",validation)
    (final_dir/"VALIDATION.txt").write_text(
        "Generals evolutionary validation\n"
        f"start_sha={START_SHA}\n"
        f"final_x_sha={validation['final_x_sha']}\n"
        f"final_y_sha={validation['final_y_sha']}\n"
        f"champion={champion}\nchampion_sha={validation['champion_sha']}\n"
        f"cycle1_completed={state['cycle1_completed']}\ncycle2_completed={state['cycle2_completed']}\n"
        f"robust={json.dumps(robust,sort_keys=True)}\n"
    )
    run(["bash",str(final_dir/"juraj_v35"/"build.sh")],cwd=final_dir/"juraj_v35")
    agent=final_dir/"juraj_v35"/"agent"
    if agent.exists(): agent.unlink()
    zip_path=final_dir/"generals_final_submission.zip"
    run(["zip","-qr",str(zip_path),"juraj_v35"],cwd=final_dir)
    sha=run(["sha256sum",str(zip_path)],cwd=final_dir,capture=True).stdout.strip()
    (final_dir/"generals_final_submission.sha256").write_text(sha+"\n")
    validation["zip_sha256"]=sha.split()[0]
    jdump(final_dir/"VALIDATION.json",validation)
    state.update({
        "phase":"done",
        "final_x_sha":validation["final_x_sha"],
        "final_y_sha":validation["final_y_sha"],
        "final_champion":champion,
        "final_champion_sha":validation["champion_sha"],
        "final_zip_sha256":validation["zip_sha256"],
        "completed_at":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),
    })
    return validation

def main():
    state=jload(STATE_PATH)
    if state.get("start_sha")!=START_SHA:
        raise RuntimeError("unexpected start SHA in state")
    phase=state.get("phase")
    if phase=="cycle1":
        cycle1(state)
    elif phase=="cycle2":
        cycle2(state)
    elif phase=="final":
        final_tournament(state)
    elif phase=="done":
        print("already complete")
        return
    else:
        raise RuntimeError(f"unknown phase {phase}")
    state["last_error"]=None
    state["retry_count"]=0
    jdump(STATE_PATH,state)
    print(json.dumps({"phase":state["phase"],"cycle1_completed":state["cycle1_completed"],
                      "cycle2_completed":state["cycle2_completed"]},sort_keys=True))

if __name__=="__main__":
    main()
