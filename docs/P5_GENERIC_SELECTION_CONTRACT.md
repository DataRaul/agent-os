# P5 generic capability selection request V1

Status: declarative interface only. This schema describes a candidate request. It does not select, load, compose, execute, or authorize any capability.

`schemas/capability-selection-request.schema.json` is the public contract. A consumer supplies an exact 40-character public repository commit SHA, stable public `capability_id`, and `capability_contract_version`. The SHA is the implementation identity; a floating branch name is invalid. The request also declares a generic work class, C0–C3 complexity class, authority class, preconditions, and output/postconditions.

Validation of this object is structural only. It does not prove that the SHA exists, that the ID and contract version match a registry at that SHA, that preconditions are met, or that authority is granted. A future consumer must verify those facts against its pinned registry and local policy, and fail closed on mismatch. A declaration of `publish-deploy`, `spend`, or `destructive` is a description of requested authority, never permission. Empty preconditions are permitted when none are required; postconditions must be stated.

The public request contains no project selector, private route, credential, provider installation, tool invocation, policy override, or execution plan. Consumer-specific mappings, selection, authority checks, consent, calibration, and runtime evidence remain outside this public contract. No registry entry or runtime admission changes in this tranche.

The public-safe benchmark at `benchmarks/capability-selection-contract/cases.json` covers valid declarations and rejection of floating pins, malformed IDs, missing/extra fields, invalid authority, and missing postconditions. Run `python scripts/test_capability_selection_contract.py` for the deterministic structural check.
