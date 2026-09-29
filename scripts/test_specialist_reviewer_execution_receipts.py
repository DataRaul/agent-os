"""Deterministic tests for P2 independent execution receipts."""

from __future__ import annotations

import copy
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILDER_PATH = ROOT / "scripts" / "build_specialist_reviewer_run_packets.py"
ASSEMBLER_PATH = ROOT / "scripts" / "assemble_specialist_reviewer_eval_result.py"


def fail(message: str) -> None:
    raise SystemExit(f"REVIEWER_RECEIPT_TEST_FAIL: {message}")


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        fail(f"could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_receipt(module, packet: dict, session_id: str) -> dict:
    return {
        "schema_version": 1,
        "suite": "specialist-reviewer-evaluation",
        "candidate_reviewer": packet["candidate_reviewer"],
        "mode": packet["mode"],
        "model_configuration_id": packet["model_configuration_id"],
        "packet_sha256": module.canonical_sha256(packet),
        "executor_session_id": session_id,
        "oracle_supplied": False,
        "peer_output_supplied": False,
        "runs": [
            {
                "case_id": run["case_id"],
                "replicate": run["replicate"],
                "finding_codes": [],
            }
            for run in packet["runs"]
        ],
    }


def expect_rejected(module, baseline_packet, baseline_receipt, reviewer_packet, reviewer_receipt, label: str) -> None:
    try:
        module.assemble(
            baseline_packet,
            baseline_receipt,
            reviewer_packet,
            reviewer_receipt,
        )
    except module.ReceiptError:
        return
    fail(f"{label} was accepted")


def main() -> None:
    builder = load_module(BUILDER_PATH, "reviewer_packet_builder")
    assembler = load_module(ASSEMBLER_PATH, "reviewer_receipt_assembler")

    baseline_packet = builder.build_packet(
        "research-validity-reviewer", "baseline", "gpt-5.6-sol-high-v1"
    )
    reviewer_packet = builder.build_packet(
        "research-validity-reviewer", "reviewer", "gpt-5.6-sol-high-v1"
    )
    baseline_receipt = make_receipt(assembler, baseline_packet, "baseline-session-001")
    reviewer_receipt = make_receipt(assembler, reviewer_packet, "reviewer-session-001")

    assembled = assembler.assemble(
        baseline_packet, baseline_receipt, reviewer_packet, reviewer_receipt
    )
    if assembled["candidate_reviewer"] != "research-validity-reviewer":
        fail("candidate mismatch")
    if assembled["reviewer_received_baseline_output"] is not False:
        fail("reviewer independence flag widened")
    if len(assembled["runs"]) != 15:
        fail("assembled result must contain 15 runs")
    if assembled["execution_receipts"]["oracle_supplied"] is not False:
        fail("assembled receipt incorrectly reports oracle access")
    if assembled["execution_receipts"]["peer_output_supplied"] is not False:
        fail("assembled receipt incorrectly reports peer-output access")

    same_session = copy.deepcopy(reviewer_receipt)
    same_session["executor_session_id"] = baseline_receipt["executor_session_id"]
    expect_rejected(
        assembler,
        baseline_packet,
        baseline_receipt,
        reviewer_packet,
        same_session,
        "same-session pair",
    )

    bad_digest = copy.deepcopy(reviewer_receipt)
    bad_digest["packet_sha256"] = "0" * 64
    expect_rejected(
        assembler,
        baseline_packet,
        baseline_receipt,
        reviewer_packet,
        bad_digest,
        "digest mismatch",
    )

    peer_leak = copy.deepcopy(reviewer_receipt)
    peer_leak["peer_output_supplied"] = True
    expect_rejected(
        assembler,
        baseline_packet,
        baseline_receipt,
        reviewer_packet,
        peer_leak,
        "peer-output leak",
    )

    oracle_leak = copy.deepcopy(baseline_receipt)
    oracle_leak["oracle_supplied"] = True
    expect_rejected(
        assembler,
        baseline_packet,
        oracle_leak,
        reviewer_packet,
        reviewer_receipt,
        "oracle leak",
    )

    wrong_run = copy.deepcopy(reviewer_receipt)
    wrong_run["runs"][0]["replicate"] = 2
    expect_rejected(
        assembler,
        baseline_packet,
        baseline_receipt,
        reviewer_packet,
        wrong_run,
        "run identity mismatch",
    )

    unknown_code = copy.deepcopy(reviewer_receipt)
    unknown_code["runs"][0]["finding_codes"] = ["NOT_IN_TAXONOMY"]
    expect_rejected(
        assembler,
        baseline_packet,
        baseline_receipt,
        reviewer_packet,
        unknown_code,
        "unknown finding code",
    )

    print("SPECIALIST_REVIEWER_EXECUTION_RECEIPT_PASS")


if __name__ == "__main__":
    main()
