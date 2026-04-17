"""Tests for template seeding (story #6)."""

import shutil
import tempfile
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest

from r2po_init.templates import validate_source, seed, SourceNotFoundError
from r2po_init.constants import TEMPLATE_FILES, R2PO_TEAM_PATH


class TestValidateSource:
    def test_should_pass_when_r2po_team_exists_with_all_files(self):
        # The actual r2po-team repo exists on this machine — this is a real check.
        validate_source()  # Should not raise.

    def test_should_raise_when_r2po_team_dir_missing(self):
        with patch("r2po_init.templates.R2PO_TEAM_PATH", Path("/nonexistent/path")):
            with pytest.raises(SourceNotFoundError, match="r2po-team directory not found"):
                validate_source()

    def test_should_raise_when_a_template_file_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake_team = Path(tmp)
            # Create the directory but none of the files.
            with patch("r2po_init.templates.R2PO_TEAM_PATH", fake_team), \
                 patch("r2po_init.templates.TEMPLATE_FILES", TEMPLATE_FILES[:1]):
                with pytest.raises(SourceNotFoundError, match="Missing template file"):
                    validate_source()

    def test_error_message_includes_expected_path(self):
        with patch("r2po_init.templates.R2PO_TEAM_PATH", Path("/nonexistent/path")):
            with pytest.raises(SourceNotFoundError) as exc_info:
                validate_source()
        assert "/nonexistent/path" in str(exc_info.value)


class TestSeed:
    def setup_method(self):
        self.dest = Path(tempfile.mkdtemp())

    def teardown_method(self):
        shutil.rmtree(self.dest, ignore_errors=True)

    def test_should_copy_all_issue_templates(self):
        seed(self.dest, "my-project", "A project")
        for name in ("epic.md", "story.md", "spike.md", "bug.md"):
            assert (self.dest / ".github" / "ISSUE_TEMPLATE" / name).exists(), f"Missing {name}"

    def test_should_copy_all_doc_templates(self):
        seed(self.dest, "my-project", "A project")
        expected = [
            "docs/functional-spec.md",
            "docs/architecture/system.md",
            "docs/architecture/platform.md",
            "docs/test-plan.md",
            "docs/test-report.md",
        ]
        for path in expected:
            assert (self.dest / path).exists(), f"Missing {path}"

    def test_should_generate_status_md_with_phase_1(self):
        seed(self.dest, "my-project", "A project")
        content = (self.dest / "docs" / "status.md").read_text()
        assert "Phase: 1 - Discovery" in content

    def test_should_generate_status_md_with_todays_date(self):
        seed(self.dest, "my-project", "A project")
        content = (self.dest / "docs" / "status.md").read_text()
        assert date.today().isoformat() in content

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

    def test_should_produce_exactly_11_files(self):
        seed(self.dest, "my-project", "desc")
        all_files = [p for p in self.dest.rglob("*") if p.is_file()]
        assert len(all_files) == 11, f"Expected 11 files, got {len(all_files)}: {all_files}"
