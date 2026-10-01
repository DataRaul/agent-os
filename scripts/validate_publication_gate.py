from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {
    ".md", ".py", ".json", ".yml", ".yaml", ".toml", ".txt", ".ini", ".cfg",
    ".sh", ".bash", ".zsh", ".ps1", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs",
    ".sql", ".csv", ".xml", ".html", ".css", ".properties", ".conf", ".lock",
}
TEXT_BASENAMES = {"Dockerfile", "Makefile", "Procfile"}
SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules"}

OWNER = "Data" + "Raul"
PUBLIC_REPO = "agent" + "-os"
SAME_OWNER_REPO = re.compile(
    rf"(?<![A-Za-z0-9_.-]){re.escape(OWNER)}/([A-Za-z0-9_.-]+)",
    re.IGNORECASE,
)

SENSITIVE_BASENAMES = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.staging",
    ".env.development",
    "credentials.json",
    "service-account.json",
    "id_rsa",
    "id_ed25519",
}
SENSITIVE_SUFFIXES = {".pem", ".p12", ".pfx"}

SECRET_PATTERNS = {
    "private-key-block": re.compile(
        r"-----BEGIN " + r"(?:RSA |EC |OPENSSH )?" + r"PRIVATE KEY-----"
    ),
    "pgp-private-key-block": re.compile(
        r"-----BEGIN PGP " + r"PRIVATE KEY BLOCK-----"
    ),
    "github-classic-token": re.compile(r"gh" + r"p_[A-Za-z0-9]{30,}"),
    "github-fine-grained-token": re.compile(r"github" + r"_pat_[A-Za-z0-9_]{40,}"),
    "github-oauth-or-app-token": re.compile(
        r"gh" + r"(?:o|u|s|r)_[A-Za-z0-9]{30,}"
    ),
    "aws-access-key": re.compile(r"AK" + r"IA[0-9A-Z]{16}"),
    "google-api-key": re.compile(r"AI" + r"za[0-9A-Za-z_-]{35}"),
    "slack-token": re.compile(r"xox" + r"[aboprs]-[A-Za-z0-9-]{20,}"),
    "stripe-live-secret": re.compile(r"sk" + r"_live_[A-Za-z0-9]{20,}"),
    "api-secret": re.compile(r"sk" + r"-[A-Za-z0-9_-]{32,}"),
}


def fail(message: str) -> None:
    raise SystemExit(f"PUBLICATION_GATE_FAIL: {message}")


def _is_sensitive_path(path: Path) -> bool:
    name = path.name.lower()
    if name in SENSITIVE_BASENAMES:
        return True
    return path.suffix.lower() in SENSITIVE_SUFFIXES


def find_hazards(root: Path) -> list[str]:
    root = root.resolve()
    hazards: list[str] = []

    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        try:
            relative = path.relative_to(root)
        except ValueError:
            continue
        if any(part in SKIP_DIRS for part in relative.parts):
            continue

        if _is_sensitive_path(path):
            hazards.append(f"{relative}: sensitive credential/key path")

        if path.suffix.lower() not in TEXT_SUFFIXES and path.name not in TEXT_BASENAMES:
            continue

        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        for name, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                hazards.append(f"{relative}: {name}")

        for match in SAME_OWNER_REPO.finditer(text):
            if match.group(1).lower() != PUBLIC_REPO.lower():
                hazards.append(
                    f"{relative}: project-specific same-owner repository reference"
                )

    return sorted(set(hazards))


def main() -> None:
    hazards = find_hazards(ROOT)
    if hazards:
        fail("; ".join(hazards))
    print("PUBLICATION_GATE_PASS")


if __name__ == "__main__":
    main()
