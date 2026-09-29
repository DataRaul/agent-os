from __future__ import annotations

import json
from pathlib import Path

from capability_selection_contract import load_schema, validate_request

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "benchmarks" / "capability-selection-contract" / "cases.json"


def main() -> None:
    schema = load_schema()
    cases = json.loads(CASES.read_text(encoding="utf-8"))
    assert schema["additionalProperties"] is False
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert set(schema["required"]) == set(schema["properties"])
    assert cases["schema_version"] == 1
    assert len(cases["cases"]) >= 8
    for case in cases["cases"]:
        actual = validate_request(case["request"], schema)
        assert actual is case["valid"], f"{case['id']}: expected {case['valid']}, got {actual}"
    print("P5_GENERIC_SELECTION_CONTRACT_PASS")


if __name__ == "__main__":
    main()
