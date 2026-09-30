"""Deterministic operations for manual P2 specialist-reviewer execution.

This utility is oracle-free. It initializes append-only ledgers, imports bounded attempt
records, reports the exact next pending run, validates baseline/reviewer session
separation, and summarizes multi-candidate progress. It never executes or scores a model.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
LEDGER_MODULE_PATH = ROOT / "scripts" / "summarize_specialist_reviewer_attempt_ledger.py"
EXPECTED_CANDIDATES = {
    "research-validity-reviewer",
    "evidence-provenance-reviewer",
    "runtime-postcondition-verifier",
}


class OperationsError(ValueError):
    pass


def _load_ledger_module():
    spec = importlib.util.spec_from_file_location("reviewer_attempt_ledger", LEDGER_MODULE_PATH)
    if spec is None or spec.loader is None:
        raise OperationsError("could not load attempt-ledger validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise OperationsError(f"missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise OperationsError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise OperationsError(f"{path} must contain a JSON object")
    return value


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def init_ledger(packet: dict) -> dict:
    module = _load_ledger_module()
    module.validate_packet(packet)
    return {
        "schema_version": 1,
        "suite": "specialist-reviewer-evaluation",
        "candidate_reviewer": packet["candidate_reviewer"],
        "mode": packet["mode"],
        "model_configuration_id": packet["model_configuration_id"],
        "packet_sha256": module.canonical_sha256(packet),
        "oracle_supplied": False,
        "peer_output_supplied": False,
        "attempts": [],
    }


def _load_attempt_records(path: Path) -> list[dict]:
    value = load_json(path)
    if "attempts" in value:
        attempts = value["attempts"]
    elif "attempt" in value:
        attempts = [value["attempt"]]
    else:
        attempts = [value]
    if not isinstance(attempts, list) or any(not isinstance(item, dict) for item in attempts):
        raise OperationsError("attempt import must contain an object or an attempts array")
    return attempts


def import_attempts(packet: dict, ledger: dict, records: Iterable[dict]) -> dict:
    module = _load_ledger_module()
    candidate = json.loads(json.dumps(ledger))
    attempts = candidate.get("attempts")
    if not isinstance(attempts, list):
        raise OperationsError("ledger attempts must be an array")
    attempts.extend(records)
    try:
        module.summarize(packet, candidate)
    except module.LedgerError as exc:
        raise OperationsError(str(exc)) from exc
    return candidate


def progress(packet: dict, ledger: dict) -> dict:
    module = _load_ledger_module()
    try:
        summary = module.summarize(packet, ledger)
    except module.LedgerError as exc:
        raise OperationsError(str(exc)) from exc
    next_pending = summary["missing_runs"][0] if summary["missing_runs"] else None
    return {
        **summary,
        "next_pending_run": next_pending,
        "receipt_ready": summary["status"] == "COMPLETE",
    }


def _attempt_sessions(ledger: dict) -> set[str]:
    attempts = ledger.get("attempts")
    if not isinstance(attempts, list):
        raise OperationsError("ledger attempts must be an array")
    sessions: set[str] = set()
    for position, attempt in enumerate(attempts, start=1):
        if not isinstance(attempt, dict):
            raise OperationsError(f"attempt {position} must be an object")
        session = attempt.get("executor_session_id")
        if not isinstance(session, str) or not session.strip():
            raise OperationsError(f"attempt {position} executor_session_id must be non-empty")
        sessions.add(session)
    return sessions


def validate_pair(
    baseline_packet: dict,
    baseline_ledger: dict,
    reviewer_packet: dict,
    reviewer_ledger: dict,
) -> dict:
    if baseline_packet.get("mode") != "baseline":
        raise OperationsError("baseline packet mode must equal baseline")
    if reviewer_packet.get("mode") != "reviewer":
        raise OperationsError("reviewer packet mode must equal reviewer")
    if baseline_packet.get("candidate_reviewer") != reviewer_packet.get("candidate_reviewer"):
        raise OperationsError("baseline/reviewer candidate mismatch")
    if baseline_packet.get("model_configuration_id") != reviewer_packet.get("model_configuration_id"):
        raise OperationsError("baseline/reviewer model_configuration_id mismatch")

    baseline_progress = progress(baseline_packet, baseline_ledger)
    reviewer_progress = progress(reviewer_packet, reviewer_ledger)
    overlap = sorted(_attempt_sessions(baseline_ledger) & _attempt_sessions(reviewer_ledger))
    if overlap:
        raise OperationsError(
            "baseline/reviewer executor sessions must be disjoint: " + ", ".join(overlap)
        )

    ready = (
        baseline_progress["status"] == "COMPLETE"
        and reviewer_progress["status"] == "COMPLETE"
    )
    return {
        "schema_version": 1,
        "suite": "specialist-reviewer-evaluation",
        "candidate_reviewer": baseline_packet["candidate_reviewer"],
        "model_configuration_id": baseline_packet["model_configuration_id"],
        "baseline": baseline_progress,
        "reviewer": reviewer_progress,
        "session_sets_disjoint": True,
        "pre_score_ready": ready,
        "pre_score_checklist": {
            "both_packets_complete": ready,
            "matching_model_configuration": True,
            "baseline_reviewer_sessions_disjoint": True,
            "oracle_supplied": False,
            "peer_output_supplied": False,
            "scoring_oracle_read": False,
        },
    }


def overall_manifest(entries: list[tuple[dict, dict, dict, dict]]) -> dict:
    pairs = [
        validate_pair(baseline_packet, baseline_ledger, reviewer_packet, reviewer_ledger)
        for baseline_packet, baseline_ledger, reviewer_packet, reviewer_ledger in entries
    ]
    candidates = [item["candidate_reviewer"] for item in pairs]
    if len(candidates) != len(set(candidates)):
        raise OperationsError("duplicate candidate pair in overall manifest")
    unexpected = set(candidates) - EXPECTED_CANDIDATES
    if unexpected:
        raise OperationsError("unexpected candidate(s): " + ", ".join(sorted(unexpected)))

    total_runs = sum(
        pair[mode]["total_runs"]
        for pair in pairs
        for mode in ("baseline", "reviewer")
    )
    completed_runs = sum(
        pair[mode]["completed_runs"]
        for pair in pairs
        for mode in ("baseline", "reviewer")
    )
    attempts_recorded = sum(
        pair[mode]["attempts_recorded"]
        for pair in pairs
        for mode in ("baseline", "reviewer")
    )
    status = "COMPLETE" if completed_runs == total_runs and len(pairs) == 3 else "IN_PROGRESS"
    next_pending: list[dict] = []
    for pair in pairs:
        for mode in ("baseline", "reviewer"):
            pending = pair[mode]["next_pending_run"]
            if pending is not None:
                next_pending.append(
                    {
                        "candidate_reviewer": pair["candidate_reviewer"],
                        "mode": mode,
                        **pending,
                    }
                )

    return {
        "schema_version": 1,
        "suite": "specialist-reviewer-evaluation",
        "status": status,
        "candidate_pairs_present": len(pairs),
        "required_candidate_pairs": 3,
        "total_runs": total_runs,
        "required_total_runs": 90,
        "completed_runs": completed_runs,
        "pending_runs": total_runs - completed_runs,
        "attempts_recorded": attempts_recorded,
        "next_pending_runs": next_pending,
        "pre_score_ready": status == "COMPLETE"
        and set(candidates) == EXPECTED_CANDIDATES
        and total_runs == 90
        and all(pair["pre_score_ready"] for pair in pairs),
        "pairs": pairs,
    }


def _load_pair(paths: list[str]) -> tuple[dict, dict, dict, dict]:
    if len(paths) != 4:
        raise OperationsError("--pair requires BASE_PACKET BASE_LEDGER REVIEWER_PACKET REVIEWER_LEDGER")
    return tuple(load_json(Path(path)) for path in paths)  # type: ignore[return-value]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    init_parser = sub.add_parser("init-ledger")
    init_parser.add_argument("packet", type=Path)
    init_parser.add_argument("output", type=Path)

    import_parser = sub.add_parser("import-attempts")
    import_parser.add_argument("packet", type=Path)
    import_parser.add_argument("ledger", type=Path)
    import_parser.add_argument("records", type=Path)

    status_parser = sub.add_parser("status")
    status_parser.add_argument("packet", type=Path)
    status_parser.add_argument("ledger", type=Path)

    receipt_parser = sub.add_parser("emit-receipt")
    receipt_parser.add_argument("packet", type=Path)
    receipt_parser.add_argument("ledger", type=Path)

    pair_parser = sub.add_parser("validate-pair")
    pair_parser.add_argument("baseline_packet", type=Path)
    pair_parser.add_argument("baseline_ledger", type=Path)
    pair_parser.add_argument("reviewer_packet", type=Path)
    pair_parser.add_argument("reviewer_ledger", type=Path)

    overall_parser = sub.add_parser("overall")
    overall_parser.add_argument(
        "--pair",
        nargs=4,
        action="append",
        metavar=("BASE_PACKET", "BASE_LEDGER", "REVIEWER_PACKET", "REVIEWER_LEDGER"),
        required=True,
    )

    args = parser.parse_args()

    try:
        if args.command == "init-ledger":
            packet = load_json(args.packet)
            value = init_ledger(packet)
            write_json(args.output, value)
            result = value
        elif args.command == "import-attempts":
            packet = load_json(args.packet)
            ledger = load_json(args.ledger)
            records = _load_attempt_records(args.records)
            result = import_attempts(packet, ledger, records)
            write_json(args.ledger, result)
        elif args.command == "status":
            result = progress(load_json(args.packet), load_json(args.ledger))
        elif args.command == "emit-receipt":
            packet = load_json(args.packet)
            ledger = load_json(args.ledger)
            module = _load_ledger_module()
            try:
                result = module.build_receipt(packet, ledger)
            except module.LedgerError as exc:
                raise OperationsError(str(exc)) from exc
        elif args.command == "validate-pair":
            result = validate_pair(
                load_json(args.baseline_packet),
                load_json(args.baseline_ledger),
                load_json(args.reviewer_packet),
                load_json(args.reviewer_ledger),
            )
        else:
            result = overall_manifest([_load_pair(paths) for paths in args.pair])
    except OperationsError as exc:
        raise SystemExit(f"REVIEWER_EXECUTION_OPS_FAIL: {exc}") from None

    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
