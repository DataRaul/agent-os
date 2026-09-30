"""Assemble independently executed P2 specialist-reviewer receipts for scoring.

This module deliberately does not read the benchmark oracle. It verifies that each
result receipt is bound to the exact blinded packet that was executed and that the
baseline and reviewer executions declare disjoint sessions before producing the
combined scorer input.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ALLOWED_MODES = {"baseline", "reviewer"}
SINGLE_SESSION_SCHEMA = 1
PER_RUN_SESSION_SCHEMA = 2
PER_RUN_LAYOUT = "PER_RUN_SESSIONS"


class ReceiptError(ValueError):
    pass


def load_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ReceiptError(f"missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ReceiptError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ReceiptError(f"{path} must contain a JSON object")
    return data


def canonical_sha256(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _require_nonempty_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReceiptError(f"{label} must be a non-empty string")
    return value


def _validate_packet(packet: dict, expected_mode: str) -> None:
    if packet.get("schema_version") != 1:
        raise ReceiptError(f"{expected_mode} packet schema_version must equal 1")
    if packet.get("suite") != "specialist-reviewer-evaluation":
        raise ReceiptError(f"{expected_mode} packet suite mismatch")
    if packet.get("mode") != expected_mode:
        raise ReceiptError(f"expected {expected_mode} packet")
    _require_nonempty_string(packet.get("candidate_reviewer"), "candidate_reviewer")
    _require_nonempty_string(packet.get("model_configuration_id"), "model_configuration_id")

    contract = packet.get("independence_contract")
    if not isinstance(contract, dict):
        raise ReceiptError(f"{expected_mode} packet independence contract missing")
    for key in ("oracle_supplied", "peer_output_supplied", "hidden_reasoning_requested"):
        if contract.get(key) is not False:
            raise ReceiptError(f"{expected_mode} packet independence violation: {key}")
    if contract.get("same_model_configuration_required_for_pair") is not True:
        raise ReceiptError(f"{expected_mode} packet configuration-pair requirement missing")

    output = packet.get("output_contract")
    if not isinstance(output, dict) or output.get("format") != "finding_codes_only":
        raise ReceiptError(f"{expected_mode} packet output contract invalid")
    taxonomy = output.get("allowed_finding_codes")
    if (
        not isinstance(taxonomy, list)
        or not taxonomy
        or len(taxonomy) != len(set(taxonomy))
        or any(not isinstance(code, str) or not code for code in taxonomy)
    ):
        raise ReceiptError(f"{expected_mode} packet finding-code taxonomy invalid")

    runs = packet.get("runs")
    if not isinstance(runs, list) or not runs:
        raise ReceiptError(f"{expected_mode} packet runs must be non-empty")
    seen: set[tuple[str, int]] = set()
    for run in runs:
        if not isinstance(run, dict):
            raise ReceiptError(f"{expected_mode} packet run must be object")
        case_id = _require_nonempty_string(run.get("case_id"), "case_id")
        replicate = run.get("replicate")
        if not isinstance(replicate, int) or isinstance(replicate, bool) or replicate < 1:
            raise ReceiptError(f"{expected_mode} packet {case_id} replicate invalid")
        pair = (case_id, replicate)
        if pair in seen:
            raise ReceiptError(f"{expected_mode} packet duplicate run: {pair}")
        seen.add(pair)


def _validate_result_run(
    packet_run: dict,
    result_run: dict,
    taxonomy: set[str],
    expected_mode: str,
) -> None:
    if (
        result_run.get("case_id") != packet_run.get("case_id")
        or result_run.get("replicate") != packet_run.get("replicate")
    ):
        raise ReceiptError(f"{expected_mode} receipt run ordering/identity mismatch")
    codes = result_run.get("finding_codes")
    if (
        not isinstance(codes, list)
        or len(codes) != len(set(codes))
        or any(not isinstance(code, str) or code not in taxonomy for code in codes)
    ):
        raise ReceiptError(
            f"{expected_mode} receipt {packet_run['case_id']} finding_codes invalid"
        )
    for key in ("tool_calls", "latency_ms"):
        value = result_run.get(key)
        if value is not None and (
            not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0
        ):
            raise ReceiptError(
                f"{expected_mode} receipt {packet_run['case_id']} {key} invalid"
            )


def _validate_receipt(
    packet: dict,
    receipt: dict,
    expected_mode: str,
) -> tuple[str, list[str]]:
    schema_version = receipt.get("schema_version")
    if schema_version not in {SINGLE_SESSION_SCHEMA, PER_RUN_SESSION_SCHEMA}:
        raise ReceiptError(f"{expected_mode} receipt schema_version must equal 1 or 2")
    if receipt.get("suite") != "specialist-reviewer-evaluation":
        raise ReceiptError(f"{expected_mode} receipt suite mismatch")
    if receipt.get("mode") != expected_mode:
        raise ReceiptError(f"expected {expected_mode} receipt")
    for key in ("candidate_reviewer", "model_configuration_id"):
        if receipt.get(key) != packet.get(key):
            raise ReceiptError(f"{expected_mode} receipt {key} mismatch")
    if receipt.get("packet_sha256") != canonical_sha256(packet):
        raise ReceiptError(f"{expected_mode} receipt packet digest mismatch")

    if receipt.get("oracle_supplied") is not False:
        raise ReceiptError(f"{expected_mode} receipt must declare oracle_supplied=false")
    if receipt.get("peer_output_supplied") is not False:
        raise ReceiptError(f"{expected_mode} receipt must declare peer_output_supplied=false")

    packet_runs = packet["runs"]
    receipt_runs = receipt.get("runs")
    if not isinstance(receipt_runs, list) or len(receipt_runs) != len(packet_runs):
        raise ReceiptError(f"{expected_mode} receipt run count mismatch")

    taxonomy = set(packet["output_contract"]["allowed_finding_codes"])
    session_ids: list[str] = []
    if schema_version == SINGLE_SESSION_SCHEMA:
        if "execution_layout" in receipt:
            raise ReceiptError(
                f"{expected_mode} schema v1 receipt must not declare execution_layout"
            )
        session_id = _require_nonempty_string(
            receipt.get("executor_session_id"), "executor_session_id"
        )
        session_ids = [session_id]
    else:
        if receipt.get("execution_layout") != PER_RUN_LAYOUT:
            raise ReceiptError(
                f"{expected_mode} schema v2 receipt execution_layout must equal {PER_RUN_LAYOUT}"
            )
        if "executor_session_id" in receipt:
            raise ReceiptError(
                f"{expected_mode} schema v2 receipt must not declare top-level executor_session_id"
            )

    for packet_run, result_run in zip(packet_runs, receipt_runs):
        if not isinstance(result_run, dict):
            raise ReceiptError(f"{expected_mode} receipt run must be object")
        _validate_result_run(packet_run, result_run, taxonomy, expected_mode)
        if schema_version == PER_RUN_SESSION_SCHEMA:
            session_ids.append(
                _require_nonempty_string(
                    result_run.get("executor_session_id"),
                    f"{expected_mode} receipt {packet_run['case_id']} executor_session_id",
                )
            )
        elif "executor_session_id" in result_run:
            raise ReceiptError(
                f"{expected_mode} schema v1 receipt run must not declare executor_session_id"
            )

    if schema_version == PER_RUN_SESSION_SCHEMA and len(session_ids) != len(set(session_ids)):
        raise ReceiptError(
            f"{expected_mode} per-run receipt must use a distinct executor session for every run"
        )

    layout = (
        "SINGLE_PACKET_SESSION"
        if schema_version == SINGLE_SESSION_SCHEMA
        else PER_RUN_LAYOUT
    )
    return layout, session_ids


def assemble(
    baseline_packet: dict,
    baseline_receipt: dict,
    reviewer_packet: dict,
    reviewer_receipt: dict,
) -> dict:
    _validate_packet(baseline_packet, "baseline")
    _validate_packet(reviewer_packet, "reviewer")

    for key in ("candidate_reviewer", "model_configuration_id"):
        if baseline_packet.get(key) != reviewer_packet.get(key):
            raise ReceiptError(f"packet pair {key} mismatch")
    if baseline_packet.get("runs") != reviewer_packet.get("runs"):
        raise ReceiptError("baseline/reviewer packet runs differ")
    if (
        baseline_packet["output_contract"]["allowed_finding_codes"]
        != reviewer_packet["output_contract"]["allowed_finding_codes"]
    ):
        raise ReceiptError("baseline/reviewer packet taxonomies differ")

    baseline_layout, baseline_sessions = _validate_receipt(
        baseline_packet, baseline_receipt, "baseline"
    )
    reviewer_layout, reviewer_sessions = _validate_receipt(
        reviewer_packet, reviewer_receipt, "reviewer"
    )

    if set(baseline_sessions) & set(reviewer_sessions):
        raise ReceiptError(
            "baseline and reviewer receipts must use disjoint executor sessions"
        )

    combined_runs: list[dict] = []
    for baseline_run, reviewer_run in zip(
        baseline_receipt["runs"], reviewer_receipt["runs"]
    ):
        combined = {
            "case_id": baseline_run["case_id"],
            "replicate": baseline_run["replicate"],
            "baseline_finding_codes": baseline_run["finding_codes"],
            "reviewer_finding_codes": reviewer_run["finding_codes"],
        }
        if "tool_calls" in baseline_run:
            combined["baseline_tool_calls"] = baseline_run["tool_calls"]
        if "tool_calls" in reviewer_run:
            combined["reviewer_tool_calls"] = reviewer_run["tool_calls"]
        if "latency_ms" in baseline_run:
            combined["baseline_latency_ms"] = baseline_run["latency_ms"]
        if "latency_ms" in reviewer_run:
            combined["reviewer_latency_ms"] = reviewer_run["latency_ms"]
        combined_runs.append(combined)

    execution_receipts = {
        "baseline_packet_sha256": baseline_receipt["packet_sha256"],
        "reviewer_packet_sha256": reviewer_receipt["packet_sha256"],
        "baseline_execution_layout": baseline_layout,
        "reviewer_execution_layout": reviewer_layout,
        "baseline_executor_session_ids": baseline_sessions,
        "reviewer_executor_session_ids": reviewer_sessions,
        "oracle_supplied": False,
        "peer_output_supplied": False,
    }
    if len(baseline_sessions) == 1:
        execution_receipts["baseline_executor_session_id"] = baseline_sessions[0]
    if len(reviewer_sessions) == 1:
        execution_receipts["reviewer_executor_session_id"] = reviewer_sessions[0]

    return {
        "schema_version": 1,
        "suite": "specialist-reviewer-evaluation",
        "candidate_reviewer": baseline_packet["candidate_reviewer"],
        "model_configuration_id": baseline_packet["model_configuration_id"],
        "reviewer_received_baseline_output": False,
        "execution_receipts": execution_receipts,
        "runs": combined_runs,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline_packet", type=Path)
    parser.add_argument("baseline_receipt", type=Path)
    parser.add_argument("reviewer_packet", type=Path)
    parser.add_argument("reviewer_receipt", type=Path)
    args = parser.parse_args()

    try:
        result = assemble(
            load_json(args.baseline_packet),
            load_json(args.baseline_receipt),
            load_json(args.reviewer_packet),
            load_json(args.reviewer_receipt),
        )
    except ReceiptError as exc:
        raise SystemExit(f"REVIEWER_RECEIPT_FAIL: {exc}") from None

    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
