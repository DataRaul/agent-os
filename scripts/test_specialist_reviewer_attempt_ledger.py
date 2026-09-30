"""Deterministic tests for resumable P2 execution attempt ledgers."""

from __future__ import annotations

import copy
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER_PATH = ROOT / "scripts" / "build_specialist_reviewer_run_packets.py"
LEDGER_PATH = ROOT / "scripts" / "summarize_specialist_reviewer_attempt_ledger.py"


def fail(message: str) -> None:
    raise SystemExit(f"REVIEWER_ATTEMPT_LEDGER_TEST_FAIL: {message}")


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        fail(f"could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def completed_attempt(packet: dict, index: int, attempt_id: str, session_id: str) -> dict:
    run = packet["runs"][index]
    return {
        "attempt_id": attempt_id,
        "case_id": run["case_id"],
        "replicate": run["replicate"],
        "executor_session_id": session_id,
        "model_configuration_id": packet["model_configuration_id"],
        "configuration_confirmed": True,
        "status": "COMPLETED",
        "oracle_supplied": False,
        "peer_output_supplied": False,
        "finding_codes": [],
    }


def ledger(module, packet: dict, attempts: list[dict]) -> dict:
    return {
        "schema_version": 1,
        "suite": "specialist-reviewer-evaluation",
        "candidate_reviewer": packet["candidate_reviewer"],
        "mode": packet["mode"],
        "model_configuration_id": packet["model_configuration_id"],
        "packet_sha256": module.canonical_sha256(packet),
        "oracle_supplied": False,
        "peer_output_supplied": False,
        "attempts": attempts,
    }


def expect_rejected(module, packet: dict, value: dict, contains: str) -> None:
    try:
        module.summarize(packet, value)
    except module.LedgerError as exc:
        if contains not in str(exc):
            fail(f"wrong rejection for {contains!r}: {exc}")
    else:
        fail(f"expected rejection containing: {contains}")


def main() -> None:
    builder = load_module(BUILDER_PATH, "reviewer_packet_builder")
    module = load_module(LEDGER_PATH, "reviewer_attempt_ledger")
    packet = builder.build_packet(
        "research-validity-reviewer", "baseline", "manual-p2-config-v1"
    )

    first_run = packet["runs"][0]
    interrupted = {
        "attempt_id": "attempt-001",
        "case_id": first_run["case_id"],
        "replicate": first_run["replicate"],
        "executor_session_id": "session-interrupted-001",
        "model_configuration_id": packet["model_configuration_id"],
        "configuration_confirmed": False,
        "status": "INTERRUPTED",
        "oracle_supplied": False,
        "peer_output_supplied": False,
        "reason": "session ended before a usable final response",
    }
    partial = ledger(
        module,
        packet,
        [
            interrupted,
            completed_attempt(packet, 0, "attempt-002", "session-complete-001"),
            completed_attempt(packet, 1, "attempt-003", "session-complete-002"),
        ],
    )
    summary = module.summarize(packet, partial)
    if summary["status"] != "IN_PROGRESS":
        fail("partial ledger must remain in progress")
    if summary["completed_runs"] != 2 or summary["pending_runs"] != 13:
        fail("partial ledger progress counts incorrect")
    if summary["attempts_recorded"] != 3 or summary["interrupted_attempts"] != 1:
        fail("partial ledger attempt counts incorrect")

    try:
        module.build_receipt(packet, partial)
    except module.LedgerError as exc:
        if "pending runs" not in str(exc):
            fail(f"wrong incomplete receipt failure: {exc}")
    else:
        fail("incomplete ledger emitted a receipt")

    full_attempts = [
        completed_attempt(packet, index, f"complete-{index+1:02d}", f"session-{index+1:02d}")
        for index in range(len(packet["runs"]))
    ]
    full = ledger(module, packet, full_attempts)
    full_summary = module.summarize(packet, full)
    if full_summary["status"] != "COMPLETE" or full_summary["completed_runs"] != 15:
        fail("complete ledger summary incorrect")
    receipt = module.build_receipt(packet, full)
    if receipt["execution_layout"] != "PER_RUN_SESSIONS" or len(receipt["runs"]) != 15:
        fail("complete ledger receipt incorrect")

    duplicate_session = copy.deepcopy(full)
    duplicate_session["attempts"][1]["executor_session_id"] = duplicate_session["attempts"][0][
        "executor_session_id"
    ]
    expect_rejected(module, packet, duplicate_session, "session reused")

    after_complete = copy.deepcopy(full)
    run = packet["runs"][0]
    after_complete["attempts"].append(
        {
            "attempt_id": "late-rerun",
            "case_id": run["case_id"],
            "replicate": run["replicate"],
            "executor_session_id": "late-session",
            "model_configuration_id": packet["model_configuration_id"],
            "configuration_confirmed": False,
            "status": "INTERRUPTED",
            "oracle_supplied": False,
            "peer_output_supplied": False,
            "reason": "should never be reached after completion",
        }
    )
    expect_rejected(module, packet, after_complete, "already completed")

    unconfirmed = copy.deepcopy(full)
    unconfirmed["attempts"][0]["configuration_confirmed"] = False
    expect_rejected(module, packet, unconfirmed, "without confirmed configuration")

    bad_interrupted = copy.deepcopy(partial)
    bad_interrupted["attempts"][0]["finding_codes"] = []
    expect_rejected(module, packet, bad_interrupted, "must not declare finding_codes")

    oracle_leak = copy.deepcopy(full)
    oracle_leak["attempts"][0]["oracle_supplied"] = True
    expect_rejected(module, packet, oracle_leak, "oracle_supplied=false")

    bad_code = copy.deepcopy(full)
    bad_code["attempts"][0]["finding_codes"] = ["NOT_IN_TAXONOMY"]
    expect_rejected(module, packet, bad_code, "finding_codes invalid")

    print("SPECIALIST_REVIEWER_ATTEMPT_LEDGER_PASS")


if __name__ == "__main__":
    main()
