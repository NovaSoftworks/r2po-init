"""Git operations for creating the first commit and pushing to the remote."""

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class PushResult:
    """Outcome of the commit-and-push step."""

    committed: bool
    pushed: bool
    push_error: str | None = None


def commit_and_push(
    repo_path: Path,
    remote_url: str,
    token: str,
    commit_message: str,
) -> PushResult:
    """Create the first commit in repo_path and push to the remote.

    Sets up a temporary git credential store so the token is never
    embedded in the remote URL or visible in the process list.

    Args:
        repo_path: Root of the local repository working directory.
        remote_url: HTTPS clone URL of the remote (from PyGithub repo.clone_url).
        token: GitHub personal access token for authentication.
        commit_message: The commit message to use.

    Returns:
        PushResult indicating whether the commit and push succeeded.

    Raises:
        RuntimeError: If git init, add, or commit fails (these are hard failures).
    """
    _run_git(repo_path, "init", "-b", "main")
    _run_git(repo_path, "config", "user.email", "r2po-init@novasoftworks.com")
    _run_git(repo_path, "config", "user.name", "r2po-init")
    _run_git(repo_path, "add", ".")
    _run_git(repo_path, "commit", "-m", commit_message)
    _run_git(repo_path, "remote", "add", "origin", remote_url)

    # Write a temporary credential store file so the token is not in the process list.
    cred_file = repo_path / ".git-credentials"
    cred_file.write_text(
        f"https://x-access-token:{token}@github.com\n",
        encoding="utf-8",
    )
    cred_file.chmod(0o600)
    _run_git(repo_path, "config", "credential.helper", f"store --file={cred_file}")

    push = subprocess.run(
        ["git", "push", "-u", "origin", "main"],
        cwd=repo_path,
        capture_output=True,
        text=True,
    )

    # Remove credential file immediately after push attempt.
    cred_file.unlink(missing_ok=True)

    if push.returncode == 0:
        return PushResult(committed=True, pushed=True)
    return PushResult(committed=True, pushed=False, push_error=push.stderr.strip())


def _run_git(repo_path: Path, *args: str) -> subprocess.CompletedProcess:
    """Run a git command in repo_path, raising RuntimeError on non-zero exit.

    Args:
        repo_path: Working directory for the git command.
        *args: Arguments to pass to git.

    Returns:
        The completed process result.

    Raises:
        RuntimeError: If git exits with a non-zero return code.
    """
    result = subprocess.run(
        ["git", *args],
        cwd=repo_path,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"git {args[0]} failed: {result.stderr.strip() or result.stdout.strip()}"
        )
    return result
