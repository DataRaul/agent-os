"""Reusable structural validator for the public P5 selection-request contract."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "capability-selection-request.schema.json"


def load_schema(path: Path = SCHEMA_PATH) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("selection-request schema must be a JSON object")
    return data


def valid_strings(values: object, *, allow_empty: bool) -> bool:
    return (
        isinstance(values, list)
        and (allow_empty or bool(values))
        and all(isinstance(value, str) and bool(value.strip()) for value in values)
        and len(values) == len(set(values))
    )


def validate_request(request: object, schema: dict) -> bool:
    if not isinstance(request, dict):
        return False
    if set(request) != set(schema["required"]):
        return False
    props = schema["properties"]
    if type(request["schema_version"]) is not int or request["schema_version"] != 1:
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
    if not valid_strings(request["required_preconditions"], allow_empty=True):
        return False
    output = request["output_postcondition_contract"]
    if not isinstance(output, dict) or set(output) != {"output_type", "postconditions"}:
        return False
    return (
        isinstance(output["output_type"], str)
        and bool(output["output_type"].strip())
        and valid_strings(output["postconditions"], allow_empty=False)
    )
