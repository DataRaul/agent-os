"""Validate and summarize resumable P2 specialist-reviewer execution attempts.

The ledger is append-only evidence for manual or otherwise split execution. It keeps
interrupted/invalid attempts instead of silently replacing them, prevents reruns after
a completed case/replicate, and can emit a schema-v2 PER_RUN_SESSIONS receipt only
when every packet run has exactly one accepted completed attempt.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ALLOWED_STATUSES = {"COMPLETED", "INTERRUPTED", "INVALID"}
ATTEMPT_KEYS = {
    "attempt_id",
    "case_id",
    "replicate",
    "executor_session_id",
    "model_configuration_id",
    "configuration_confirmed",
    "status",
    "oracle_supplied",
    "peer_output_supplied",
    "finding_codes",
    "reason",
    "tool_calls",
    "latency_ms",
}


class LedgerError(ValueError):
    pass


def load_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise LedgerError(f"missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise LedgerError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise LedgerError(f"{path} must contain a JSON object")
    return data


def canonical_sha256(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def require_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LedgerError(f"{label} must be a non-empty string")
    return value


def validate_packet(packet: dict) -> None:
    if packet.get("schema_version") != 1:
        raise LedgerError("packet schema_version must equal 1")
    if packet.get("suite") != "specialist-reviewer-evaluation":
        raise LedgerError("packet suite mismatch")
    if packet.get("mode") not in {"baseline", "reviewer"}:
        raise LedgerError("packet mode invalid")
    require_string(packet.get("candidate_reviewer"), "packet candidate_reviewer")
    require_string(packet.get("model_configuration_id"), "packet model_configuration_id")

    output = packet.get("output_contract")
    if not isinstance(output, dict) or output.get("format") != "finding_codes_only":
        raise LedgerError("packet output contract invalid")
    taxonomy = output.get("allowed_finding_codes")
    if (
        not isinstance(taxonomy, list)
        or not taxonomy
        or len(taxonomy) != len(set(taxonomy))
        or any(not isinstance(code, str) or not code for code in taxonomy)
    ):
        raise LedgerError("packet finding-code taxonomy invalid")

    runs = packet.get("runs")
    if not isinstance(runs, list) or not runs:
        raise LedgerError("packet runs must be non-empty")
    seen: set[tuple[str, int]] = set()
    for run in runs:
        if not isinstance(run, dict):
            raise LedgerError("packet run must be object")
        case_id = require_string(run.get("case_id"), "packet case_id")
        replicate = run.get("replicate")
        if not isinstance(replicate, int) or isinstance(replicate, bool) or replicate < 1:
            raise LedgerError(f"packet {case_id} replicate invalid")
        key = (case_id, replicate)
        if key in seen:
            raise LedgerError(f"packet duplicate run: {key}")
        seen.add(key)


def _nonnegative_optional(value: object, label: str) -> None:
    if value is not None and (
        not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0
    ):
        raise LedgerError(f"{label} must be non-negative when present")


def _validated_state(packet: dict, ledger: dict) -> dict:
    validate_packet(packet)

    if ledger.get("schema_version") != 1:
        raise LedgerError("ledger schema_version must equal 1")
    if ledger.get("suite") != "specialist-reviewer-evaluation":
        raise LedgerError("ledger suite mismatch")
    for key in ("candidate_reviewer", "mode", "model_configuration_id"):
        if ledger.get(key) != packet.get(key):
            raise LedgerError(f"ledger {key} mismatch")
    if ledger.get("packet_sha256") != canonical_sha256(packet):
        raise LedgerError("ledger packet digest mismatch")
    if ledger.get("oracle_supplied") is not False:
        raise LedgerError("ledger must declare oracle_supplied=false")
    if ledger.get("peer_output_supplied") is not False:
        raise LedgerError("ledger must declare peer_output_supplied=false")

    attempts = ledger.get("attempts")
    if not isinstance(attempts, list):
        raise LedgerError("ledger attempts must be an array")

    expected_order = [(run["case_id"], run["replicate"]) for run in packet["runs"]]
    expected = set(expected_order)
    taxonomy = set(packet["output_contract"]["allowed_finding_codes"])

    attempt_ids: set[str] = set()
    session_ids: set[str] = set()
    completed: dict[tuple[str, int], dict] = {}
    terminal_runs: set[tuple[str, int]] = set()
    interrupted_attempts = 0
    invalid_attempts = 0

    required = {
        "attempt_id",
        "case_id",
        "replicate",
        "executor_session_id",
        "model_configuration_id",
        "configuration_confirmed",
        "status",
        "oracle_supplied",
        "peer_output_supplied",
    }

    for position, attempt in enumerate(attempts, start=1):
        if not isinstance(attempt, dict):
            raise LedgerError(f"attempt {position} must be object")
        missing = required - set(attempt)
        extra = set(attempt) - ATTEMPT_KEYS
        if missing or extra:
            raise LedgerError(
                f"attempt {position} keys mismatch: missing={sorted(missing)} extra={sorted(extra)}"
            )

        attempt_id = require_string(attempt.get("attempt_id"), f"attempt {position} attempt_id")
        if attempt_id in attempt_ids:
            raise LedgerError(f"duplicate attempt_id: {attempt_id}")
        attempt_ids.add(attempt_id)

        case_id = require_string(attempt.get("case_id"), f"attempt {attempt_id} case_id")
        replicate = attempt.get("replicate")
        if not isinstance(replicate, int) or isinstance(replicate, bool) or replicate < 1:
            raise LedgerError(f"attempt {attempt_id} replicate invalid")
        run_key = (case_id, replicate)
        if run_key not in expected:
            raise LedgerError(f"attempt {attempt_id} run not present in packet: {run_key}")
        if run_key in terminal_runs:
            raise LedgerError(
                f"attempt {attempt_id} recorded after run already completed: {run_key}"
            )

        session_id = require_string(
            attempt.get("executor_session_id"),
            f"attempt {attempt_id} executor_session_id",
        )
        if session_id in session_ids:
            raise LedgerError(f"executor session reused across attempts: {session_id}")
        session_ids.add(session_id)

        if attempt.get("model_configuration_id") != packet["model_configuration_id"]:
            raise LedgerError(f"attempt {attempt_id} model_configuration_id mismatch")
        if not isinstance(attempt.get("configuration_confirmed"), bool):
            raise LedgerError(f"attempt {attempt_id} configuration_confirmed must be boolean")
        if attempt.get("oracle_supplied") is not False:
            raise LedgerError(f"attempt {attempt_id} must declare oracle_supplied=false")
        if attempt.get("peer_output_supplied") is not False:
            raise LedgerError(f"attempt {attempt_id} must declare peer_output_supplied=false")

        status = attempt.get("status")
        if status not in ALLOWED_STATUSES:
            raise LedgerError(f"attempt {attempt_id} invalid status: {status!r}")
        _nonnegative_optional(attempt.get("tool_calls"), f"attempt {attempt_id} tool_calls")
        _nonnegative_optional(attempt.get("latency_ms"), f"attempt {attempt_id} latency_ms")

        if status == "COMPLETED":
            if attempt.get("configuration_confirmed") is not True:
                raise LedgerError(
                    f"attempt {attempt_id} completed without confirmed configuration"
                )
            codes = attempt.get("finding_codes")
            if (
                not isinstance(codes, list)
                or len(codes) != len(set(codes))
                or any(not isinstance(code, str) or code not in taxonomy for code in codes)
            ):
                raise LedgerError(f"attempt {attempt_id} finding_codes invalid")
            if "reason" in attempt:
                raise LedgerError(f"attempt {attempt_id} completed attempt must not declare reason")
            completed[run_key] = attempt
            terminal_runs.add(run_key)
        else:
            reason = require_string(
                attempt.get("reason"),
                f"attempt {attempt_id} reason",
            )
            if "finding_codes" in attempt:
                raise LedgerError(
                    f"attempt {attempt_id} non-completed attempt must not declare finding_codes"
                )
            if status == "INTERRUPTED":
                interrupted_attempts += 1
            else:
                invalid_attempts += 1

    return {
        "expected_order": expected_order,
        "completed": completed,
        "attempts_recorded": len(attempts),
        "interrupted_attempts": interrupted_attempts,
        "invalid_attempts": invalid_attempts,
    }


def summarize(packet: dict, ledger: dict) -> dict:
    state = _validated_state(packet, ledger)
    expected_order = state["expected_order"]
    completed = state["completed"]
    missing = [
        {"case_id": case_id, "replicate": replicate}
        for case_id, replicate in expected_order
        if (case_id, replicate) not in completed
    ]
    return {
        "schema_version": 1,
        "suite": "specialist-reviewer-evaluation",
        "candidate_reviewer": packet["candidate_reviewer"],
        "mode": packet["mode"],
        "packet_sha256": canonical_sha256(packet),
        "status": "COMPLETE" if not missing else "IN_PROGRESS",
        "total_runs": len(expected_order),
        "completed_runs": len(completed),
        "pending_runs": len(missing),
        "attempts_recorded": state["attempts_recorded"],
        "interrupted_attempts": state["interrupted_attempts"],
        "invalid_attempts": state["invalid_attempts"],
        "missing_runs": missing,
    }


def build_receipt(packet: dict, ledger: dict) -> dict:
    state = _validated_state(packet, ledger)
    expected_order = state["expected_order"]
    completed = state["completed"]
    missing = [key for key in expected_order if key not in completed]
    if missing:
        raise LedgerError(
            "cannot emit receipt with pending runs: "
            + ", ".join(f"{case_id}/{replicate}" for case_id, replicate in missing)
        )

    runs: list[dict] = []
    for run_key in expected_order:
        attempt = completed[run_key]
        result = {
            "case_id": attempt["case_id"],
            "replicate": attempt["replicate"],
            "executor_session_id": attempt["executor_session_id"],
            "finding_codes": attempt["finding_codes"],
        }
        for key in ("tool_calls", "latency_ms"):
            if key in attempt:
                result[key] = attempt[key]
        runs.append(result)

    return {
        "schema_version": 2,
        "suite": "specialist-reviewer-evaluation",
        "candidate_reviewer": packet["candidate_reviewer"],
        "mode": packet["mode"],
        "model_configuration_id": packet["model_configuration_id"],
        "packet_sha256": canonical_sha256(packet),
        "execution_layout": "PER_RUN_SESSIONS",
        "oracle_supplied": False,
        "peer_output_supplied": False,
        "runs": runs,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet", type=Path)
    parser.add_argument("ledger", type=Path)
    parser.add_argument("--emit-receipt", action="store_true")
    args = parser.parse_args()

    try:
        packet = load_json(args.packet)
        ledger = load_json(args.ledger)
        result = build_receipt(packet, ledger) if args.emit_receipt else summarize(packet, ledger)
    except LedgerError as exc:
        raise SystemExit(f"REVIEWER_ATTEMPT_LEDGER_FAIL: {exc}") from None

    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
