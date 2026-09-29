from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "capability-selection-request.schema.json"
CASES = ROOT / "benchmarks" / "capability-selection-contract" / "cases.json"


def validate(request: object, schema: dict) -> bool:
    if not isinstance(request, dict):
        return False
    if set(request) != set(schema["required"]):
        return False
    props = schema["properties"]
    if request["schema_version"] != 1:
        return False
    for field in ("public_base_sha", "capability_id"):
        value = request[field]
        if not isinstance(value, str) or re.fullmatch(props[field]["pattern"], value) is None:
            return False
    version = request["capability_contract_version"]
    if type(version) is not int or version < 1:
        return False
    for field in ("work_class", "complexity_class", "declared_authority_class"):
        if not isinstance(request[field], str) or request[field] not in props[field]["enum"]:
            return False
    preconditions = request["required_preconditions"]
    if not valid_strings(preconditions, allow_empty=True):
        return False
    output = request["output_postcondition_contract"]
    if not isinstance(output, dict) or set(output) != {"output_type", "postconditions"}:
        return False
    return (
        isinstance(output["output_type"], str)
        and bool(output["output_type"].strip())
        and valid_strings(output["postconditions"], allow_empty=False)
    )


def valid_strings(values: object, *, allow_empty: bool) -> bool:
    return (
        isinstance(values, list)
        and (allow_empty or bool(values))
        and all(isinstance(value, str) and bool(value.strip()) for value in values)
        and len(values) == len(set(values))
    )


def main() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    cases = json.loads(CASES.read_text(encoding="utf-8"))
    assert schema["additionalProperties"] is False
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert set(schema["required"]) == set(schema["properties"])
    assert cases["schema_version"] == 1
    assert len(cases["cases"]) >= 8
    for case in cases["cases"]:
        actual = validate(case["request"], schema)
        assert actual is case["valid"], f"{case['id']}: expected {case['valid']}, got {actual}"
    print("P5_GENERIC_SELECTION_CONTRACT_PASS")


if __name__ == "__main__":
    main()
