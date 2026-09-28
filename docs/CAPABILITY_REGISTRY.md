# Public capability registry contract

## Purpose

`catalog/capability-registry.json` is the stable machine-readable index of capabilities that public Agent OS actually exposes for reuse.

It solves a different problem from the tooling inventory:

- the tooling inventory records things Agent OS has discovered or audited;
- the capability registry records public Agent OS capabilities that a consumer may reference by stable ID.

Discovery, audit and availability are deliberately separate states.

## Dependency direction

Public Agent OS is self-contained.

```text
PUBLIC AGENT OS
capability registry + skills + reviewers + evals
        |
        | exact commit SHA + capability IDs
        v
OPTIONAL CONSUMER / PRIVATE OVERLAY
selection + mapping + policy + authority
```

The public repository must never fetch, clone, authenticate to, test against, or otherwise require a private overlay.

A private or organizational overlay may depend on public Agent OS. Public Agent OS must never depend on that overlay.

## Version contract

Consumers pin two identities:

1. an exact public Agent OS repository commit SHA — authoritative implementation identity;
2. the capability ID and `capability_contract_version` — stable semantic contract identity.

A consumer does not silently follow `main` or `latest`.

A material capability-contract change increments `capability_contract_version`. A normal code/docs change still receives a new repository SHA even when the contract version does not change.

## Registry inclusion

An entry may be `AVAILABLE` only when:

- its public implementation path exists;
- required public-safe eval material exists for skills;
- deterministic Agent OS validation covers it;
- it grants no authority merely by being present;
- it is understandable without private context.

Vendor/tool candidates discovered in P4 do not enter the registry merely because they were found or audited. They enter only after the applicable admission/evidence/delivery gates establish a public reusable capability.

## Authority boundary

The registry answers:

> What generic public capability exists at this exact public version?

It does not answer:

> Which project should use it?
> When should it run?
> What credentials may it use?
> May it write, publish, deploy or spend?

Those decisions belong to the consuming environment, local repository contracts, and any private overlay. The consumer may narrow authority but may not infer authority from registry membership.

## Privacy boundary

The registry must contain no:

- private repository names or project IDs;
- private routing or selection decisions;
- private incidents, metrics, chronology or eval fixtures;
- private Knowledge Core contents;
- credentials, secrets or personal data.

The public publication gate remains mandatory.

## Evolution

The registry is additive by default.

Deprecation/removal requires an explicit compatibility path and should not silently break consumers pinned to an older public SHA.

Consumers are expected to review a public diff before advancing their adopted SHA.
