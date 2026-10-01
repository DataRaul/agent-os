# Private overlay contract

A private overlay extends Agent OS without forking or copying its public capabilities.

## Required behavior

A private overlay should be able to declare, per project or work class:

- enabled public Agent OS skills;
- approved official/vendor skills;
- private-only skills;
- independent reviewer roles;
- complexity-level overrides;
- authority and human-gate rules;
- private knowledge/reasoning routes;
- private evaluation fixtures.

## Inheritance rule

The overlay should reference public capability IDs rather than copy their instructions.

When the public capability changes, the private layer should evaluate the diff before adopting the new version.

## Authority rule

The overlay may narrow authority but must not treat Agent OS as granting external authority.

Project-local instructions, repository protections, current source-of-truth state, and explicit human approvals remain controlling.

## Suggested machine-readable shape

See `schemas/private-overlay-profile.schema.json`.

The schema is intentionally generic. It contains no private project identifiers or examples.

## Public/private firewall

The public repository must not require private overlay data for tests or normal development.

Public Agent OS may specify the generic adoption/pinning contract, but whether any private consumer has adopted a particular SHA, route, capability, or authority state is private operational state and must not be recorded as a current fact in the public repository.

Private test fixtures must never be copied into public evals merely to improve coverage.
