from aggregate_benchmark_v41 import summarize


def row(seed, seat, result):
    return {"seed": seed, "candidate_seat": seat, "status": "ok",
            "result": result, "wall_seconds": 1.0, "turns": 100}


def test_paired_score_and_seat_split():
    rows = [
        row(30000, 0, "win"), row(30000, 1, "loss"),
        row(30001, 0, "draw"), row(30001, 1, "win"),
    ]
    report = summarize(rows, bootstrap_samples=1000, bootstrap_seed=7)
    assert report["wins"] == 2
    assert report["draws"] == 1
    assert report["losses"] == 1
    assert report["score"] == 0.625
    assert report["paired_seed_count"] == 2
    assert report["seat_split"]["0"]["score"] == 0.75
    assert report["seat_split"]["1"]["score"] == 0.5
    assert report["acceptance_ready"] is True


def test_incomplete_pair_is_not_acceptance_ready():
    report = summarize([row(30000, 0, "win")], bootstrap_samples=10)
    assert report["paired_seed_count"] == 0
    assert report["incomplete_seeds"] == [30000]
    assert report["acceptance_ready"] is False
