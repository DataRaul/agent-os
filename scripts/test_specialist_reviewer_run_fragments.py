"""Deterministic tests for P2 per-run execution fragment collection."""

from __future__ import annotations

import copy
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILDER_PATH = ROOT / "scripts" / "build_specialist_reviewer_run_packets.py"
COLLECTOR_PATH = ROOT / "scripts" / "collect_specialist_reviewer_run_fragments.py"
ASSEMBLER_PATH = ROOT / "scripts" / "assemble_specialist_reviewer_eval_result.py"


def fail(message: str) -> None:
    raise SystemExit(f"REVIEWER_FRAGMENT_TEST_FAIL: {message}")


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        fail(f"could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_fragments(module, packet: dict, prefix: str) -> list[dict]:
    digest = module.canonical_sha256(packet)
    return [
        {
            "schema_version": 1,
            "suite": "specialist-reviewer-evaluation",
            "candidate_reviewer": packet["candidate_reviewer"],
            "mode": packet["mode"],
            "model_configuration_id": packet["model_configuration_id"],
            "packet_sha256": digest,
            "case_id": run["case_id"],
            "replicate": run["replicate"],
            "executor_session_id": f"{prefix}-{index:02d}",
            "oracle_supplied": False,
            "peer_output_supplied": False,
            "finding_codes": [],
        }
        for index, run in enumerate(packet["runs"], start=1)
    ]


def expect_collect_rejected(
    module,
    packet: dict,
    fragments: list[dict],
    label: str,
) -> None:
    try:
        module.collect(packet, fragments)
    except module.FragmentError:
        return
    fail(f"{label} was accepted")


def expect_assemble_rejected(
    module,
    baseline_packet,
    baseline_receipt,
    reviewer_packet,
    reviewer_receipt,
    label: str,
) -> None:
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
    collector = load_module(COLLECTOR_PATH, "reviewer_fragment_collector")
    assembler = load_module(ASSEMBLER_PATH, "reviewer_receipt_assembler")

    baseline_packet = builder.build_packet(
        "research-validity-reviewer", "baseline", "manual-p2-config-v1"
    )
    reviewer_packet = builder.build_packet(
        "research-validity-reviewer", "reviewer", "manual-p2-config-v1"
    )
    baseline_fragments = make_fragments(collector, baseline_packet, "baseline")
    reviewer_fragments = make_fragments(collector, reviewer_packet, "reviewer")

    baseline_receipt = collector.collect(baseline_packet, baseline_fragments)
    reviewer_receipt = collector.collect(reviewer_packet, reviewer_fragments)

    if baseline_receipt["schema_version"] != 2:
        fail("collector must emit schema v2 receipts")
    if baseline_receipt["execution_layout"] != "PER_RUN_SESSIONS":
        fail("collector execution layout mismatch")
    if len(baseline_receipt["runs"]) != 15:
        fail("collector must emit all 15 packet runs")
    if len({run["executor_session_id"] for run in baseline_receipt["runs"]}) != 15:
        fail("collector must preserve 15 distinct session references")

    assembled = assembler.assemble(
        baseline_packet,
        baseline_receipt,
        reviewer_packet,
        reviewer_receipt,
    )
    receipts = assembled["execution_receipts"]
    if receipts["baseline_execution_layout"] != "PER_RUN_SESSIONS":
        fail("assembler did not preserve baseline per-run layout")
    if receipts["reviewer_execution_layout"] != "PER_RUN_SESSIONS":
        fail("assembler did not preserve reviewer per-run layout")
    if len(receipts["baseline_executor_session_ids"]) != 15:
        fail("assembler baseline session provenance incomplete")
    if len(receipts["reviewer_executor_session_ids"]) != 15:
        fail("assembler reviewer session provenance incomplete")

    missing = copy.deepcopy(baseline_fragments[:-1])
    expect_collect_rejected(
        collector,
        baseline_packet,
        missing,
        "missing fragment set",
    )

    duplicate_run = copy.deepcopy(baseline_fragments)
    duplicate_run[-1]["case_id"] = duplicate_run[0]["case_id"]
    duplicate_run[-1]["replicate"] = duplicate_run[0]["replicate"]
    expect_collect_rejected(
        collector,
        baseline_packet,
        duplicate_run,
        "duplicate fragment run",
    )

    duplicate_session = copy.deepcopy(baseline_fragments)
    duplicate_session[-1]["executor_session_id"] = duplicate_session[0][
        "executor_session_id"
    ]
    expect_collect_rejected(
        collector,
        baseline_packet,
        duplicate_session,
        "duplicate fragment session",
    )

    bad_digest = copy.deepcopy(baseline_fragments)
    bad_digest[0]["packet_sha256"] = "0" * 64
    expect_collect_rejected(
        collector,
        baseline_packet,
        bad_digest,
        "fragment digest mismatch",
    )

    oracle_leak = copy.deepcopy(baseline_fragments)
    oracle_leak[0]["oracle_supplied"] = True
    expect_collect_rejected(
        collector,
        baseline_packet,
        oracle_leak,
        "fragment oracle leak",
    )

    unknown_code = copy.deepcopy(baseline_fragments)
    unknown_code[0]["finding_codes"] = ["NOT_IN_TAXONOMY"]
    expect_collect_rejected(
        collector,
        baseline_packet,
        unknown_code,
        "fragment unknown finding code",
    )

    overlapping_reviewer = copy.deepcopy(reviewer_receipt)
    overlapping_reviewer["runs"][0]["executor_session_id"] = baseline_receipt["runs"][0][
        "executor_session_id"
    ]
    expect_assemble_rejected(
        assembler,
        baseline_packet,
        baseline_receipt,
        reviewer_packet,
        overlapping_reviewer,
        "baseline/reviewer session overlap",
    )

    duplicate_receipt_session = copy.deepcopy(reviewer_receipt)
    duplicate_receipt_session["runs"][-1]["executor_session_id"] = (
        duplicate_receipt_session["runs"][0]["executor_session_id"]
    )
    expect_assemble_rejected(
        assembler,
        baseline_packet,
        baseline_receipt,
        reviewer_packet,
        duplicate_receipt_session,
        "duplicate per-run receipt session",
    )

    print("SPECIALIST_REVIEWER_RUN_FRAGMENT_COLLECTION_PASS")


if __name__ == "__main__":
    main()
