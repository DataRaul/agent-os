"""Deterministic bounded-run integrity classifier.

This module verifies evidence for a consequential bounded run. It does not execute the
underlying runner, grant authority, make network calls, or mutate project state.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

CAPABILITY_ID = "bounded-run-integrity"
CAPABILITY_CONTRACT_VERSION = 1
WORK_CLASS = "BOUNDED_EVIDENCE_PRODUCING_RUN"

PASS = "RUN_INTEGRITY_PASS"
PARTIAL = "RUN_INTEGRITY_PARTIAL"
FAILED = "RUN_INTEGRITY_FAILED"
INSUFFICIENT = "RUN_INTEGRITY_INSUFFICIENT_EVIDENCE"

CHECK_STATUSES = {"PASS", "FAIL", "UNKNOWN"}
PROTECTED_STATUSES = {"UNCHANGED", "CHANGED", "UNKNOWN"}


class IntegrityError(ValueError):
    pass


def canonical_sha256(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _require_dict(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise IntegrityError(f"{label} must be an object")
    return value


def _require_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise IntegrityError(f"{label} must be a non-empty string")
    return value


def _require_bool(value: object, label: str) -> bool:
    if not isinstance(value, bool):
        raise IntegrityError(f"{label} must be boolean")
    return value


def _require_string_list(value: object, label: str) -> list[str]:
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise IntegrityError(f"{label} must be an array of non-empty strings")
    if len(value) != len(set(value)):
        raise IntegrityError(f"{label} must not contain duplicates")
    return value


def _normalize_checks(
    raw: object,
    declared_ids: list[str],
    label: str,
) -> tuple[list[dict[str, str]], bool, bool]:
    if not isinstance(raw, list):
        raise IntegrityError(f"{label} must be an array")
    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    has_fail = False
    has_unknown = False
    for index, item in enumerate(raw):
        row = _require_dict(item, f"{label}[{index}]")
        check_id = _require_string(row.get("id"), f"{label}[{index}].id")
        status = row.get("status")
        if status not in CHECK_STATUSES:
            raise IntegrityError(f"{label}[{index}].status invalid")
        if check_id in seen:
            raise IntegrityError(f"{label} duplicate id: {check_id}")
        seen.add(check_id)
        rows.append({"id": check_id, "status": status})
        has_fail = has_fail or status == "FAIL"
        has_unknown = has_unknown or status == "UNKNOWN"
    if set(seen) != set(declared_ids):
        missing = sorted(set(declared_ids) - seen)
        extra = sorted(seen - set(declared_ids))
        raise IntegrityError(f"{label} coverage mismatch: missing={missing} extra={extra}")
    return rows, has_fail, has_unknown


def _normalize_protected_checks(
    raw: object,
    required: bool,
) -> tuple[list[dict[str, str]], bool, bool]:
    if not isinstance(raw, list):
        raise IntegrityError("protected_state_checks must be an array")
    if required and not raw:
        return [], False, True
    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    changed = False
    unknown = False
    for index, item in enumerate(raw):
        row = _require_dict(item, f"protected_state_checks[{index}]")
        check_id = _require_string(row.get("id"), f"protected_state_checks[{index}].id")
        status = row.get("status")
        if status not in PROTECTED_STATUSES:
            raise IntegrityError(f"protected_state_checks[{index}].status invalid")
        if check_id in seen:
            raise IntegrityError(f"protected_state_checks duplicate id: {check_id}")
        seen.add(check_id)
        rows.append({"id": check_id, "status": status})
        changed = changed or status == "CHANGED"
        unknown = unknown or status == "UNKNOWN"
    return rows, changed, unknown


def classify_run(record: object) -> dict[str, Any]:
    data = _require_dict(record, "run record")
    if data.get("schema_version") != 1:
        raise IntegrityError("unsupported run record schema_version")
    if data.get("work_class") != WORK_CLASS:
        raise IntegrityError("unsupported work_class")

    candidate = _require_string(data.get("candidate_identity"), "candidate_identity")
    runner = _require_string(data.get("runner_identity"), "runner_identity")
    authority_source = _require_string(
        data.get("authority_source_declaration"), "authority_source_declaration"
    )
    if data.get("authority_granted") is not False:
        raise IntegrityError("bounded-run-integrity must declare authority_granted=false")

    contract = _require_dict(data.get("contract"), "contract")
    precondition_ids = _require_string_list(contract.get("preconditions"), "contract.preconditions")
    positive_ids = _require_string_list(
        contract.get("positive_postconditions"), "contract.positive_postconditions"
    )
    negative_ids = _require_string_list(
        contract.get("negative_postconditions"), "contract.negative_postconditions"
    )
    persistence_required = _require_bool(
        contract.get("persistence_required"), "contract.persistence_required"
    )
    protected_required = _require_bool(
        contract.get("protected_state_checks_required"),
        "contract.protected_state_checks_required",
    )
    partial_allowed = _require_bool(
        contract.get("partial_result_allowed"), "contract.partial_result_allowed"
    )

    inputs_configuration = _require_dict(
        data.get("inputs_configuration"), "inputs_configuration"
    )
    config_digest = canonical_sha256(inputs_configuration)
    contract_digest = canonical_sha256(contract)

    evidence = _require_dict(data.get("evidence"), "evidence")
    evidence_available = evidence.get("authoritative_evidence_available")
    if not isinstance(evidence_available, bool):
        raise IntegrityError("evidence.authoritative_evidence_available must be boolean")

    preconditions, pre_fail, pre_unknown = _normalize_checks(
        evidence.get("preconditions"), precondition_ids, "preconditions"
    )
    positives, positive_fail, positive_unknown = _normalize_checks(
        evidence.get("positive_postconditions"), positive_ids, "positive_postconditions"
    )
    negatives, negative_fail, negative_unknown = _normalize_checks(
        evidence.get("negative_postconditions"), negative_ids, "negative_postconditions"
    )
    protected, protected_changed, protected_unknown = _normalize_protected_checks(
        evidence.get("protected_state_checks"), protected_required
    )

    runner_executed = evidence.get("runner_executed")
    expected_work_occurred = evidence.get("expected_work_occurred")
    if runner_executed is not None and not isinstance(runner_executed, bool):
        raise IntegrityError("evidence.runner_executed must be true, false, or null")
    if expected_work_occurred is not None and not isinstance(expected_work_occurred, bool):
        raise IntegrityError("evidence.expected_work_occurred must be true, false, or null")

    observed_candidate = evidence.get("observed_candidate_identity")
    if observed_candidate is not None:
        _require_string(observed_candidate, "evidence.observed_candidate_identity")
    observed_inputs = evidence.get("observed_inputs_configuration")
    if observed_inputs is not None:
        _require_dict(observed_inputs, "evidence.observed_inputs_configuration")

    source_failure_status = evidence.get("source_failure_evidence_status")
    if source_failure_status not in {"COMPLETE", "UNKNOWN"}:
        raise IntegrityError(
            "evidence.source_failure_evidence_status must be COMPLETE or UNKNOWN"
        )
    source_failures = _require_string_list(
        evidence.get("source_failures"), "evidence.source_failures"
    )
    warnings = _require_string_list(evidence.get("warnings"), "evidence.warnings")

    artifacts_raw = evidence.get("artifacts")
    if not isinstance(artifacts_raw, list):
        raise IntegrityError("evidence.artifacts must be an array")
    artifacts: list[dict[str, Any]] = []
    artifact_failure = False
    artifact_unknown = False
    artifact_ids: set[str] = set()
    for index, item in enumerate(artifacts_raw):
        artifact = _require_dict(item, f"evidence.artifacts[{index}]")
        artifact_id = _require_string(
            artifact.get("artifact_id"), f"evidence.artifacts[{index}].artifact_id"
        )
        if artifact_id in artifact_ids:
            raise IntegrityError(f"evidence.artifacts duplicate artifact_id: {artifact_id}")
        artifact_ids.add(artifact_id)
        artifact_candidate = artifact.get("candidate_identity")
        artifact_inputs = artifact.get("inputs_configuration")
        fresh = artifact.get("fresh")
        persisted = artifact.get("persisted")
        if artifact_candidate is not None:
            _require_string(
                artifact_candidate, f"evidence.artifacts[{index}].candidate_identity"
            )
        if artifact_inputs is not None:
            _require_dict(
                artifact_inputs, f"evidence.artifacts[{index}].inputs_configuration"
            )
        if fresh is not None and not isinstance(fresh, bool):
            raise IntegrityError(
                f"evidence.artifacts[{index}].fresh must be true, false, or null"
            )
        if persisted is not None and not isinstance(persisted, bool):
            raise IntegrityError(
                f"evidence.artifacts[{index}].persisted must be true, false, or null"
            )
        artifact_config_digest = (
            canonical_sha256(artifact_inputs) if artifact_inputs is not None else None
        )
        artifact_failure = artifact_failure or (
            artifact_candidate is not None and artifact_candidate != candidate
        )
        artifact_failure = artifact_failure or (
            artifact_config_digest is not None and artifact_config_digest != config_digest
        )
        artifact_failure = artifact_failure or fresh is False
        artifact_failure = artifact_failure or (
            persistence_required and persisted is False
        )
        artifact_unknown = artifact_unknown or artifact_candidate is None
        artifact_unknown = artifact_unknown or artifact_inputs is None
        artifact_unknown = artifact_unknown or fresh is None
        artifact_unknown = artifact_unknown or (
            persistence_required and persisted is None
        )
        artifacts.append(
            {
                "artifact_id": artifact_id,
                "candidate_identity": artifact_candidate,
                "inputs_configuration_digest": artifact_config_digest,
                "fresh": fresh,
                "persisted": persisted,
            }
        )

    failed = False
    insufficient = False
    partial = False

    if not evidence_available:
        insufficient = True
    if pre_fail:
        failed = True
    if pre_unknown:
        insufficient = True
    if runner_executed is False or expected_work_occurred is False:
        failed = True
    if runner_executed is None or expected_work_occurred is None:
        insufficient = True
    if observed_candidate is None or observed_inputs is None:
        insufficient = True
    else:
        if observed_candidate != candidate:
            failed = True
        if canonical_sha256(observed_inputs) != config_digest:
            failed = True
    if source_failure_status == "UNKNOWN":
        insufficient = True
    if source_failures:
        if partial_allowed:
            partial = True
        else:
            failed = True
    if not artifacts:
        failed = True
    if artifact_failure:
        failed = True
    if artifact_unknown:
        insufficient = True
    if positive_fail or negative_fail or protected_changed:
        failed = True
    if positive_unknown or negative_unknown or protected_unknown:
        insufficient = True

    if failed:
        disposition = FAILED
    elif insufficient:
        disposition = INSUFFICIENT
    elif partial:
        disposition = PARTIAL
    else:
        disposition = PASS

    return {
        "schema_version": 1,
        "contract_type": "BOUNDED_RUN_INTEGRITY_RECEIPT",
        "capability_id": CAPABILITY_ID,
        "capability_contract_version": CAPABILITY_CONTRACT_VERSION,
        "work_class": WORK_CLASS,
        "candidate_identity": candidate,
        "runner_identity": runner,
        "declared_run_contract_digest": contract_digest,
        "inputs_configuration_digest": config_digest,
        "precondition_results": preconditions,
        "execution_evidence": {
            "authoritative_evidence_available": evidence_available,
            "runner_executed": runner_executed,
            "expected_work_occurred": expected_work_occurred,
            "observed_candidate_identity": observed_candidate,
            "observed_inputs_configuration_digest": (
                canonical_sha256(observed_inputs) if observed_inputs is not None else None
            ),
            "source_failure_evidence_status": source_failure_status,
        },
        "produced_output_artifact_identities": artifacts,
        "positive_postcondition_results": positives,
        "negative_postcondition_results": negatives,
        "protected_state_checks": protected,
        "observed_failures_warnings": {
            "source_failures": source_failures,
            "warnings": warnings,
        },
        "final_disposition": disposition,
        "authority_source_declaration": authority_source,
        "authority_granted": False,
    }
