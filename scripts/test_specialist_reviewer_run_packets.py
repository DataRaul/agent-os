"""Deterministic checks for blinded specialist reviewer run packets."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER_PATH = ROOT / "scripts" / "build_specialist_reviewer_run_packets.py"
CASES_PATH = ROOT / "benchmarks" / "specialist-reviewer-evaluation" / "cases.json"


def fail(message: str) -> None:
    raise SystemExit(f"REVIEWER_PACKET_TEST_FAIL: {message}")


def load_builder():
    spec = importlib.util.spec_from_file_location("reviewer_packet_builder", BUILDER_PATH)
    if spec is None or spec.loader is None:
        fail("could not load builder")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    source = BUILDER_PATH.read_text(encoding="utf-8")
    if "oracle.json" in source:
        fail("builder must not read oracle.json")

    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    builder = load_builder()

    for candidate, config in cases["candidates"].items():
        baseline = builder.build_packet(candidate, "baseline", "test-config")
        reviewer = builder.build_packet(candidate, "reviewer", "test-config")

        if baseline["model_configuration_id"] != reviewer["model_configuration_id"]:
            fail(f"{candidate} model configuration mismatch")
        if baseline["runs"] != reviewer["runs"]:
            fail(f"{candidate} baseline/reviewer case packets differ")
        if len(baseline["runs"]) != 15:
            fail(f"{candidate} must contain 15 runs per mode")

        observed = {(run["case_id"], run["replicate"]) for run in baseline["runs"]}
        expected_case_ids = {
            case["id"]
            for case in cases["cases"]
            if case["reviewer_candidate"] == candidate
        }
        expected = {
            (case_id, replicate)
            for case_id in expected_case_ids
            for replicate in (1, 2, 3)
        }
        if observed != expected:
            fail(f"{candidate} case/replicate coverage mismatch")

        if [item["skill_id"] for item in baseline["baseline_skills"]] != config["baseline_skills"]:
            fail(f"{candidate} baseline skill set mismatch")
        if "baseline_skills" in reviewer:
            fail(f"{candidate} reviewer packet must not inherit baseline skills")
        if reviewer.get("reviewer_received_baseline_output") is not False:
            fail(f"{candidate} reviewer baseline-output flag must be false")

        for packet in (baseline, reviewer):
            contract = packet.get("independence_contract", {})
            if contract.get("oracle_supplied") is not False:
                fail(f"{candidate} packet exposes oracle")
            if contract.get("peer_output_supplied") is not False:
                fail(f"{candidate} packet exposes peer output")
            if contract.get("hidden_reasoning_requested") is not False:
                fail(f"{candidate} packet requests hidden reasoning")
            if packet["output_contract"]["allowed_finding_codes"] != cases["finding_code_taxonomy"]:
                fail(f"{candidate} finding taxonomy mismatch")

    print("SPECIALIST_REVIEWER_RUN_PACKET_PASS")


if __name__ == "__main__":
    main()
