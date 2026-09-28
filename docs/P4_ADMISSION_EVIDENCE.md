# P4.3 admission and value evidence

## Scope

P4.3 evaluates whether the three bounded P4.2 candidates earn any change from their audited dispositions. Evidence is intentionally narrow: a clean source audit or a green CI badge is not sufficient.

Machine-readable evidence is in `catalog/p4-admission-evidence.json`.

## Agent Skills format specification

Disposition remains `REFERENCE_ONLY`.

It is useful for portability and compatibility checks, but it is a specification rather than an executable capability. No runtime admission evidence is required for that disposition.

## skills-ref reference library

Disposition remains `REFERENCE_ONLY`.

The pinned 0.1.0 source is useful as comparison evidence, but upstream explicitly states that the library is demonstration-only and not intended for production. Agent OS therefore does not install or depend on it.

## Playwright browser observation

Disposition remains `PIN_REQUIRED`; no runtime admission or capability-registry promotion is granted.

The valid synthetic run used exact `@playwright/cli@0.1.21` in an ephemeral public GitHub runner, an isolated browser session, a loopback-only fixture, stdout observation, and temporary runtime files outside the repository.

Accepted evidence is bound to Agent OS commit `09ad8d4f869ced502032b5043820ca425b9dcf85`, workflow run `36496133988`, job `109176027754`. The job completed successfully and its logs contain the required terminal marker `P4_PLAYWRIGHT_OBSERVATION_RUNTIME_EVAL_PASS`, the exact package-install command, and no failure marker.

The fixture established three functional observations:

- dynamic DOM state was visible through snapshot/find;
- a deliberate console error was visible through console inspection;
- a deliberate missing-resource request was visible through request inspection.

The repository-clean postcondition also passed after moving Playwright's own runtime files to a disposable directory outside the checkout.

## Failure-detection evidence

P4.3 explicitly rejected three earlier attempts instead of treating CI state as authoritative completion evidence:

1. run `36495815821` was green but rejected as a false green because a malformed shell file did not execute the intended runtime check and the terminal marker was absent;
2. run `36495877773` failed because the pinned CLI was invoked with an invalid config-option position;
3. run `36496046712` correctly failed because Playwright created `.playwright-cli/` inside the repository, violating the clean-repository postcondition.

This is evidence for the postcondition and failure-detection dimensions, not a reason to widen authority.

## Admission conclusion

The Playwright result demonstrates useful browser-runtime observation beyond static source inspection, but it is only synthetic loopback evidence. Calibration over time is not established. The candidate therefore remains pinned and non-admitted, eligible only for later bounded/shadow evaluation under the P4.2 narrow profile.

No capability registry entry is added in P4.3.

## Terminal

`P4_3_ADMISSION_EVIDENCE_COMPLETE__P4_4_DELIVERY_GATE_NEXT`
