"""Explicit opt-in: two paid live calls using synthetic evidence and a temporary DB."""
import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server import Store, generate, PROVIDER
from core import BANK, validate_config, evaluate_trace, ValidationError
from test_core import good_trace


def main():
    if "--run" not in sys.argv:
        raise SystemExit("Use --run to authorize two live generation calls (up to four with JSON repair).")
    with tempfile.TemporaryDirectory() as folder:
        store = Store(Path(folder) / "live.sqlite3")
        learner = {"id": "S-LIVE-SYNTHETIC", "label": "Synthetic live verification",
                   "synthetic": True, "diagnostic": {k: next(iter(BANK[k]["misconception_options"]))
                                                     for k in ("D01", "D02", "D03")}}
        store.save("students", learner)
        first = generate(store, learner["id"], "live", validate_config({}))
        trace = good_trace(first)
        evaluation = evaluate_trace(first, trace)
        with store.connect() as db:
            db.execute("INSERT INTO traces VALUES (?,?,?,?)", (first["id"], 1, json.dumps(trace), json.dumps(evaluation)))
        second = generate(store, learner["id"], "live", validate_config({}))
        assert second["request"]["confirmed_evaluations"], "Round two lost evidence"
        assert second["proposal"]["evidence_refs"], "Missing AI evidence references"
        report = {"synthetic": True, "rounds": [
            {"round": p["round"], "model": p["audit"]["model"],
             "question_ids": p["proposal"]["question_ids"],
             "evidence_refs": p["proposal"]["evidence_refs"],
             "elapsed_seconds": p["audit"]["elapsed_seconds"],
             "attempts": len(p["audit"]["attempts"])} for p in (first, second)]}
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    try:
        main()
    except ValidationError as exc:
        raise SystemExit(str(exc)) from None
