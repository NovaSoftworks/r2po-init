"""Orchestrates the full repository initialization sequence."""

import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from . import git as git_ops
from . import github as gh
from . import templates
from .constants import FIRST_COMMIT_MESSAGE, GITHUB_ORG


@dataclass
class Result:
    """Outcome of a single initialization run."""

    success: bool
    repo_url: Optional[str] = None
    push_succeeded: Optional[bool] = None
    push_error: Optional[str] = None
    error_message: Optional[str] = None
    error_report_path: Optional[Path] = None


def run(
    repo_name: str,
    description: str,
    on_step: Callable[[str, bool], None] = lambda step, ok: None,
) -> Result:
    """Run the full initialization sequence for a new R2PO project repo.

    Args:
        repo_name: Validated repository name (lowercase, hyphens, max 100 chars).
        description: Repository description string.
        on_step: Callback fired after each major step with (step_name, success).

    Returns:
        Result indicating success or failure with details.
    """
    # Validate source templates before touching GitHub (fail fast, no cleanup needed).
    try:
        templates.validate_source()
    except templates.SourceNotFoundError as e:
        return Result(success=False, error_message=str(e))

    # Validate gh token before touching GitHub.
    token = gh.get_token()
    if not token:
        return Result(
            success=False,
            error_message="No GitHub token found. Run 'gh auth login' first.",
        )

    client = gh.create_client(token)
    created_repo = None
    work_dir: Optional[Path] = None

    try:
        # Step 1: Create the repository.
        created_repo = gh.create_repo(client, repo_name, description)
        on_step("Create repository", True)

        # Step 2: Seed templates into a local temp directory.
        work_dir = Path(tempfile.mkdtemp())
        templates.seed(work_dir, repo_name, description)
        on_step("Seed templates", True)

        # Step 3: Commit all seeded files and push.
        push_result = git_ops.commit_and_push(
            work_dir, created_repo.clone_url, token, FIRST_COMMIT_MESSAGE
        )
        on_step("Commit and push", push_result.committed)

        return Result(
            success=True,
            repo_url=created_repo.html_url,
            push_succeeded=push_result.pushed,
            push_error=push_result.push_error,
        )

    except gh.RepoExistsError as e:
        on_step("Create repository", False)
        return Result(success=False, error_message=str(e))

    except gh.AuthError as e:
        on_step("Create repository", False)
        return Result(success=False, error_message=str(e))

    except Exception as e:
        on_step("Create repository", False)
        # Rollback: delete the repo if it was created.
        if created_repo is not None:
            try:
                gh.delete_repo(client, repo_name)
            except Exception:
                pass  # Best-effort; full rollback is implemented in story #12.
        return Result(success=False, error_message=f"Unexpected error: {e}")

    finally:
        if work_dir is not None:
            shutil.rmtree(work_dir, ignore_errors=True)
