# Public release readiness

Status: `RELEASE_READINESS_V1`

The public release-readiness gate is a deterministic, local control-plane check. It does not publish a release, update any consumer pin, grant runtime authority, install tooling, authenticate a service, or make network calls.

For the first stable-release programme, readiness validates the historical RC records, the stable candidate, and `catalog/stable-release-publication.json`. The stable-publication check binds `v1.0.0` to the exact tagged candidate, candidate blob identity, registry version/digest, final release classification, explicit publication authority, and the still-closed consumer/private-overlay pin boundary.

## Command

Run:

```bash
python scripts/release_readiness.py check
```

The command resolves the exact local Git HEAD, runs the Agent OS validator, publication boundary gate, and capability-registry validator, checks repository-path references in public Markdown, and emits a machine-readable result.

A passing result includes a deterministic capability snapshot containing:

- exact public repository SHA;
- canonical SHA-256 of `catalog/capability-registry.json`;
- registry version;
- every registered capability ID, kind, state, contract version and implementation path;
- SHA-256 digests for implementation paths and registered eval paths;
- `authority_granted: false`.

Use `--snapshot-out <path>` when a retained snapshot is needed. The output is evidence only; it is not an automatic publication instruction.

## Compatibility

Compare two retained public capability snapshots with:

```bash
python scripts/release_readiness.py compare base-snapshot.json head-snapshot.json
```

The comparison is local and deterministic. Before comparing compatibility, it revalidates both retained snapshot envelopes and capability rows: exact allowed keys, exact SHA/SHA-256 formats, allowed kinds and states, positive contract versions, paired eval path/digest evidence, reviewer-to-skill references, and `authority_granted: false` at both snapshot and capability level. This prevents malformed or hand-edited retained evidence from bypassing compatibility checks.

It fails closed when:

- `registry_version` decreases;
- a capability contract version decreases;
- a capability is removed without first being `DEPRECATED`;
- kind/path/eval/primary-skill contract structure changes without a capability-contract version increment;
- a deprecated capability is reactivated without a capability-contract version increment;
- capability-level changes occur without a registry-version increment;
- a capability addition, deprecation, removal, reactivation, or contract-version change lacks explicit changelog treatment.

The comparison does not authorize an automatic upgrade. Consumers still review and adopt an exact public SHA themselves.

## Changelog rules

Machine-readable capability evolution is recorded in `catalog/capability-changelog.json`.

Each entry records:

- `capability_id`;
- `change_type`;
- `from_contract_version`;
- `to_contract_version`;
- resulting `registry_version`;
- compatibility treatment;
- migration or compatibility notes.

Ordinary code or documentation changes that preserve the public semantic contract receive a new repository SHA but do not require a capability-contract version bump. Material contract changes must increment `capability_contract_version`. Capability-level registry changes must also increment `registry_version`.

## Documentation consistency

The readiness gate validates backticked repository-relative references under `docs/`, `scripts/`, `catalog/`, `schemas/`, `benchmarks/`, and `.github/`. These namespaces are treated as local documentation/control-plane references; missing referenced paths fail readiness. Skill, reviewer, and eval membership/path consistency is enforced separately by the Agent OS and capability-registry validators so documentation may still quote upstream `skills/...` paths without falsely treating them as local.

## Boundary

A `READY` result means the deterministic checks represented by this gate passed for the evaluated checkout. It does not establish release quality beyond those checks and never implies that a release was published, that a private overlay advanced its pin, or that any capability has execution authority.

Stable `v1.0.0` is published at exact commit `62fd8466971f4c8055ffefa3606d1cb1e28c7974`. The tagged commit is the authoritative stable distribution point. Consumer/private-overlay adoption remains separate and must explicitly choose the exact stable SHA.
