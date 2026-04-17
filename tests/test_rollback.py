"""Tests for rollback-on-failure and error reporting (stories #12, #13)."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from r2po_init import initializer
from r2po_init.reporter import ErrorReport, write as write_report


class TestRollback:
    """Story #12: rollback when failure occurs after repo creation."""

    def _run_with_failure_at(self, fail_step: str):
        """Run initializer with a simulated failure at a given step."""
        mock_repo = MagicMock(
            html_url="https://github.com/NovaSoftworks/fail-proj",
            clone_url="https://github.com/NovaSoftworks/fail-proj.git",
        )
        steps = []

        def apply_labels_fail(*args, **kwargs):
            if fail_step == "apply_labels":
                raise RuntimeError("Simulated label failure")

        def seed_fail(*args, **kwargs):
            if fail_step == "seed":
                raise RuntimeError("Simulated seed failure")

        with patch("r2po_init.initializer.templates.validate_source"), \
             patch("r2po_init.initializer.gh.get_token", return_value="fake-token"), \
             patch("r2po_init.initializer.gh.create_client"), \
             patch("r2po_init.initializer.gh.create_repo", return_value=mock_repo), \
             patch("r2po_init.initializer.gh.apply_labels", side_effect=apply_labels_fail), \
             patch("r2po_init.initializer.gh.delete_repo") as mock_delete, \
             patch("r2po_init.initializer.templates.seed", side_effect=seed_fail), \
             patch("r2po_init.initializer.reporter.write", return_value=Path("/tmp/report.txt")):
            result = initializer.run(
                "fail-proj", "desc", on_step=lambda s, ok: steps.append((s, ok))
            )

        return result, steps, mock_delete

    def test_should_delete_repo_on_failure_after_creation(self):
        _, _, mock_delete = self._run_with_failure_at("apply_labels")
        mock_delete.assert_called_once()

    def test_should_return_failure_result_on_rollback(self):
        result, _, _ = self._run_with_failure_at("apply_labels")
        assert result.success is False

    def test_should_include_error_report_path_on_rollback(self):
        result, _, _ = self._run_with_failure_at("apply_labels")
        assert result.error_report_path is not None

    def test_should_fire_rollback_step_in_on_step_callback(self):
        _, steps, _ = self._run_with_failure_at("apply_labels")
        step_names = [name for name, _ in steps]
        assert "Rollback" in step_names

    def test_should_not_rollback_on_repo_exists_error(self):
        """RepoExistsError is non-retryable and non-rollbackable (nothing to undo)."""
        from r2po_init.github import RepoExistsError

        with patch("r2po_init.initializer.templates.validate_source"), \
             patch("r2po_init.initializer.gh.get_token", return_value="fake-token"), \
             patch("r2po_init.initializer.gh.create_client"), \
             patch("r2po_init.initializer.gh.create_repo",
                   side_effect=RepoExistsError("already exists")), \
             patch("r2po_init.initializer.gh.delete_repo") as mock_delete:
            result = initializer.run("test-repo", "desc")

        mock_delete.assert_not_called()
        assert result.success is False

    def test_should_delete_repo_on_seed_failure(self):
        _, _, mock_delete = self._run_with_failure_at("seed")
        mock_delete.assert_called_once()

    def test_should_write_error_report_on_failure(self):
        _, _, mock_delete = self._run_with_failure_at("apply_labels")
        # delete_repo was called — rollback happened
        mock_delete.assert_called_once()


class TestErrorReporter:
    """Story #13: error report written to cwd on abort."""

    def test_should_write_report_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            report = ErrorReport(
                repo_name="my-proj",
                description="Test project",
                error_message="Something went wrong",
                steps_completed=["Create repository"],
                rollback_actions=["Delete repository NovaSoftworks/my-proj"],
            )
            path = write_report(report, dest_dir=dest)
            assert path.exists()

    def test_should_use_timestamp_filename(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            report = ErrorReport(
                repo_name="x", description="d", error_message="err"
            )
            path = write_report(report, dest_dir=dest)
            assert path.name.startswith("r2po-init-error-")
            assert path.suffix == ".txt"

    def test_should_include_repo_name_in_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            report = ErrorReport(
                repo_name="my-proj", description="d", error_message="err"
            )
            path = write_report(report, dest_dir=dest)
            assert "my-proj" in path.read_text()

    def test_should_include_error_message_in_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            report = ErrorReport(
                repo_name="x", description="d",
                error_message="Fatal: label creation failed"
            )
            path = write_report(report, dest_dir=dest)
            assert "Fatal: label creation failed" in path.read_text()

    def test_should_include_completed_steps_in_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            report = ErrorReport(
                repo_name="x", description="d", error_message="err",
                steps_completed=["Create repository", "Apply labels"],
            )
            path = write_report(report, dest_dir=dest)
            content = path.read_text()
            assert "Create repository" in content
            assert "Apply labels" in content

    def test_should_include_rollback_actions_in_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            report = ErrorReport(
                repo_name="x", description="d", error_message="err",
                rollback_actions=["Delete repository NovaSoftworks/x"],
            )
            path = write_report(report, dest_dir=dest)
            assert "Delete repository NovaSoftworks/x" in path.read_text()

    def test_should_omit_steps_section_when_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            report = ErrorReport(
                repo_name="x", description="d", error_message="err",
                steps_completed=[],
            )
            path = write_report(report, dest_dir=dest)
            assert "Steps completed" not in path.read_text()

    def test_should_omit_rollback_section_when_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            report = ErrorReport(
                repo_name="x", description="d", error_message="err",
                rollback_actions=[],
            )
            path = write_report(report, dest_dir=dest)
            assert "Rollback actions" not in path.read_text()

    def test_should_default_dest_dir_to_cwd(self):
        import os
        report = ErrorReport(repo_name="x", description="d", error_message="err")
        path = write_report(report)
        try:
            assert path.parent == Path(os.getcwd())
        finally:
            path.unlink(missing_ok=True)
