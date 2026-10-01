# Agent OS stability policy

Status: `FIRST_STABLE_RELEASE_CANDIDATE_POLICY_V1`

Prepared stable candidate: `1.0.0`

Published prerelease candidate: `v1.0.0-rc.1`

## Stable public surface

The first stable release is intended to stabilize the public capability identity and consumer contracts, not every experimental implementation in the repository.

The published RC preparation manifest is `catalog/release-candidate.json`; the post-publication record is `catalog/release-publication.json`; and the prepared stable candidate is `catalog/stable-release-candidate.json`. The stable candidate revalidates the same public capability IDs, contract versions, registry, selection, decision, overlay, and trust interfaces for the 1.0 line and pins their RC Git blob identities.

Consumers still pin an exact repository commit SHA. The semantic release version identifies a reviewed distribution point; it does not replace the exact-SHA implementation identity.

## Compatibility rules

After 1.0.0:

- removing or incompatibly changing a stable public interface requires a major release;
- a material capability contract change requires that capability's `capability_contract_version` to increment;
- any capability addition, deprecation, removal, reactivation, or contract-version change requires a `registry_version` increment and explicit `catalog/capability-changelog.json` treatment;
- compatible implementation fixes may preserve a capability contract version but always have a new repository SHA;
- registry membership never grants file, network, credential, mutation, deployment, spend, or other execution authority;
- public Agent OS must remain usable without a private overlay.

## Experimental exclusions

The following are explicitly outside the proposed 1.0 stability guarantee:

- P2 specialist reviewer candidates until independent comparative runs justify admission;
- the P5 bounded executable fixture router as a production runtime surface;
- non-admitted P4 vendor/tool candidates;
- Playwright browser observation, which remains pinned and non-runtime.

Experimental material may evolve without implying a breaking change to the stable 1.0 interface, provided stable capability contracts and stable schemas remain compatible.

## Release gate

`scripts/release_readiness.py check` remains the authoritative local release-readiness command. The release-candidate validator adds exact manifest, registry, capability-contract, stable-path, and publication-boundary checks.

A release-candidate pass does not by itself create a tag, publish a GitHub Release, advance any consumer or private-overlay pin, or grant runtime authority. Explicit publication authority was exercised for prerelease `v1.0.0-rc.1`; post-publication evidence is recorded in `catalog/release-publication.json`. Stable `v1.0.0` publication remains separately gated.

## Publication sequence

1. Merge release/stability preparation with all public checks green.
2. Fresh-reconcile the resulting main commit and run release readiness on that exact commit.
3. Review the generated capability snapshot and registry digest.
4. Obtain explicit publication authority.
5. Only then create the stable tag/release and, separately, allow consumers to choose whether to advance their pins.

## Terminal

`AGENT_OS_1_0_0_STABLE_CANDIDATE_PREPARED__PUBLICATION_AUTHORITY_REQUIRED`
