"""Tests for GitHub API operations (story #4)."""

from unittest.mock import MagicMock, patch, PropertyMock

import pytest
from github import GithubException

from r2po_init.github import (
    get_token,
    create_client,
    create_repo,
    delete_repo,
    RepoExistsError,
    AuthError,
)
from r2po_init.constants import GITHUB_ORG


class TestGetToken:
    def test_should_return_token_when_gh_is_authenticated(self):
        with patch("r2po_init.github.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="ghp_testtoken123\n")
            assert get_token() == "ghp_testtoken123"

    def test_should_return_none_when_gh_returns_empty(self):
        with patch("r2po_init.github.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="")
            assert get_token() is None

    def test_should_return_none_when_gh_returns_whitespace(self):
        with patch("r2po_init.github.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="   \n")
            assert get_token() is None


class TestCreateRepo:
    def _make_client(self, side_effect=None, return_value=None):
        client = MagicMock()
        org = client.get_organization.return_value
        if side_effect:
            org.create_repo.side_effect = side_effect
        else:
            org.create_repo.return_value = return_value or MagicMock(
                html_url=f"https://github.com/{GITHUB_ORG}/test-repo",
                clone_url=f"https://github.com/{GITHUB_ORG}/test-repo.git",
            )
        return client

    def test_should_return_repo_on_success(self):
        mock_repo = MagicMock(html_url="https://github.com/NovaSoftworks/test-repo")
        client = self._make_client(return_value=mock_repo)

        result = create_repo(client, "test-repo", "A test repo")

        assert result.html_url == "https://github.com/NovaSoftworks/test-repo"
        client.get_organization.assert_called_once_with(GITHUB_ORG)
        client.get_organization().create_repo.assert_called_once_with(
            "test-repo", description="A test repo", private=True
        )

    def test_should_create_repo_as_private(self):
        client = self._make_client()
        create_repo(client, "test-repo", "desc")
        _, kwargs = client.get_organization().create_repo.call_args
        assert kwargs["private"] is True

    def test_should_raise_repo_exists_error_on_422_name_taken(self):
        exc = GithubException(
            422,
            data={"errors": [{"field": "name", "message": "name already exists"}]},
            headers={},
        )
        client = self._make_client(side_effect=exc)

        with pytest.raises(RepoExistsError, match="already exists"):
            create_repo(client, "existing-repo", "desc")

    def test_should_raise_auth_error_on_401(self):
        exc = GithubException(401, data={}, headers={})
        client = self._make_client(side_effect=exc)

        with pytest.raises(AuthError):
            create_repo(client, "test-repo", "desc")

    def test_should_raise_auth_error_on_403(self):
        exc = GithubException(403, data={}, headers={})
        client = self._make_client(side_effect=exc)

        with pytest.raises(AuthError):
            create_repo(client, "test-repo", "desc")

    def test_should_reraise_other_github_exceptions(self):
        exc = GithubException(500, data={}, headers={})
        client = self._make_client(side_effect=exc)

        with pytest.raises(GithubException):
            create_repo(client, "test-repo", "desc")


class TestDeleteRepo:
    def test_should_delete_existing_repo(self):
        client = MagicMock()
        delete_repo(client, "test-repo")
        client.get_organization().get_repo.assert_called_once_with("test-repo")
        client.get_organization().get_repo().delete.assert_called_once()

    def test_should_be_noop_when_repo_does_not_exist(self):
        client = MagicMock()
        client.get_organization().get_repo.side_effect = GithubException(404, data={}, headers={})
        # Should not raise.
        delete_repo(client, "nonexistent-repo")


class TestInitializerWithGitHub:
    """Integration tests for initializer.run() covering story #4 scenarios."""

    def _run(self, repo_name="test-repo", description="Test repo", **patches):
        from r2po_init import initializer
        steps = []

        with patch("r2po_init.initializer.gh.get_token", return_value="fake-token"), \
             patch("r2po_init.initializer.gh.create_client") as mock_client_factory, \
             patch("r2po_init.initializer.gh.create_repo", **patches.get("create_repo", {"return_value": MagicMock(html_url="https://github.com/NovaSoftworks/test-repo")})), \
             patch("r2po_init.initializer.gh.delete_repo"):
            result = initializer.run(repo_name, description, on_step=lambda s, ok: steps.append((s, ok)))

        return result, steps

    def test_should_return_success_when_repo_created(self):
        result, _ = self._run()
        assert result.success is True
        assert "test-repo" in result.repo_url

    def test_should_call_on_step_with_success_on_happy_path(self):
        _, steps = self._run()
        assert ("Create repository", True) in steps

    def test_should_return_failure_when_repo_already_exists(self):
        from r2po_init.github import RepoExistsError
        result, steps = self._run(**{"create_repo": {"side_effect": RepoExistsError("Repository 'test-repo' already exists in NovaSoftworks.")}})
        assert result.success is False
        assert "already exists" in result.error_message
        assert ("Create repository", False) in steps

    def test_should_return_failure_when_no_token(self):
        from r2po_init import initializer
        with patch("r2po_init.initializer.gh.get_token", return_value=None):
            result = initializer.run("test-repo", "desc")
        assert result.success is False
        assert "gh auth login" in result.error_message
