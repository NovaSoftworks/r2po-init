"""Tests for git commit and push operations (story #7)."""

import shutil
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from r2po_init.git import commit_and_push

# Capture before any patching so the side_effect can call through to the real function.
_real_subprocess_run = subprocess.run


def _push_interceptor(push_returncode: int = 0, push_stderr: str = ""):
    """Return a subprocess.run side_effect that runs real git commands but mocks push."""
    def side_effect(args, **kwargs):
        if isinstance(args, list) and args[:3] == ["git", "push", "-u"]:
            return MagicMock(returncode=push_returncode, stderr=push_stderr)
        return _real_subprocess_run(args, **kwargs)
    return side_effect


class TestCommitAndPush:
    def setup_method(self):
        self.repo_path = Path(tempfile.mkdtemp())
        (self.repo_path / "README.md").write_text("# Test\n")

    def teardown_method(self):
        shutil.rmtree(self.repo_path, ignore_errors=True)

    def test_should_create_commit_on_main_branch(self):
        with patch("r2po_init.git.subprocess.run", side_effect=_push_interceptor()):
            commit_and_push(
                self.repo_path, "https://github.com/NovaSoftworks/test.git",
                "fake-token", "Test commit"
            )

        log = _real_subprocess_run(
            ["git", "log", "--oneline"],
            cwd=self.repo_path, capture_output=True, text=True
        )
        assert "Test commit" in log.stdout

    def test_should_commit_on_main_branch_not_master(self):
        with patch("r2po_init.git.subprocess.run", side_effect=_push_interceptor()):
            commit_and_push(
                self.repo_path, "https://github.com/NovaSoftworks/test.git",
                "fake-token", "Test commit"
            )

        branch = _real_subprocess_run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=self.repo_path, capture_output=True, text=True
        )
        assert branch.stdout.strip() == "main"

    def test_should_commit_using_provided_message(self):
        with patch("r2po_init.git.subprocess.run", side_effect=_push_interceptor()):
            commit_and_push(
                self.repo_path, "https://github.com/NovaSoftworks/test.git",
                "fake-token", "Initialize R2PO project structure"
            )

        log = _real_subprocess_run(
            ["git", "log", "--format=%s"],
            cwd=self.repo_path, capture_output=True, text=True
        )
        assert "Initialize R2PO project structure" in log.stdout

    def test_should_return_pushed_true_when_push_succeeds(self):
        with patch("r2po_init.git.subprocess.run", side_effect=_push_interceptor(0)):
            result = commit_and_push(
                self.repo_path, "https://github.com/NovaSoftworks/test.git",
                "fake-token", "Test commit"
            )
        assert result.committed is True
        assert result.pushed is True
        assert result.push_error is None

    def test_should_return_pushed_false_when_push_fails(self):
        with patch("r2po_init.git.subprocess.run",
                   side_effect=_push_interceptor(128, "fatal: authentication failed\n")):
            result = commit_and_push(
                self.repo_path, "https://github.com/NovaSoftworks/test.git",
                "fake-token", "Test commit"
            )
        assert result.committed is True
        assert result.pushed is False
        assert "authentication failed" in result.push_error

    def test_should_not_raise_when_push_fails(self):
        with patch("r2po_init.git.subprocess.run",
                   side_effect=_push_interceptor(1, "error\n")):
            # Should not raise — push failure is non-fatal per BR-009.
            result = commit_and_push(
                self.repo_path, "https://github.com/NovaSoftworks/test.git",
                "fake-token", "Test commit"
            )
        assert result.committed is True

    def test_should_remove_credential_file_after_successful_push(self):
        with patch("r2po_init.git.subprocess.run", side_effect=_push_interceptor(0)):
            commit_and_push(
                self.repo_path, "https://github.com/NovaSoftworks/test.git",
                "fake-token", "Test commit"
            )
        assert not (self.repo_path / ".git-credentials").exists()

    def test_should_remove_credential_file_even_when_push_fails(self):
        with patch("r2po_init.git.subprocess.run",
                   side_effect=_push_interceptor(1, "error\n")):
            commit_and_push(
                self.repo_path, "https://github.com/NovaSoftworks/test.git",
                "fake-token", "Test commit"
            )
        assert not (self.repo_path / ".git-credentials").exists()


class TestInitializerFullHappyPath:
    """End-to-end initializer tests covering the complete iteration-1 happy path."""

    def _run_with_mocks(self, push_succeeded=True, push_error=None):
        from r2po_init import initializer

        steps = []
        mock_repo = MagicMock(
            html_url="https://github.com/NovaSoftworks/test-proj",
            clone_url="https://github.com/NovaSoftworks/test-proj.git",
        )

        with patch("r2po_init.initializer.templates.validate_source"), \
             patch("r2po_init.initializer.gh.get_token", return_value="fake-token"), \
             patch("r2po_init.initializer.gh.create_client"), \
             patch("r2po_init.initializer.gh.create_repo", return_value=mock_repo), \
             patch("r2po_init.initializer.gh.apply_labels"), \
             patch("r2po_init.initializer.templates.seed"), \
             patch("r2po_init.initializer.git_ops.commit_and_push",
                   return_value=MagicMock(
                       committed=True, pushed=push_succeeded, push_error=push_error
                   )):
            result = initializer.run(
                "test-proj", "desc",
                on_step=lambda s, ok: steps.append((s, ok))
            )

        return result, steps

    def test_should_succeed_on_full_happy_path(self):
        result, _ = self._run_with_mocks()
        assert result.success is True
        assert result.push_succeeded is True

    def test_should_fire_all_three_steps_on_happy_path(self):
        _, steps = self._run_with_mocks()
        step_names = [name for name, _ in steps]
        assert "Create repository" in step_names
        assert "Seed templates" in step_names
        assert "Commit and push" in step_names

    def test_should_succeed_even_when_push_fails(self):
        result, _ = self._run_with_mocks(push_succeeded=False, push_error="auth failed")
        assert result.success is True
        assert result.push_succeeded is False
        assert result.push_error == "auth failed"
