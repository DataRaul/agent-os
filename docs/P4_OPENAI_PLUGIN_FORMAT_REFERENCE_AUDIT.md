# OpenAI plugin format reference — bounded audit

Status: **REFERENCE_ONLY — NO INSTALLATION OR RUNTIME ADMISSION**

This audit reviews only the public manifest/marketplace format reference at upstream commit `5fd93af4cd0c623e020d0cc7e9ce178b4ac1f70f`.

Reviewed material establishes the documented plugin manifest location, marketplace locations, relative source-path convention, and marketplace policy fields. Agent OS does not install a plugin, connect an MCP server, authenticate, execute the creator script, write a plugin tree, or mutate a marketplace.

The adjacent upstream `plugin-creator` skill is intentionally outside this admitted reference surface because it can create files and update marketplace metadata. Therefore the disposition remains `REFERENCE_ONLY`; no capability-registry entry or runtime authority changes.

Machine-readable evidence: `catalog/p4-openai-plugin-format-reference-audit.json`.
