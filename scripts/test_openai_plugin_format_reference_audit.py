from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "catalog" / "p4-openai-plugin-format-reference-audit.json"

def main() -> None:
    x = json.loads(PATH.read_text(encoding="utf-8"))
    assert x["status"] == "P4_MARKETPLACE_FORMAT_REFERENCE_AUDIT_COMPLETE"
    assert x["upstream_commit"] == "5fd93af4cd0c623e020d0cc7e9ce178b4ac1f70f"
    assert x["candidate"] == "openai-plugin-format-reference"
    assert len(x["reviewed_files"]) == 3
    authority = x["authority_profile"]
    for key in ("installation","authentication","mcp_connection","script_execution","local_write","marketplace_mutation"):
        assert authority[key] is False
    assert authority["reference_read_only"] is True
    assert x["disposition"] == "REFERENCE_ONLY"
    assert x["registry_promotion"] is False
    assert x["runtime_admission"] is False
    print("P4_OPENAI_PLUGIN_FORMAT_REFERENCE_AUDIT_PASS")

if __name__ == "__main__":
    main()
