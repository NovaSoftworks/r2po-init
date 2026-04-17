"""Tests for CLI argument parsing and validation (story #8)."""

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from r2po_init.cli import app, _is_valid_repo_name
from r2po_init.initializer import Result

runner = CliRunner()


class TestRepoNameValidation:
    def test_should_accept_lowercase_letters(self):
        assert _is_valid_repo_name("myproject") is True

    def test_should_accept_hyphens(self):
        assert _is_valid_repo_name("my-project") is True

    def test_should_accept_digits(self):
        assert _is_valid_repo_name("project2") is True

    def test_should_reject_uppercase(self):
        assert _is_valid_repo_name("MyProject") is False

    def test_should_reject_spaces(self):
        assert _is_valid_repo_name("my project") is False

    def test_should_reject_leading_hyphen(self):
        assert _is_valid_repo_name("-project") is False

    def test_should_reject_trailing_hyphen(self):
        assert _is_valid_repo_name("project-") is False

    def test_should_reject_name_over_100_chars(self):
        assert _is_valid_repo_name("a" * 101) is False

    def test_should_accept_single_character(self):
        assert _is_valid_repo_name("a") is True

    def test_should_reject_single_hyphen(self):
        assert _is_valid_repo_name("-") is False

    def test_should_accept_exactly_100_chars(self):
        assert _is_valid_repo_name("a" * 100) is True


class TestCliArgumentMode:
    def _mock_result(self, **kwargs):
        defaults = dict(
            success=True,
            repo_url="https://github.com/NovaSoftworks/test-repo",
            push_succeeded=True,
            push_error=None,
            error_message=None,
            error_report_path=None,
        )
        return Result(**{**defaults, **kwargs})

    def test_should_complete_without_prompts_when_name_provided(self):
        with patch("r2po_init.cli.initializer.run") as mock_run:
            mock_run.return_value = self._mock_result()
            result = runner.invoke(app, ["my-project"])
        assert result.exit_code == 0
        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args
        assert call_kwargs.args[0] == "my-project"

    def test_should_use_default_description_when_not_provided(self):
        with patch("r2po_init.cli.initializer.run") as mock_run:
            mock_run.return_value = self._mock_result()
            runner.invoke(app, ["my-project"])
        assert mock_run.call_args.args[1] == "R2PO project: my-project"

    def test_should_use_custom_description_when_provided(self):
        with patch("r2po_init.cli.initializer.run") as mock_run:
            mock_run.return_value = self._mock_result()
            runner.invoke(app, ["my-project", "--description", "Custom desc"])
        assert mock_run.call_args.args[1] == "Custom desc"

    def test_should_exit_1_on_invalid_name(self):
        result = runner.invoke(app, ["InvalidName"])
        assert result.exit_code != 0

    def test_should_not_call_initializer_on_invalid_name(self):
        with patch("r2po_init.cli.initializer.run") as mock_run:
            runner.invoke(app, ["InvalidName"])
        mock_run.assert_not_called()

    def test_should_exit_0_on_success(self):
        with patch("r2po_init.cli.initializer.run") as mock_run:
            mock_run.return_value = self._mock_result()
            result = runner.invoke(app, ["my-project"])
        assert result.exit_code == 0

    def test_should_exit_1_on_failure(self):
        with patch("r2po_init.cli.initializer.run") as mock_run:
            mock_run.return_value = self._mock_result(success=False, error_message="something failed")
            result = runner.invoke(app, ["my-project"])
        assert result.exit_code == 1

    def test_should_print_repo_url_on_success(self):
        with patch("r2po_init.cli.initializer.run") as mock_run:
            mock_run.return_value = self._mock_result(
                repo_url="https://github.com/NovaSoftworks/my-project"
            )
            result = runner.invoke(app, ["my-project"])
        assert "https://github.com/NovaSoftworks/my-project" in result.output

    def test_should_warn_but_exit_0_when_push_fails(self):
        with patch("r2po_init.cli.initializer.run") as mock_run:
            mock_run.return_value = self._mock_result(
                push_succeeded=False,
                push_error="authentication failed",
            )
            result = runner.invoke(app, ["my-project"])
        assert result.exit_code == 0
        assert "push failed" in result.output.lower()

    def test_should_show_help(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "repo-name" in result.output.lower() or "usage" in result.output.lower()
