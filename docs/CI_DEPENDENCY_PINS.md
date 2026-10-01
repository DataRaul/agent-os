# Immutable CI dependency pins

Status: `CI_ACTION_PINS_V1`

External GitHub Actions in public Agent OS workflows must use exact 40-character commit SHAs. Mutable tag, branch, major, or minor references fail deterministic validation.

## Reviewed dependencies

Reviewed from the official upstream repositories on 2026-10-01:

- `actions/checkout` release `v7.0.1` -> `3d3c42e5aac5ba805825da76410c181273ba90b1`
- `actions/setup-python` release `v7.0.0` -> `5fda3b95a4ea91299a34e894583c3862153e4b97`

Both reviewed releases use the Node 24 GitHub Actions runtime. Current workflows use checkout defaults plus the existing `python-version` input only. No token permission, credential input, cache setting, external service, or write authority is added; workflow permissions remain `contents: read`.

## Update rule

An upstream release is a candidate, not an automatic update. Review official upstream source/release notes, verify used inputs remain compatible, preserve least privilege, update the exact SHA and version comment together, then run public validation.

`scripts/validate_ci_action_pins.py` rejects non-immutable external `owner/repository@ref` references. Local actions are outside this external-pin check.

Pinning identifies executable source; it does not grant authority.

Terminal: `CI_ACTION_DEPENDENCIES_EXACT_SHA_PINNED_V1`
