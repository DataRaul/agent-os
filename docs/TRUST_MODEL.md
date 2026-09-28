# Trust and vendor capability admission

## Goal

Use high-quality upstream skills and plugins without turning provenance into blanket permission.

## Trust tiers

### T0 — local Agent OS capability

Authored and reviewed in this repository.

### T1 — official vendor capability

Published under the vendor/project's authoritative organization or official documentation.

This establishes provenance, not unlimited trust.

### T2 — vendor-hosted community capability

Hosted in an official ecosystem but materially authored or maintained by a third party.

Requires explicit audit before admission.

### T3 — independent third party

Not admitted by default. Evaluate source, maintainer, code, permissions, update path, and necessity before use.

## Admission checks

For any external capability record:

1. canonical upstream owner and URL;
2. exact capability name and purpose;
3. verified date;
4. license status;
5. executable scripts/hooks present?;
6. network access?;
7. requested tools/permissions;
8. credential handling;
9. external side effects;
10. update/pinning strategy;
11. narrower alternative?;
12. admission state.

## Default admission states

- `REFERENCE_ONLY` — safe to reference, not automatically executed.
- `SKILL_ALLOWED` — instructions/resources allowed with bounded tools.
- `PLUGIN_ALLOWED` — plugin plus declared tool surfaces reviewed.
- `PIN_REQUIRED` — usable only at an explicitly reviewed version/commit.
- `REJECTED` — not approved.

## Audit records

Vendor capabilities considered beyond initial discovery must use the generic audit contract in `docs/VENDOR_CAPABILITY_ADMISSION.md` and, when audited, link a machine-readable record under `catalog/vendor-audits/`.

A completed audit does not imply admission. `KEEP_REFERENCE_ONLY` is a valid audit outcome when the package has useful reference value but requests broader execution, network, credential, filesystem, installer, or privacy authority than Agent OS should grant by default.

## Update rule

Upstream updates are new candidates. They do not inherit prior approval automatically when scripts, hooks, permissions, tool surfaces, or material instructions changed.
