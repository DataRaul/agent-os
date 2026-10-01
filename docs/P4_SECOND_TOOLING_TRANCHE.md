# P4 second tooling tranche

Status: `P4_SECOND_TOOLING_TRANCHE_V1_COMPLETE__NO_RUNTIME_ADMISSION`

## Scope

This bounded follow-up audits the six source-audited priority-group 4 candidates that were explicitly selected after the initial P4 tranche:

- `cloudflare-skills:cloudflare`;
- `duckdb-skills:convert-file`;
- `duckdb-skills:query`;
- `duckdb-skills:read-memories`;
- `duckdb-skills:s3-explore`;
- `microsoft-playwright-skills:persistent-and-attached-sessions`.

The tranche is source inspection plus deterministic public-safe contract evaluation only. It installs nothing, authenticates nothing, executes no vendor code, uses no credentials, reads no private session history, opens no browser, makes no object-store request, and mutates no external state.

Machine-readable evidence is in `catalog/p4-second-tooling-tranche-audits.json`; synthetic cases are in `catalog/p4-second-tooling-tranche-cases.json`.

## Source reconciliation

The Cloudflare and DuckDB default-branch identities still match the previously reviewed commits.

Playwright advanced from the previously reviewed implementation `74354ecc7a43da16d91a9bc54fa8db8283a3fcf5` / package `0.1.21` to implementation `b85c7a736bb473bf55b584e54a09ffa698d6d871` / package `0.1.22`, with documentation at `718ff450acfcb2fb1b006515a07c9412efe0bd88`. The newer bundled skill narrows its preapproved command surface, but persistent profiles and attached-browser access still cross authenticated-state and privacy boundaries. The new upstream state is therefore reviewed as evidence, not adopted as runtime authority.

## Candidate conclusions

- Cloudflare root guidance remains reference-only: product-selection reasoning is useful, while MCP, Wrangler, authentication, deployment, secrets, and sibling implementation skills remain outside the contract.
- DuckDB `convert-file` remains evaluation-only because actual conversion writes output and can require extensions, remote reads, or credentials.
- DuckDB `query` may only reuse the existing bounded local ad-hoc evaluation profile; shared session state, arbitrary write SQL, external access, persistent secrets, and extension installation remain excluded.
- DuckDB `read-memories` is restricted to synthetic fixtures because real historical agent logs cross a private-context boundary.
- DuckDB `s3-explore` remains reference-only because live use requires network access and may require credentials to private remote data.
- Playwright persistent/attached sessions remain reference-only because they can expose stored or pre-existing authenticated browser state and enable broader browser mutation through the parent CLI.

## Delivery boundary

This tranche changes neither the public capability registry nor runtime admission. It creates no project mapping, private route, authority grant, vendor installation, credential flow, external mutation, or automatic marketplace expansion.

Any executable use of these broader vendor surfaces requires a separate bounded authorization and evidence path.

## Terminal

`P4_SECOND_TOOLING_TRANCHE_COMPLETE__ALL_CANDIDATES_REMAIN_NON_RUNTIME`
