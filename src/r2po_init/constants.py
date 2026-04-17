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


R2PO_LABELS: list[LabelDefinition] = [
    LabelDefinition("epic", "0075ca", "Major capability or goal"),
    LabelDefinition("story", "e4e669", "Single unit of user-facing functionality"),
    LabelDefinition("spike", "d876e3", "Time-boxed investigation"),
    LabelDefinition("bug", "d73a4a", "Defect found during QA or review"),
    LabelDefinition("blocked", "b60205", "Cannot progress"),
    LabelDefinition("needs-review", "0e8a16", "Waiting for human approval"),
]


@dataclass(frozen=True)
class TemplateFile:
    """Maps a source file in r2po-team to its destination path in the new repo."""

    source: Path  # relative to R2PO_TEAM_PATH
    dest: Path    # relative to repo root


TEMPLATE_FILES: list[TemplateFile] = [
    # Issue templates
    TemplateFile(
        source=Path(".github/ISSUE_TEMPLATE/epic.md"),
        dest=Path(".github/ISSUE_TEMPLATE/epic.md"),
    ),
    TemplateFile(
        source=Path(".github/ISSUE_TEMPLATE/story.md"),
        dest=Path(".github/ISSUE_TEMPLATE/story.md"),
    ),
    TemplateFile(
        source=Path(".github/ISSUE_TEMPLATE/spike.md"),
        dest=Path(".github/ISSUE_TEMPLATE/spike.md"),
    ),
    TemplateFile(
        source=Path(".github/ISSUE_TEMPLATE/bug.md"),
        dest=Path(".github/ISSUE_TEMPLATE/bug.md"),
    ),
    # Doc templates (source uses hyphenated names, dest uses subdirectory structure)
    TemplateFile(
        source=Path("templates/functional-spec.md"),
        dest=Path("docs/functional-spec.md"),
    ),
    TemplateFile(
        source=Path("templates/architecture-system.md"),
        dest=Path("docs/architecture/system.md"),
    ),
    TemplateFile(
        source=Path("templates/architecture-platform.md"),
        dest=Path("docs/architecture/platform.md"),
    ),
    TemplateFile(
        source=Path("templates/test-plan.md"),
        dest=Path("docs/test-plan.md"),
    ),
    TemplateFile(
        source=Path("templates/test-report.md"),
        dest=Path("docs/test-report.md"),
    ),
]

STATUS_MD_TEMPLATE = """\
# Project Status

Phase: 1 - Discovery
Iteration: pre-iteration
Last updated: {date}

## Current state

Project just initialized. Waiting for Phase 1 to begin.

## Pending approvals

Epics - not yet written.

## Blockers

None.
"""

CLAUDE_MD_TEMPLATE = """\
# Project: {repo_name}

{description}

Tech stack: to be determined in Phase 2.
Target environment: WSL2, run locally by the developer.

Team instructions: https://github.com/NovaSoftworks/r2po-team/blob/main/CLAUDE.md
Workflow: https://github.com/NovaSoftworks/r2po-team/blob/main/workflow.md
Current state: see docs/status.md
"""
