# P4.2 narrow audits

## Scope

This tranche audits only the three candidates selected by the deterministic P4.1 queue. It performs source inspection and public-safe contract evaluation only.

No package was installed, no account was authenticated, no external system was mutated, no MCP server was connected, and no paid infrastructure was introduced.

Machine-readable evidence is in `catalog/p4-narrow-audits.json`. Public-safe cases are in `evals/p4-narrow-audits/cases.json`.

## Results

### Agent Skills format specification

Disposition: `REFERENCE_ONLY`.

The pinned specification is useful for SKILL.md portability, but it is a format contract rather than an execution capability. Its experimental `allowed-tools` field and optional executable-script convention cannot be interpreted as Agent OS authority.

### skills-ref reference library

Disposition: `REFERENCE_ONLY`.

The pinned 0.1.0 implementation is a small deterministic local parser/validator/prompt serializer. The inspected runtime code reads local skill files and emits output; however, upstream explicitly labels the library demonstration-only and not intended for production. Agent OS therefore keeps it as reference evidence rather than adding a production dependency.

### Microsoft Playwright browser observation

Disposition: `PIN_REQUIRED` for any later evaluation; not admitted.

The pinned 0.1.21 skill contains useful observation primitives, but the same skill also exposes broad browser mutation, storage, arbitrary-code, installation, and publication surfaces. P4.2 defines a narrower candidate profile:

- exact package pin;
- isolated ephemeral browser session;
- stdout evidence;
- explicit target-origin/read scope;
- observation operations only;
- no authenticated profile, storage access, arbitrary code, WebMCP calls, UI mutation, file evidence writes, request mocking, package installation, test rewriting, or publication.

This profile still requires P4.3 runtime value evidence before any admission.

## Gate state

P4.2 is complete for the bounded initial queue.

P4.3 may close the two Agent Skills candidates as reference-only without runtime admission work. The Playwright observation candidate remains evidence-pending; a clean source audit alone is not sufficient for promotion.

## Terminal

`P4_2_BOUNDED_NARROW_AUDITS_COMPLETE__P4_3_ADMISSION_EVIDENCE_NEXT`
