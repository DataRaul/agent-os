# P5 declarative decision contracts V1

Status: `DECLARATIVE_ONLY`

This tranche extends the generic P5 interface without creating an executable router. It defines deterministic evidence shapes for one capability already named by a request, explicit precondition/postcondition results, and an explicit multi-capability composition declaration.

The contracts never choose a capability dynamically, load an adapter, invoke a tool, satisfy a precondition, execute a composition, authenticate a provider, or grant authority.

## Contracts

The machine-readable schema is `schemas/capability-decision-contracts.schema.json`. Deterministic construction and validation live in `scripts/capability_decision_contracts.py`.

### Declared capability binding decision

A binding decision evaluates only the capability ID already present in a structurally valid P5 selection request. It binds evidence to:

- the consumer-verified exact public repository SHA;
- the exact canonical SHA-256 of the supplied public registry;
- the canonical SHA-256 of the request;
- the declared capability ID and contract version.

Possible dispositions are:

- `BOUND`: the single declared ID is available and version-compatible;
- `NO_MATCH`: that declared ID does not exist;
- `AMBIGUOUS_MATCH`: malformed registry evidence contains more than one matching ID;
- `REJECTED`: another deterministic incompatibility exists.

This is not a capability search. A `NO_MATCH` result does not inspect or propose alternatives.

### Reason codes

The public reason-code set is:

- `NO_MATCH`;
- `AMBIGUOUS_MATCH`;
- `STALE_PIN`;
- `REGISTRY_DIGEST_MISMATCH`;
- `CAPABILITY_NOT_AVAILABLE`;
- `CONTRACT_VERSION_MISMATCH`;
- `MALFORMED_REQUEST`;
- `REGISTRY_AUTHORITY_VIOLATION`;
- `PRECONDITION_FAILED`;
- `PRECONDITION_UNKNOWN`;
- `POSTCONDITION_FAILED`;
- `POSTCONDITION_UNKNOWN`;
- `AUTHORITY_CEILING_EXCEEDED`;
- `PRECONDITION_CONFLICT`.

Every decision/evidence artifact explicitly reports `authority_granted: false` and `executable: false`.

### Preconditions

A precondition result contains explicit checks with `PASS`, `FAIL`, or `UNKNOWN` evidence. Aggregation is deterministic:

1. any `FAIL` => `FAIL`;
2. otherwise any `UNKNOWN` => `UNKNOWN`;
3. otherwise => `PASS`.

The contract reports whether supplied evidence satisfies a declaration; it does not perform the action required to make a precondition true.

### Postconditions

Postcondition verification uses the same deterministic aggregation and additionally binds the evidence to an exact `output_sha256`. The contract does not create or mutate the output.

### Multi-capability composition declaration

A composition declaration requires at least two explicitly named capability members. Each member declares:

- capability ID and contract version;
- exact request digest;
- declared authority class;
- named precondition key/value requirements.

The composition contract checks only declarative compatibility. It reports:

- `AUTHORITY_CEILING_EXCEEDED` when a member asks for more authority than the composition ceiling;
- `PRECONDITION_CONFLICT` when members declare incompatible values for the same precondition key.

A consistent composition declaration is still not executable. No ordering, scheduling, tool loading, handoff, retry, side effect, or autonomous orchestration is created by this tranche.

## Public-safe fixtures and validation

Fixtures are in `benchmarks/capability-decision-contract/fixtures.json`. Run:

```bash
python scripts/test_capability_decision_contracts.py
```

CI covers valid binding plus stale-pin, registry-digest, no-match, ambiguous-match, availability, contract-version, authority, malformed-request, precondition, postcondition, authority-ceiling, and composition-conflict cases.

## Boundary

This tranche remains declarative and deterministic only. Any executable capability selection, adapter loading, multi-capability runtime composition, external tool invocation, credential use, or authority grant requires a separate explicit bounded authorization.
