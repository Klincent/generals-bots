#!/usr/bin/env python3
"""Compare exact-e50123 and candidate action traces against one fixed opponent."""

import argparse
import concurrent.futures
import json
import os
import signal
import subprocess
import sys
import tempfile
import threading
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RUNNING = set()
RUNNING_LOCK = threading.Lock()


class MatchTimeout(RuntimeError):
    pass


def stop_process(proc):
    if proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
        proc.wait(timeout=5)
    except (ProcessLookupError, subprocess.TimeoutExpired):
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait()


def stop_all():
    with RUNNING_LOCK:
        processes = list(RUNNING)
    for proc in processes:
        stop_process(proc)


def run_match(agents, seed, trace, timeout, label):
    env = os.environ.copy()
    env["V35_PICKER_ENABLED"] = "0"
    env["JURAJ_RNG_SEED"] = str((seed * 0x9E3779B1 + 0x35) & 0xFFFFFFFF)
    env["PYTHONPATH"] = str(ROOT)
    command = [
        sys.executable, str(ROOT / "competition/matchup.py"),
        *(str(agent.resolve()) for agent in agents),
        "--mode", "competition", "--seed", str(seed),
        "--action-trace-json", str(trace), "--skip-build",
    ]
    proc = subprocess.Popen(
        command, cwd=ROOT, env=env, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True,
    )
    with RUNNING_LOCK:
        RUNNING.add(proc)
    try:
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired as error:
            stop_process(proc)
            raise MatchTimeout(
                f"timeout after {timeout}s: seed={seed} {label}\ncommand={' '.join(command)}"
            ) from error
    finally:
        with RUNNING_LOCK:
            RUNNING.discard(proc)
    if proc.returncode:
        raise RuntimeError(
            f"match failed: seed={seed} {label} returncode={proc.returncode}\n"
            f"stdout:\n{stdout[-4000:]}\nstderr:\n{stderr[-8000:]}"
        )
    return json.loads(trace.read_text())


def check_game(seed, seat, candidate, baseline, output, timeout):
    opponent = baseline
    baseline_trace = output / f"baseline-{seed}-{seat}.json"
    candidate_trace = output / f"candidate-{seed}-{seat}.json"
    baseline_agents = [baseline, opponent] if seat == 0 else [opponent, baseline]
    candidate_agents = [candidate, opponent] if seat == 0 else [opponent, candidate]
    reference = run_match(baseline_agents, seed, baseline_trace, timeout,
                          f"seat={seat} implementation=baseline")
    observed = run_match(candidate_agents, seed, candidate_trace, timeout,
                         f"seat={seat} implementation=candidate")
    reference_actions = [frame["actions"][seat] for frame in reference["frames"]]
    observed_actions = [frame["actions"][seat] for frame in observed["frames"]]
    for turn, (expected, actual) in enumerate(zip(reference_actions, observed_actions)):
        if expected != actual:
            raise AssertionError(
                f"first divergence: seed={seed} seat={seat} turn={turn} "
                f"baseline={expected} candidate={actual}"
            )
    if len(reference_actions) != len(observed_actions):
        turn = min(len(reference_actions), len(observed_actions))
        expected = reference_actions[turn] if turn < len(reference_actions) else "<terminated>"
        actual = observed_actions[turn] if turn < len(observed_actions) else "<terminated>"
        raise AssertionError(
            f"first divergence: seed={seed} seat={seat} turn={turn} "
            f"baseline={expected} candidate={actual}"
        )
    return seed, seat, len(reference_actions)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--start", type=int, default=31000)
    parser.add_argument("--seeds", type=int, default=20)
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--timeout", type=int, default=600,
                        help="timeout in seconds for each full match")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.jobs < 1 or args.timeout < 1 or args.seeds < 1:
        parser.error("--jobs, --timeout, and --seeds must be positive")

    for run_sh in (args.candidate, args.baseline):
        if not run_sh.exists():
            parser.error(f"agent does not exist: {run_sh}")
        build = run_sh.parent / "build.sh"
        if build.exists():
            subprocess.run(["bash", str(build.resolve())], cwd=build.parent, check=True)

    temp = None
    if args.output is None:
        temp = tempfile.TemporaryDirectory(prefix="v35-equivalence-")
        output = Path(temp.name)
    else:
        output = args.output
        output.mkdir(parents=True, exist_ok=True)

    work = [(seed, seat) for seed in range(args.start, args.start + args.seeds)
            for seat in (0, 1)]
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs)
    futures = {
        executor.submit(check_game, seed, seat, args.candidate, args.baseline,
                        output, args.timeout): (seed, seat)
        for seed, seat in work
    }
    completed = 0
    try:
        for future in concurrent.futures.as_completed(futures):
            seed, seat = futures[future]
            try:
                _, _, turns = future.result()
            except Exception as error:
                print(f"[equivalence] FAILED seed={seed} seat={seat}: {error}",
                      file=sys.stderr, flush=True)
                stop_all()
                for pending in futures:
                    pending.cancel()
                executor.shutdown(wait=False, cancel_futures=True)
                return 1
            completed += 1
            print(f"[equivalence] PASS seed={seed} seat={seat} turns={turns} "
                  f"progress={completed}/{len(work)}", flush=True)
    finally:
        stop_all()
    executor.shutdown(wait=True)
    print(f"[equivalence] PASS all {len(work)} games; every action identical")
    if temp is not None:
        temp.cleanup()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
