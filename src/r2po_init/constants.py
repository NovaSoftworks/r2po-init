"""Hardcoded configuration for r2po-init. All magic values live here."""

from dataclasses import dataclass
from pathlib import Path

GITHUB_ORG = "NovaSoftworks"
R2PO_TEAM_PATH = Path.home() / "ns" / "r2po" / "r2po-team"
FIRST_COMMIT_MESSAGE = "Initialize R2PO project structure"
ERROR_REPORT_FILENAME_PATTERN = "r2po-init-error-{timestamp}.txt"
GITHUB_API_RETRY_COUNT = 3
GITHUB_API_RETRY_DELAY_SECONDS = 2

REPO_NAME_PATTERN = r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$"
REPO_NAME_MAX_LENGTH = 100


@dataclass(frozen=True)
class LabelDefinition:
    """A standard R2PO GitHub label with its canonical color and description."""

    name: str
    color: str
    description: str
