"""Template discovery and file seeding for new R2PO project repositories."""

import re
import shutil
from datetime import date
from pathlib import Path

from .constants import LabelDefinition, R2PO_TEAM_PATH

_TEMPLATES_SUBDIR = Path("templates")
_ISSUE_TEMPLATE_SUBDIR = Path(".github") / "ISSUE_TEMPLATE"
_README = Path("README.md")

_LABEL_PATTERN = re.compile(
    r'gh label create (\S+) --color ([0-9a-f]+) --description "([^"]+)"'
)
_STATUS_HEREDOC_PATTERN = re.compile(
    r"cat > docs/status\.md << 'EOF'\n(.*?)\nEOF", re.DOTALL
)


class SourceNotFoundError(Exception):
    """Raised when the r2po-team source directory or required content is missing."""


def validate_source() -> None:
    """Verify the r2po-team directory and required source subdirectories exist.

    Checks for the root directory, the templates/ and .github/ISSUE_TEMPLATE/
    subdirectories, and the README.md used for label and status template parsing.

    Raises:
        SourceNotFoundError: If anything required is missing.
    """
    if not R2PO_TEAM_PATH.is_dir():
        raise SourceNotFoundError(
            f"r2po-team directory not found at {R2PO_TEAM_PATH}\n"
            "Ensure the r2po-team repo is cloned at ~/ns/r2po/r2po-team"
        )
    for subdir in (_TEMPLATES_SUBDIR, _ISSUE_TEMPLATE_SUBDIR):
        path = R2PO_TEAM_PATH / subdir
        if not path.is_dir():
            raise SourceNotFoundError(f"Missing source directory in r2po-team: {path}")
    readme = R2PO_TEAM_PATH / _README
    if not readme.exists():
        raise SourceNotFoundError(f"README.md not found in r2po-team: {readme}")


def discover_templates() -> list[tuple[Path, Path]]:
    """Return (absolute_source, relative_dest) pairs for all template files to seed.

    Scans r2po-team directories at runtime so no hardcoded file list is needed.
    Files in templates/ map to docs/; issue templates map to .github/ISSUE_TEMPLATE/.

    Returns:
        Sorted list of (source_path, relative_dest_path) tuples.
    """
    pairs: list[tuple[Path, Path]] = []
    for src in sorted((R2PO_TEAM_PATH / _TEMPLATES_SUBDIR).glob("*.md")):
        pairs.append((src, Path("docs") / src.name))
    for src in sorted((R2PO_TEAM_PATH / _ISSUE_TEMPLATE_SUBDIR).glob("*.md")):
        pairs.append((src, _ISSUE_TEMPLATE_SUBDIR / src.name))
    return pairs


def parse_labels() -> list[LabelDefinition]:
    """Parse label definitions from r2po-team README.md.

    Extracts all ``gh label create`` command lines using regex. This means label
    changes in r2po-team require no code change in r2po-init.

    Returns:
        List of LabelDefinition instances in the order they appear in the README.

    Raises:
        SourceNotFoundError: If README is missing or contains no label definitions.
    """
    readme = R2PO_TEAM_PATH / _README
    try:
        text = readme.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise SourceNotFoundError(f"README.md not found in r2po-team: {readme}")

    matches = _LABEL_PATTERN.findall(text)
    if not matches:
        raise SourceNotFoundError(
            f"No label definitions found in {readme}\n"
            'Expected lines like: gh label create <name> --color <hex> --description "<desc>"'
        )
    return [LabelDefinition(name=name, color=color, description=desc)
            for name, color, desc in matches]


def parse_status_template() -> str:
    """Extract the status.md template from r2po-team README.md.

    Finds the heredoc block that creates docs/status.md and returns its content
    with ``[date]`` replaced by the Python format placeholder ``{date}``.

    Returns:
        Template string ready for ``.format(date=...)`` substitution.

    Raises:
        SourceNotFoundError: If README is missing or the heredoc block is not found.
    """
    readme = R2PO_TEAM_PATH / _README
    try:
        text = readme.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise SourceNotFoundError(f"README.md not found in r2po-team: {readme}")

    match = _STATUS_HEREDOC_PATTERN.search(text)
    if not match:
        raise SourceNotFoundError(
            f"No status.md template found in {readme}\n"
            "Expected a heredoc block: cat > docs/status.md << 'EOF' ... EOF"
        )
    return match.group(1).replace("[date]", "{date}")


def seed(dest: Path, repo_name: str, description: str) -> None:
    """Copy all template files into dest and generate status.md and CLAUDE.md.

    Template files are discovered dynamically from r2po-team at call time.

    Args:
        dest: Root of the local repository working directory.
        repo_name: Repository name, used in the generated CLAUDE.md.
        description: Repository description, used in the generated CLAUDE.md.

    Raises:
        SourceNotFoundError: If a source file is missing at copy time or
            the README cannot be parsed.
    """
    seeded_docs: list[Path] = []

    for src, rel_dest in discover_templates():
        target = dest / rel_dest
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)
        if rel_dest.parts[0] == "docs":
            seeded_docs.append(rel_dest)

    docs_dir = dest / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    status_template = parse_status_template()
    (docs_dir / "status.md").write_text(
        status_template.format(date=date.today().isoformat()),
        encoding="utf-8",
    )
    seeded_docs.insert(0, Path("docs/status.md"))

    (dest / "CLAUDE.md").write_text(
        _build_claude_md(repo_name, description, seeded_docs),
        encoding="utf-8",
    )


def _build_claude_md(repo_name: str, description: str, seeded_docs: list[Path]) -> str:
    """Generate CLAUDE.md content listing the documents that were actually seeded."""
    doc_list = "\n".join(f"  {p}" for p in seeded_docs)
    return (
        f"# Project: {repo_name}\n\n"
        f"{description}\n\n"
        "Team instructions: https://github.com/NovaSoftworks/r2po-team/blob/main/CLAUDE.md\n"
        "Workflow: https://github.com/NovaSoftworks/r2po-team/blob/main/workflow.md\n"
        "Current state: see docs/status.md\n\n"
        f"## Documents\n\n{doc_list}\n"
    )
