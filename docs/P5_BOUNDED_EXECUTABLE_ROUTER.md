# P5 bounded executable router prototype V1

Status: `BOUNDED_EXECUTABLE_FIXTURE_ROUTER_V1_COMPLETE`

## Purpose

This tranche exercises the execution path behind the P5 declarative contracts without granting authority to any real public capability or vendor tool.

`scripts/p5_bounded_executable_router.py` can execute exactly one built-in synthetic adapter, `fixture-echo-v1`, against a synthetic `fixture-echo` registry entry in `benchmarks/p5-bounded-executable-router/fixtures.json`.

The prototype is deliberately narrower than a production router. It exists to prove exact pin/digest binding, precondition gating, adapter identity binding, deterministic execution receipts, output hashing, and postcondition verification before real adapters are admitted.

## Execution sequence

The router:

1. validates the already-declared capability against the supplied synthetic registry using the P5 binding-decision contract;
2. requires an exact reviewed public SHA and exact canonical registry SHA-256;
3. enforces a `read-only` execution ceiling;
4. requires precondition evidence to exactly cover the request's declared preconditions and all checks to pass;
5. requires the exact built-in `fixture-echo-v1` adapter;
6. rejects adapter input larger than 4096 canonical JSON bytes or any input shape other than `{"payload": ...}`;
7. executes the pure in-process echo adapter;
8. emits canonical input/output SHA-256 digests;
9. verifies the supported output postcondition;
10. emits `schemas/p5-bounded-execution-receipt.schema.json`-compatible evidence.

## Hard boundaries

The prototype has no dynamic capability search, dynamic import, subprocess execution, shell execution, filesystem mutation, network access, credential access, browser access, vendor tooling, project mapping, external side effect, or multi-capability orchestration.

The synthetic registry is not the public capability registry. `fixture-echo` is not a public Agent OS capability and is not eligible for private mapping or real-project routing.

A successful receipt reports:

- `runtime_scope: SYNTHETIC_BUILTIN_ADAPTER_ONLY`;
- `authority_source: PUBLIC_SAFE_FIXTURE_HARNESS`;
- `registry_authority_granted: false`;
- `external_authority_used: false`;
- an empty `side_effects` array.

## Validation

Run:

```bash
python scripts/test_p5_bounded_executable_router.py
```

The deterministic test covers successful execution plus stale-pin, registry-digest, authority-ceiling, adapter-ID, failed/missing-precondition, output-contract, malformed/oversized-input, and registry-authority failures.

## Next boundary

This tranche establishes executable plumbing only. Connecting the router to a real capability requires a separately admitted adapter with its own authority, input/output, postcondition, and calibration evidence. Registry membership alone is never sufficient.

## Terminal

`P5_BOUNDED_EXECUTABLE_FIXTURE_ROUTER_COMPLETE__REAL_ADAPTER_ADMISSION_SEPARATE`
