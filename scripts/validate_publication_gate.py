from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {".md", ".py", ".json", ".yml", ".yaml", ".toml", ".txt", ".ini", ".cfg"}
SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules"}

OWNER = "Data" + "Raul"
PUBLIC_REPO = "agent" + "-os"
SAME_OWNER_REPO = re.compile(
    rf"(?<![A-Za-z0-9_.-]){re.escape(OWNER)}/([A-Za-z0-9_.-]+)"
)


def fail(message: str) -> None:
    raise SystemExit(f"PUBLICATION_GATE_FAIL: {message}")


def main() -> None:
    hazards: list[str] = []

    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue

        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        for match in SAME_OWNER_REPO.finditer(text):
            if match.group(1) != PUBLIC_REPO:
                hazards.append(
                    f"{path.relative_to(ROOT)}: project-specific same-owner repository reference"
                )

    if hazards:
        fail("; ".join(sorted(set(hazards))))

    print("PUBLICATION_GATE_PASS")


if __name__ == "__main__":
    main()
