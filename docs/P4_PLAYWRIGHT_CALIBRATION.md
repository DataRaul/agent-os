# P4 Playwright observation calibration baseline

Status: `P4_PLAYWRIGHT_CALIBRATION_BASELINE_V1_COMPLETE__RUNTIME_ADMISSION_UNCHANGED`

## Purpose

This tranche adds calibration evidence for the already bounded Microsoft Playwright browser-observation candidate. It does not widen the candidate beyond the P4.2 observation profile and does not authorize general browser automation.

The evidence compares two public synthetic loopback timepoints:

- the accepted 2026-09-28 runtime evidence on exact `@playwright/cli@0.1.21`;
- a 2026-10-01 shadow calibration on exact `@playwright/cli@0.1.22`, after the upstream implementation drift recorded in the second tooling tranche.

The machine-readable record is `catalog/p4-playwright-calibration.json`.

## Calibration run

The 2026-10-01 calibration used the existing loopback fixture and observation evaluator. It installed the exact public candidate package in an ephemeral GitHub runner and executed three isolated replicates.

Each replicate required:

- loopback-only target `127.0.0.1`;
- isolated ephemeral browser state;
- stdout-only observation evidence;
- dynamic DOM state observation;
- console-error observation;
- request metadata observation;
- no authenticated profile;
- no persistent or attached session;
- no credentials;
- no external target mutation;
- a clean repository postcondition.

All three replicates emitted `P4_PLAYWRIGHT_OBSERVATION_RUNTIME_EVAL_PASS`, and the enclosing job emitted `P4_PLAYWRIGHT_OBSERVATION_CALIBRATION_PASS`.

## Interpretation

The two timepoints establish a minimal shadow-calibration baseline across the 0.1.21 to 0.1.22 upstream version change for the narrow synthetic observation profile. This is useful evidence that the bounded observation contract survived the reviewed version drift.

It is not evidence for authenticated browsing, persistent profiles, attached sessions, arbitrary Playwright code, WebMCP calls, form submission, file transfer, external mutation, or production reliability.

The candidate therefore remains `PIN_REQUIRED`, outside the public capability registry, and not runtime-admitted. Real-consumer shadow evidence or a separately authorized runtime-admission tranche remains required before widening that disposition.

## Terminal

`P4_PLAYWRIGHT_CALIBRATION_BASELINE_ESTABLISHED__RUNTIME_ADMISSION_UNCHANGED`
