"""Deterministic self-tests for the public publication gate."""

from __future__ import annotations

import importlib.util
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "scripts" / "validate_publication_gate.py"


def fail(message: str) -> None:
    raise SystemExit(f"PUBLICATION_GATE_TEST_FAIL: {message}")


def load_validator():
    spec = importlib.util.spec_from_file_location("publication_gate", VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        fail("could not load publication gate")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def hazard_labels(module, root: Path) -> set[str]:
    return {item.split(": ", 1)[1] for item in module.find_hazards(root)}


def main() -> None:
    validator = load_validator()

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "README.md").write_text("public-safe text\n", encoding="utf-8")
        if validator.find_hazards(root):
            fail("clean fixture produced hazards")

        (root / "README.md").write_text(
            ("Data" + "Raul" + "/agent-os") + "\n",
            encoding="utf-8",
        )
        if validator.find_hazards(root):
            fail("public self-repository reference was rejected")

        (root / "README.md").write_text(
            ("Data" + "Raul" + "/another-repository") + "\n",
            encoding="utf-8",
        )
        labels = hazard_labels(validator, root)
        if "project-specific same-owner repository reference" not in labels:
            fail("same-owner non-public repository reference was not detected")

        (root / "README.md").write_text(
            ("gh" + "p_" + "A" * 40) + "\n",
            encoding="utf-8",
        )
        labels = hazard_labels(validator, root)
        if "github-classic-token" not in labels:
            fail("GitHub token fixture was not detected")

        (root / "README.md").write_text("clean again\n", encoding="utf-8")
        (root / "credentials.json").write_text("{}\n", encoding="utf-8")
        labels = hazard_labels(validator, root)
        if "sensitive credential/key path" not in labels:
            fail("sensitive credential path was not detected")

    print("PUBLICATION_GATE_SELF_TEST_PASS")


if __name__ == "__main__":
    main()
