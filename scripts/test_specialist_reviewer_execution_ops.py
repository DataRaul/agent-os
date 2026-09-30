"""Deterministic tests for P2 manual execution operations."""

from __future__ import annotations

import copy
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER_PATH = ROOT / "scripts" / "build_specialist_reviewer_run_packets.py"
OPS_PATH = ROOT / "scripts" / "specialist_reviewer_execution_ops.py"


def fail(message: str) -> None:
    raise SystemExit(f"REVIEWER_EXECUTION_OPS_TEST_FAIL: {message}")


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        fail(f"could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def completed_attempt(packet: dict, index: int, prefix: str) -> dict:
    run = packet["runs"][index]
    return {
        "attempt_id": f"{prefix}-attempt-{index + 1:02d}",
        "case_id": run["case_id"],
        "replicate": run["replicate"],
        "executor_session_id": f"{prefix}-session-{index + 1:02d}",
        "model_configuration_id": packet["model_configuration_id"],
        "configuration_confirmed": True,
        "status": "COMPLETED",
        "oracle_supplied": False,
        "peer_output_supplied": False,
        "finding_codes": [],
    }


def full_ledger(ops, packet: dict, prefix: str) -> dict:
    ledger = ops.init_ledger(packet)
    return ops.import_attempts(
        packet,
        ledger,
        [completed_attempt(packet, index, prefix) for index in range(len(packet["runs"]))],
    )


def expect_error(fn, contains: str) -> None:
    try:
        fn()
    except Exception as exc:
        if contains not in str(exc):
            fail(f"wrong failure for {contains!r}: {exc}")
    else:
        fail(f"expected failure containing: {contains}")


def main() -> None:
    builder = load_module(BUILDER_PATH, "reviewer_packet_builder")
    ops = load_module(OPS_PATH, "reviewer_execution_ops")
    config = "manual-p2-config-v1"

    baseline = builder.build_packet("research-validity-reviewer", "baseline", config)
    reviewer = builder.build_packet("research-validity-reviewer", "reviewer", config)
    baseline_ledger = ops.init_ledger(baseline)
    reviewer_ledger = ops.init_ledger(reviewer)

    initial = ops.progress(baseline, baseline_ledger)
    if initial["completed_runs"] != 0 or initial["pending_runs"] != 15:
        fail("empty ledger progress mismatch")
    if initial["next_pending_run"] != {
        "case_id": baseline["runs"][0]["case_id"],
        "replicate": baseline["runs"][0]["replicate"],
    }:
        fail("empty ledger next pending run mismatch")

    interrupted = {
        "attempt_id": "baseline-interrupted-001",
        "case_id": baseline["runs"][0]["case_id"],
        "replicate": baseline["runs"][0]["replicate"],
        "executor_session_id": "baseline-interrupted-session-001",
        "model_configuration_id": config,
        "configuration_confirmed": False,
        "status": "INTERRUPTED",
        "oracle_supplied": False,
        "peer_output_supplied": False,
        "reason": "manual chat ended before a usable final response",
    }
    baseline_ledger = ops.import_attempts(baseline, baseline_ledger, [interrupted])
    baseline_ledger = ops.import_attempts(
        baseline, baseline_ledger, [completed_attempt(baseline, 0, "baseline-retry")]
    )
    resumed = ops.progress(baseline, baseline_ledger)
    if resumed["completed_runs"] != 1 or resumed["attempts_recorded"] != 2:
        fail("interrupted attempt was not preserved")
    if resumed["interrupted_attempts"] != 1:
        fail("interrupted count mismatch")

    duplicate = copy.deepcopy(baseline_ledger)
    duplicate["attempts"].append(
        {
            **completed_attempt(baseline, 1, "duplicate"),
            "executor_session_id": "baseline-retry-session-01",
        }
    )
    expect_error(lambda: ops.progress(baseline, duplicate), "session reused")

    complete_baseline = full_ledger(ops, baseline, "pair-baseline")
    complete_reviewer = full_ledger(ops, reviewer, "pair-reviewer")
    pair = ops.validate_pair(baseline, complete_baseline, reviewer, complete_reviewer)
    if not pair["pre_score_ready"] or not pair["session_sets_disjoint"]:
        fail("complete disjoint pair must be pre-score ready")

    overlap_reviewer = copy.deepcopy(complete_reviewer)
    overlap_reviewer["attempts"][0]["executor_session_id"] = complete_baseline["attempts"][0][
        "executor_session_id"
    ]
    expect_error(
        lambda: ops.validate_pair(baseline, complete_baseline, reviewer, overlap_reviewer),
        "must be disjoint",
    )

    wrong_config_reviewer = builder.build_packet(
        "research-validity-reviewer", "reviewer", "different-config"
    )
    wrong_config_ledger = full_ledger(ops, wrong_config_reviewer, "wrong-config")
    expect_error(
        lambda: ops.validate_pair(
            baseline, complete_baseline, wrong_config_reviewer, wrong_config_ledger
        ),
        "model_configuration_id mismatch",
    )

    entries = []
    for candidate in sorted(ops.EXPECTED_CANDIDATES):
        base_packet = builder.build_packet(candidate, "baseline", config)
        review_packet = builder.build_packet(candidate, "reviewer", config)
        entries.append(
            (
                base_packet,
                full_ledger(ops, base_packet, f"{candidate}-baseline"),
                review_packet,
                full_ledger(ops, review_packet, f"{candidate}-reviewer"),
            )
        )
    overall = ops.overall_manifest(entries)
    if overall["status"] != "COMPLETE" or overall["completed_runs"] != 90:
        fail("overall complete progress mismatch")
    if overall["required_total_runs"] != 90 or not overall["pre_score_ready"]:
        fail("overall manifest must require and complete exactly 90 runs")
    if overall["next_pending_runs"]:
        fail("complete overall manifest must have no pending runs")

    partial_entries = copy.deepcopy(entries)
    partial_entries[0][1]["attempts"].pop()
    partial = ops.overall_manifest(partial_entries)
    if partial["status"] != "IN_PROGRESS" or partial["completed_runs"] != 89:
        fail("overall incomplete progress mismatch")
    if partial["pre_score_ready"]:
        fail("incomplete overall manifest must not be pre-score ready")
    if len(partial["next_pending_runs"]) != 1:
        fail("incomplete overall manifest must identify exact next pending run")

    print("REVIEWER_EXECUTION_OPS_TEST_PASS")


if __name__ == "__main__":
    main()
