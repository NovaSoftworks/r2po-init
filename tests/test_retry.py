"""Tests for transient-error retry logic (story #11)."""

from unittest.mock import MagicMock, call, patch

import pytest
from github import GithubException

from r2po_init.github import _retryable_api_call, create_repo, apply_labels
from r2po_init.constants import GITHUB_API_RETRY_COUNT, GITHUB_API_RETRY_DELAY_SECONDS


class TestRetryableApiCall:
    def test_should_return_result_on_first_success(self):
        func = MagicMock(return_value="ok")
        assert _retryable_api_call(func) == "ok"
        assert func.call_count == 1

    def test_should_retry_on_500_error(self):
        exc = GithubException(500, data={}, headers={})
        func = MagicMock(side_effect=[exc, "ok"])
        with patch("r2po_init.github.time.sleep"):
            result = _retryable_api_call(func)
        assert result == "ok"
        assert func.call_count == 2

    def test_should_retry_on_503_error(self):
        exc = GithubException(503, data={}, headers={})
        func = MagicMock(side_effect=[exc, exc, "ok"])
        with patch("r2po_init.github.time.sleep"):
            result = _retryable_api_call(func)
        assert result == "ok"
        assert func.call_count == 3

    def test_should_retry_on_connection_error(self):
        func = MagicMock(side_effect=[ConnectionError("timeout"), "ok"])
        with patch("r2po_init.github.time.sleep"):
            result = _retryable_api_call(func)
        assert result == "ok"
        assert func.call_count == 2

    def test_should_retry_on_oserror(self):
        func = MagicMock(side_effect=[OSError("network unreachable"), "ok"])
        with patch("r2po_init.github.time.sleep"):
            result = _retryable_api_call(func)
        assert result == "ok"
        assert func.call_count == 2

    def test_should_raise_after_max_retries_exhausted(self):
        exc = GithubException(500, data={}, headers={})
        func = MagicMock(side_effect=exc)
        with patch("r2po_init.github.time.sleep"), pytest.raises(GithubException):
            _retryable_api_call(func)
        assert func.call_count == GITHUB_API_RETRY_COUNT

    def test_should_not_retry_on_422_error(self):
        exc = GithubException(422, data={}, headers={})
        func = MagicMock(side_effect=exc)
        with pytest.raises(GithubException):
            _retryable_api_call(func)
        assert func.call_count == 1

    def test_should_not_retry_on_401_error(self):
        exc = GithubException(401, data={}, headers={})
        func = MagicMock(side_effect=exc)
        with pytest.raises(GithubException):
            _retryable_api_call(func)
        assert func.call_count == 1

    def test_should_not_retry_on_404_error(self):
        exc = GithubException(404, data={}, headers={})
        func = MagicMock(side_effect=exc)
        with pytest.raises(GithubException):
            _retryable_api_call(func)
        assert func.call_count == 1

    def test_should_sleep_between_retries(self):
        exc = GithubException(500, data={}, headers={})
        func = MagicMock(side_effect=[exc, "ok"])
        with patch("r2po_init.github.time.sleep") as mock_sleep:
            _retryable_api_call(func)
        mock_sleep.assert_called_once_with(GITHUB_API_RETRY_DELAY_SECONDS)

    def test_should_not_sleep_after_final_attempt(self):
        exc = GithubException(500, data={}, headers={})
        func = MagicMock(side_effect=exc)
        with patch("r2po_init.github.time.sleep") as mock_sleep, \
             pytest.raises(GithubException):
            _retryable_api_call(func)
        # RETRY_COUNT=3 attempts → 2 sleeps (not 3)
        assert mock_sleep.call_count == GITHUB_API_RETRY_COUNT - 1

    def test_should_pass_args_and_kwargs_to_func(self):
        func = MagicMock(return_value="ok")
        _retryable_api_call(func, "arg1", key="val")
        func.assert_called_once_with("arg1", key="val")


class TestCreateRepoRetry:
    """Verify create_repo retries the underlying API call on 5xx errors."""

    def test_should_succeed_after_one_transient_500(self):
        client = MagicMock()
        mock_repo = MagicMock(html_url="https://github.com/NovaSoftworks/test-repo")
        exc = GithubException(500, data={}, headers={})
        client.get_organization.return_value.create_repo.side_effect = [exc, mock_repo]

        with patch("r2po_init.github.time.sleep"):
            result = create_repo(client, "test-repo", "desc")

        assert result.html_url == "https://github.com/NovaSoftworks/test-repo"
        assert client.get_organization.return_value.create_repo.call_count == 2

    def test_should_raise_after_all_retries_on_persistent_500(self):
        client = MagicMock()
        exc = GithubException(500, data={}, headers={})
        client.get_organization.return_value.create_repo.side_effect = exc

        with patch("r2po_init.github.time.sleep"), pytest.raises(GithubException):
            create_repo(client, "test-repo", "desc")

        assert client.get_organization.return_value.create_repo.call_count == GITHUB_API_RETRY_COUNT
