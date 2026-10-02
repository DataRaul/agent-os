"""Deterministic tests for the bounded-run-integrity public capability."""

from __future__ import annotations

import copy
import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "bounded_run_integrity.py"
CASES_PATH = ROOT / "evals" / "bounded-run-integrity" / "cases.json"
SCHEMA_PATH = ROOT / "schemas" / "bounded-run-integrity-receipt.schema.json"

PUBLIC_CAPABILITY_FILES = [
    ROOT / "skills" / "bounded-run-integrity" / "SKILL.md",
    ROOT / "docs" / "BOUNDED_RUN_INTEGRITY.md",
    CASES_PATH,
    SCHEMA_PATH,
    MODULE_PATH,
]
FORBIDDEN_PROJECT_TERMS = (
    "youtube-blue-lagoon-lab",
    "culinary-recommender-app",
    "market-lab",
    "DataRaul/",
    "Knowledge Core",
)


def fail(message: str) -> None:
    raise SystemExit(f"BOUNDED_RUN_INTEGRITY_TEST_FAIL: {message}")


def load_module():
    spec = importlib.util.spec_from_file_location("bounded_run_integrity", MODULE_PATH)
    if spec is None or spec.loader is None:
        fail("could not load classifier module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_receipt_shape(receipt: dict, schema: dict) -> None:
    expected_keys = set(schema["properties"])
    if set(receipt) != expected_keys:
        fail(
            "receipt keys do not match schema properties: "
            f"missing={sorted(expected_keys - set(receipt))} "
            f"extra={sorted(set(receipt) - expected_keys)}"
        )
    if set(schema["required"]) != expected_keys:
        fail("receipt schema must require every top-level property")

    for key in (
        "schema_version",
        "contract_type",
        "capability_id",
        "capability_contract_version",
        "work_class",
        "authority_granted",
    ):
        rule = schema["properties"][key]
        if "const" in rule and receipt[key] != rule["const"]:
            fail(f"receipt constant mismatch: {key}")

    digest_re = re.compile(r"^[0-9a-f]{64}$")
    for key in (
        "context_identity_digest",
        "declared_run_contract_digest",
        "inputs_configuration_digest",
    ):
        if digest_re.fullmatch(receipt[key]) is None:
            fail(f"invalid digest in {key}")

    if receipt["final_disposition"] not in schema["properties"]["final_disposition"]["enum"]:
        fail("invalid final disposition")


def main() -> None:
    module = load_module()
    cases_doc = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    if cases_doc.get("schema_version") != 1:
        fail("eval schema_version mismatch")
    if cases_doc.get("skill") != "bounded-run-integrity":
        fail("eval skill mismatch")

    cases = cases_doc.get("cases")
    if not isinstance(cases, list) or len(cases) < 9:
        fail("expected at least nine deterministic lifecycle cases")

    observed_classes = set()
    for case in cases:
        expected = case.get("expected_disposition")
        record = case.get("record")
        if expected not in {module.PASS, module.PARTIAL, module.FAILED, module.INSUFFICIENT}:
            fail(f"{case.get('id')} invalid expected disposition")
        first = module.classify_run(record)
        second = module.classify_run(copy.deepcopy(record))
        if first != second:
            fail(f"{case.get('id')} classification is not deterministic")
        if first["final_disposition"] != expected:
            fail(
                f"{case.get('id')} expected {expected}, "
                f"got {first['final_disposition']}"
            )
        validate_receipt_shape(first, schema)
        observed_classes.add(first["final_disposition"])

    required_classes = {module.PASS, module.PARTIAL, module.FAILED, module.INSUFFICIENT}
    if observed_classes != required_classes:
        fail(f"evals do not cover all dispositions: {sorted(observed_classes)}")

    clean = cases[0]["record"]
    if module.classify_run(clean)["final_disposition"] != module.PASS:
        fail("clean case must pass")

    authority_expansion = copy.deepcopy(clean)
    authority_expansion["authority_granted"] = True
    try:
        module.classify_run(authority_expansion)
    except module.IntegrityError as exc:
        if "authority_granted=false" not in str(exc):
            fail(f"wrong authority expansion error: {exc}")
    else:
        fail("capability must reject authority_granted=true")

    ambiguous_candidate = copy.deepcopy(clean)
    ambiguous_candidate["evidence"]["observed_candidate_identity"] = None
    if module.classify_run(ambiguous_candidate)["final_disposition"] != module.INSUFFICIENT:
        fail("missing candidate binding must fail closed to insufficient evidence")

    wrong_runner = copy.deepcopy(clean)
    wrong_runner["evidence"]["observed_runner_identity"] = "other-runner"
    if module.classify_run(wrong_runner)["final_disposition"] != module.FAILED:
        fail("wrong runner binding must fail")

    wrong_run_artifact = copy.deepcopy(clean)
    wrong_run_artifact["evidence"]["artifacts"][0]["run_identity"] = "prior-run"
    if module.classify_run(wrong_run_artifact)["final_disposition"] != module.FAILED:
        fail("artifact from a different run must fail")

    green_without_work = copy.deepcopy(clean)
    green_without_work["evidence"]["expected_work_occurred"] = False
    if module.classify_run(green_without_work)["final_disposition"] != module.FAILED:
        fail("runner success without expected work must fail")

    invalid_bool = copy.deepcopy(clean)
    invalid_bool["evidence"]["runner_executed"] = 1
    try:
        module.classify_run(invalid_bool)
    except module.IntegrityError:
        pass
    else:
        fail("integer truthiness must not be accepted as boolean evidence")

    duplicate_artifact = copy.deepcopy(clean)
    duplicate_artifact["evidence"]["artifacts"].append(
        copy.deepcopy(duplicate_artifact["evidence"]["artifacts"][0])
    )
    try:
        module.classify_run(duplicate_artifact)
    except module.IntegrityError:
        pass
    else:
        fail("duplicate artifact identities must be rejected")

    empty_positive_contract = copy.deepcopy(clean)
    empty_positive_contract["contract"]["positive_postconditions"] = []
    empty_positive_contract["evidence"]["positive_postconditions"] = []
    try:
        module.classify_run(empty_positive_contract)
    except module.IntegrityError:
        pass
    else:
        fail("positive postcondition contract must not be empty")

    for path in PUBLIC_CAPABILITY_FILES:
        text = path.read_text(encoding="utf-8")
        lowered = text.lower()
        for term in FORBIDDEN_PROJECT_TERMS:
            if term.lower() in lowered:
                fail(f"{path.relative_to(ROOT)} contains project-specific term: {term}")

    print("BOUNDED_RUN_INTEGRITY_TEST_PASS")


if __name__ == "__main__":
    main()
