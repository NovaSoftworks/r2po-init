"""GitHub API operations for r2po-init."""

import subprocess
import time
from typing import Optional

from github import Github, GithubException

from .constants import GITHUB_ORG, GITHUB_API_RETRY_COUNT, GITHUB_API_RETRY_DELAY_SECONDS


def _retryable_api_call(func, *args, **kwargs):
    """Call func, retrying on transient 5xx or network errors.

    Retries up to GITHUB_API_RETRY_COUNT times with GITHUB_API_RETRY_DELAY_SECONDS between
    attempts. 4xx errors and non-HTTP exceptions are re-raised immediately without retry.

    Args:
        func: Callable to invoke.
        *args, **kwargs: Forwarded to func.

    Returns:
        The return value of func on success.

    Raises:
        The last exception if all retry attempts are exhausted.
    """
    last_error: Exception | None = None
    for attempt in range(GITHUB_API_RETRY_COUNT):
        try:
            return func(*args, **kwargs)
        except GithubException as e:
            if e.status >= 500:
                last_error = e
            else:
                raise  # 4xx is non-retryable
        except (ConnectionError, OSError) as e:
            last_error = e
        if attempt < GITHUB_API_RETRY_COUNT - 1:
            time.sleep(GITHUB_API_RETRY_DELAY_SECONDS)
    raise last_error  # type: ignore[misc]


class RepoExistsError(Exception):
    """Raised when the target repository already exists in the organization."""


class AuthError(Exception):
    """Raised when GitHub authentication fails or the token is missing."""


def get_token() -> Optional[str]:
    """Retrieve the GitHub token from the gh CLI.

    Returns:
        The token string, or None if gh is not authenticated.
    """
    result = subprocess.run(
        ["gh", "auth", "token"],
        capture_output=True,
        text=True,
    )
    token = result.stdout.strip()
    return token if token else None


def create_client(token: str) -> Github:
    """Create an authenticated PyGithub client.

    Args:
        token: A valid GitHub personal access token.

    Returns:
        An authenticated Github instance.
    """
    return Github(token)


def create_repo(client: Github, name: str, description: str):
    """Create a new private repository in the NovaSoftworks organization.

    Args:
        client: An authenticated Github client.
        name: Repository name (must not already exist).
        description: Short description for the repository.

    Returns:
        The created Repository object.

    Raises:
        RepoExistsError: If a repository with this name already exists.
        AuthError: If the token lacks permission to create repositories.
        GithubException: For any other GitHub API error.
    """
    try:
        org = client.get_organization(GITHUB_ORG)
        return _retryable_api_call(org.create_repo, name, description=description, private=True)
    except GithubException as e:
        if e.status == 422 and _is_name_taken_error(e):
            raise RepoExistsError(
                f"Repository '{name}' already exists in {GITHUB_ORG}."
            ) from e
        if e.status in (401, 403):
            raise AuthError(
                f"Authentication failed (HTTP {e.status}). Run 'gh auth login' to re-authenticate."
            ) from e
        raise


def delete_repo(client: Github, name: str) -> None:
    """Delete a repository from the NovaSoftworks organization.

    Used during rollback. Safe to call if the repo does not exist.

    Args:
        client: An authenticated Github client.
        name: Repository name to delete.
    """
    try:
        repo = client.get_organization(GITHUB_ORG).get_repo(name)
        repo.delete()
    except GithubException as e:
        if e.status == 404:
            return  # Already gone — rollback is a no-op.
        raise


def apply_labels(client: Github, repo_name: str) -> None:
    """Apply standard R2PO labels to the repository, overriding any existing ones.

    Creates a label if it does not exist; updates color and description if it does.

    Args:
        client: An authenticated Github client.
        repo_name: Name of the repository within GITHUB_ORG.
    """
    from .constants import R2PO_LABELS

    repo = client.get_organization(GITHUB_ORG).get_repo(repo_name)
    existing = {label.name: label for label in _retryable_api_call(repo.get_labels)}

    for label_def in R2PO_LABELS:
        if label_def.name in existing:
            _retryable_api_call(
                existing[label_def.name].edit,
                name=label_def.name,
                color=label_def.color,
                description=label_def.description,
            )
        else:
            _retryable_api_call(
                repo.create_label,
                name=label_def.name,
                color=label_def.color,
                description=label_def.description,
            )


def _is_name_taken_error(exc: GithubException) -> bool:
    """Return True if the 422 exception indicates the repo name is already taken."""
    errors = exc.data.get("errors", [])
    return any(
        err.get("field") == "name" and err.get("message") in ("name already exists", "already_exists")
        for err in errors
    )
