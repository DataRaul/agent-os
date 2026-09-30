# Public publication safety gate

## Purpose

This gate is a mandatory precondition before Agent OS expands into vendor/tooling admission or other post-P1 capability growth.

It adds a fail-closed publication boundary on top of the existing architectural firewall.

## Gate sequence

A public change is publishable only when all of the following pass:

1. automated public-boundary scanning;
2. deterministic Agent OS validation;
3. semantic review of the proposed change;
4. exact default-branch verification after merge.

The automated scan is intentionally conservative. A pass is necessary, not sufficient: it does not replace semantic privacy review.

## Automated public-boundary scan

The publication scanner checks repository text and committed paths for high-confidence publication hazards, including secret/token material, private-key blocks, sensitive credential/key filenames, and project-specific same-owner repository references other than the public Agent OS repository itself.

The scanner has deterministic self-tests covering clean content, the allowed public self-reference, forbidden same-owner repository references, representative secret material, and sensitive credential paths. The scan and its self-tests run in CI; the publication scan itself runs on pull requests and on updates to the default branch.

## Private-derived work

Private observations may inform a generic public capability, but the public artifact must be independently sanitized and understandable without private context.

Do not publish private repository names or project identifiers; private state, chronology, incidents, metrics, or roadmaps; private knowledge-system content; credentials, secrets, personal data, proprietary evidence; or private evaluation fixtures.

Use synthetic/public-safe evaluation material instead.

## Failure behavior

Any detected publication hazard blocks the gate. Ambiguous cases fail closed for semantic review rather than being treated as safe by automation.

## Sequencing rule

Vendor/tooling admission work must not be treated as ready for expansion until this publication gate is merged, active in CI, and verified on the exact public default-branch state.

## Terminal

`PUBLICATION_GATE_PASS`
