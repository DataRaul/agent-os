# DuckDB local ad-hoc query: bounded evaluation

Status: **LOCAL_EVIDENCE_ONLY — NO_RUNTIME_ADMISSION**  
Date: 2026-09-29

## Candidate and scope

The official DuckDB skills source was reviewed at commit `7feda8e01e22bc0886c86123f3884947e36d8c69`, specifically `skills/query/SKILL.md`. The documented ad-hoc command pattern was exercised with DuckDB CLI v1.4.1 in disposable local directories. The official skill itself was not installed, invoked as a plugin, or admitted.

The narrow candidate uses `:memory:`, an explicit single-file `allowed_paths` list, `enable_external_access=false`, `allow_persistent_secrets=false`, and `lock_configuration=true` before the query. All test data was synthetic. No credentials, external services, or GitHub Actions were used.

## Observations

| Probe | Observed result |
| --- | --- |
| Read the sole allowed CSV and aggregate two rows | Succeeded; sum 18 |
| Read another local CSV | Denied |
| Write a new CSV or overwrite the allowed input | Denied; files unchanged |
| Re-enable external access after locking | Denied |
| Read a symlink to another file, or a wildcard path | Denied |
| Attach another database | Denied |
| Install/load an extension | Denied |
| Read a remote HTTPS URL | Denied |
| Create a persistent secret or call `getenv` | Denied |

The upstream skill's startup instructions first search for shared `.duckdb-skills/state.sql` and, when present, execute `duckdb -init` before choosing ad-hoc versus session mode. A synthetic state file containing an `ATTACH` statement made an unrelated database visible to that startup command and to a session query. This is expected from the documented session behavior, but it crosses the proposed isolated-file boundary. The isolated `:memory:` command did not use that state file.

## Disposition

Keep the full upstream skill **REFERENCE_ONLY**. The local tests support further consideration of a separate, explicitly scoped ad-hoc adapter; they do not establish safety for arbitrary SQL, arbitrary paths, all DuckDB versions, plugin invocation, session restoration, natural-language SQL generation, installation fallback, or real project data. No registry entry, runtime authority, credentials, or private mapping is changed.

A future adapter must independently verify a canonical allowed input path, bypass state discovery and `-init`, forbid installation and session fallback, bound query output/resources, and fail closed on any mismatch. Admission requires a separate contract, public-safe evaluation, and explicit selection under the roadmap gates.
