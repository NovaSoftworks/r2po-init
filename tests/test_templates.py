"""Tests for dynamic template discovery and seeding (stories #6, #15, #16, #17)."""

import shutil
import tempfile
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest

from r2po_init.templates import (
    validate_source,
    discover_templates,
    parse_labels,
    parse_status_template,
    seed,
    SourceNotFoundError,
)
from r2po_init.constants import R2PO_TEAM_PATH


def _make_fake_team(tmp: str, *, templates=("functional-spec.md",),
                    issue_templates=("epic.md",), readme_content=None,
                    labels=None) -> Path:
    """Build a minimal fake r2po-team directory for testing."""
    root = Path(tmp)
    (root / "templates").mkdir(parents=True)
    (root / ".github" / "ISSUE_TEMPLATE").mkdir(parents=True)
    for name in templates:
        (root / "templates" / name).write_text(f"# {name}")
    for name in issue_templates:
        (root / ".github" / "ISSUE_TEMPLATE" / name).write_text(f"# {name}")
    if readme_content is None:
        readme_content = _minimal_readme(labels=labels)
    (root / "README.md").write_text(readme_content)
    return root


def _minimal_readme(labels=None) -> str:
    """Return a README with at least one label and a status.md heredoc."""
    if labels is None:
        labels = [('epic', '0075ca', 'Major capability or goal')]
    label_lines = "\n".join(
        f'gh label create {n} --color {c} --description "{d}" --force'
        for n, c, d in labels
    )
    return (
        "# r2po-team\n\n"
        "## Starting a new project\n\n"
        "```bash\n"
        f"{label_lines}\n\n"
        "cat > docs/status.md << 'EOF'\n"
        "# Project Status\n\n"
        "Phase: 1 - awaiting Gate 1\n"
        "Last updated: [date]\n"
        "EOF\n"
        "```\n"
    )


class TestValidateSource:
    def test_should_pass_against_real_r2po_team(self):
        validate_source()  # Real r2po-team on this machine — should not raise.

    def test_should_raise_when_r2po_team_dir_missing(self):
        with patch("r2po_init.templates.R2PO_TEAM_PATH", Path("/nonexistent/path")):
            with pytest.raises(SourceNotFoundError, match="r2po-team directory not found"):
                validate_source()

    def test_error_message_includes_path(self):
        with patch("r2po_init.templates.R2PO_TEAM_PATH", Path("/nonexistent/path")):
            with pytest.raises(SourceNotFoundError) as exc_info:
                validate_source()
        assert "/nonexistent/path" in str(exc_info.value)

    def test_should_raise_when_templates_subdir_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".github" / "ISSUE_TEMPLATE").mkdir(parents=True)
            (root / "README.md").write_text("x")
            with patch("r2po_init.templates.R2PO_TEAM_PATH", root):
                with pytest.raises(SourceNotFoundError, match="Missing source directory"):
                    validate_source()

    def test_should_raise_when_issue_template_subdir_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "templates").mkdir()
            (root / "README.md").write_text("x")
            with patch("r2po_init.templates.R2PO_TEAM_PATH", root):
                with pytest.raises(SourceNotFoundError, match="Missing source directory"):
                    validate_source()

    def test_should_raise_when_readme_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "templates").mkdir()
            (root / ".github" / "ISSUE_TEMPLATE").mkdir(parents=True)
            with patch("r2po_init.templates.R2PO_TEAM_PATH", root):
                with pytest.raises(SourceNotFoundError, match="README.md not found"):
                    validate_source()


class TestDiscoverTemplates:
    def test_should_map_templates_to_docs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_fake_team(tmp, templates=["functional-spec.md"])
            with patch("r2po_init.templates.R2PO_TEAM_PATH", root):
                pairs = discover_templates()
        dests = [str(dest) for _, dest in pairs]
        assert "docs/functional-spec.md" in dests

    def test_should_map_issue_templates_to_github_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_fake_team(tmp, issue_templates=["epic.md"])
            with patch("r2po_init.templates.R2PO_TEAM_PATH", root):
                pairs = discover_templates()
        dests = [str(dest) for _, dest in pairs]
        assert ".github/ISSUE_TEMPLATE/epic.md" in dests

    def test_should_discover_all_md_files_in_templates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_fake_team(tmp, templates=["a.md", "b.md", "c.md"])
            with patch("r2po_init.templates.R2PO_TEAM_PATH", root):
                pairs = discover_templates()
        doc_dests = [dest for _, dest in pairs if dest.parts[0] == "docs"]
        assert len(doc_dests) == 3

    def test_should_discover_all_md_files_in_issue_templates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_fake_team(tmp, issue_templates=["epic.md", "story.md", "bug.md"])
            with patch("r2po_init.templates.R2PO_TEAM_PATH", root):
                pairs = discover_templates()
        issue_dests = [dest for _, dest in pairs if dest.parts[0] == ".github"]
        assert len(issue_dests) == 3

    def test_should_return_empty_when_no_md_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_fake_team(tmp, templates=[], issue_templates=[])
            with patch("r2po_init.templates.R2PO_TEAM_PATH", root):
                pairs = discover_templates()
        assert pairs == []

    def test_should_use_real_r2po_team_files(self):
        pairs = discover_templates()
        assert len(pairs) > 0


class TestParseLabels:
    def test_should_parse_single_label(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_fake_team(tmp, labels=[("epic", "0075ca", "Major capability")])
            with patch("r2po_init.templates.R2PO_TEAM_PATH", root):
                labels = parse_labels()
        assert len(labels) == 1
        assert labels[0].name == "epic"
        assert labels[0].color == "0075ca"
        assert labels[0].description == "Major capability"

    def test_should_parse_multiple_labels(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_fake_team(tmp, labels=[
                ("epic", "0075ca", "Goal"),
                ("story", "e4e669", "Feature"),
                ("bug", "d73a4a", "Defect"),
            ])
            with patch("r2po_init.templates.R2PO_TEAM_PATH", root):
                labels = parse_labels()
        assert len(labels) == 3
        names = [l.name for l in labels]
        assert names == ["epic", "story", "bug"]

    def test_should_raise_when_no_labels_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_fake_team(tmp)
            (root / "README.md").write_text("# No labels here")
            with patch("r2po_init.templates.R2PO_TEAM_PATH", root):
                with pytest.raises(SourceNotFoundError, match="No label definitions"):
                    parse_labels()

    def test_should_raise_when_readme_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "templates").mkdir()
            with patch("r2po_init.templates.R2PO_TEAM_PATH", root):
                with pytest.raises(SourceNotFoundError, match="README.md not found"):
                    parse_labels()

    def test_should_parse_real_r2po_team_labels(self):
        labels = parse_labels()
        assert len(labels) > 0
        names = [l.name for l in labels]
        assert "epic" in names


class TestParseStatusTemplate:
    def test_should_extract_heredoc_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_fake_team(tmp)
            with patch("r2po_init.templates.R2PO_TEAM_PATH", root):
                template = parse_status_template()
        assert "Phase: 1" in template

    def test_should_replace_date_placeholder(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_fake_team(tmp)
            with patch("r2po_init.templates.R2PO_TEAM_PATH", root):
                template = parse_status_template()
        assert "{date}" in template
        assert "[date]" not in template

    def test_should_raise_when_heredoc_not_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_fake_team(tmp)
            (root / "README.md").write_text("# No heredoc here")
            with patch("r2po_init.templates.R2PO_TEAM_PATH", root):
                with pytest.raises(SourceNotFoundError, match="No status.md template"):
                    parse_status_template()

    def test_should_raise_when_readme_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch("r2po_init.templates.R2PO_TEAM_PATH", root):
                with pytest.raises(SourceNotFoundError, match="README.md not found"):
                    parse_status_template()

    def test_should_parse_real_r2po_team_status_template(self):
        template = parse_status_template()
        assert "{date}" in template
        assert len(template) > 10


class TestSeed:
    def setup_method(self):
        self.dest = Path(tempfile.mkdtemp())

    def teardown_method(self):
        shutil.rmtree(self.dest, ignore_errors=True)

    def test_should_copy_issue_templates(self):
        seed(self.dest, "my-project", "A project")
        issue_dir = self.dest / ".github" / "ISSUE_TEMPLATE"
        assert issue_dir.is_dir()
        md_files = list(issue_dir.glob("*.md"))
        assert len(md_files) > 0

    def test_should_copy_doc_templates_to_docs(self):
        seed(self.dest, "my-project", "A project")
        docs_dir = self.dest / "docs"
        assert docs_dir.is_dir()
        md_files = list(docs_dir.glob("*.md"))
        assert len(md_files) > 0  # at least status.md + whatever templates/ has

    def test_should_generate_status_md_with_todays_date(self):
        seed(self.dest, "my-project", "A project")
        content = (self.dest / "docs" / "status.md").read_text()
        assert date.today().isoformat() in content

    def test_should_generate_status_md_without_date_placeholder(self):
        seed(self.dest, "my-project", "A project")
        content = (self.dest / "docs" / "status.md").read_text()
        assert "[date]" not in content

    def test_should_generate_claude_md_with_repo_name(self):
        seed(self.dest, "my-project", "A project")
        content = (self.dest / "CLAUDE.md").read_text()
        assert "my-project" in content

    def test_should_generate_claude_md_with_description(self):
        seed(self.dest, "my-project", "A project description")
        content = (self.dest / "CLAUDE.md").read_text()
        assert "A project description" in content

    def test_should_generate_claude_md_with_github_urls(self):
        seed(self.dest, "my-project", "desc")
        content = (self.dest / "CLAUDE.md").read_text()
        assert "https://github.com/NovaSoftworks/r2po-team/blob/main/CLAUDE.md" in content
        assert "https://github.com/NovaSoftworks/r2po-team/blob/main/workflow.md" in content

    def test_should_list_seeded_docs_in_claude_md(self):
        seed(self.dest, "my-project", "desc")
        content = (self.dest / "CLAUDE.md").read_text()
        assert "docs/status.md" in content

    def test_should_match_discovered_template_count(self):
        """Files seeded should equal discovered templates + status.md + CLAUDE.md."""
        discovered = discover_templates()
        seed(self.dest, "my-project", "desc")
        all_files = [p for p in self.dest.rglob("*") if p.is_file()]
        # discovered files + status.md + CLAUDE.md
        assert len(all_files) == len(discovered) + 2
