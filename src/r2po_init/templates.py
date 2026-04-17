"""Template discovery and file seeding for new R2PO project repositories."""

import shutil
from datetime import date
from pathlib import Path

from .constants import (
    CLAUDE_MD_TEMPLATE,
    R2PO_TEAM_PATH,
    STATUS_MD_TEMPLATE,
    TEMPLATE_FILES,
)


class SourceNotFoundError(Exception):
    """Raised when the r2po-team source directory or a required template is missing."""


def validate_source() -> None:
    """Verify the r2po-team source directory and all required template files exist.

    Raises:
        SourceNotFoundError: If the source directory or any template file is missing.
    """
    if not R2PO_TEAM_PATH.is_dir():
        raise SourceNotFoundError(
            f"r2po-team directory not found at {R2PO_TEAM_PATH}\n"
            "Ensure the r2po-team repo is cloned at ~/ns/r2po/r2po-team"
        )
    for tmpl in TEMPLATE_FILES:
        src = R2PO_TEAM_PATH / tmpl.source
        if not src.exists():
            raise SourceNotFoundError(f"Missing template file: {src}")


def seed(dest: Path, repo_name: str, description: str) -> None:
    """Copy all template files into dest and generate status.md and CLAUDE.md.

    Args:
        dest: Root of the local repository working directory.
        repo_name: Repository name, used in the generated CLAUDE.md.
        description: Repository description, used in the generated CLAUDE.md.

    Raises:
        SourceNotFoundError: If a source file is missing at copy time.
    """
    for tmpl in TEMPLATE_FILES:
        src = R2PO_TEAM_PATH / tmpl.source
        target = dest / tmpl.dest
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)

    docs_dir = dest / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    (docs_dir / "status.md").write_text(
        STATUS_MD_TEMPLATE.format(date=date.today().isoformat()),
        encoding="utf-8",
    )
    (dest / "CLAUDE.md").write_text(
        CLAUDE_MD_TEMPLATE.format(repo_name=repo_name, description=description),
        encoding="utf-8",
    )
