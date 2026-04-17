"""Orchestrates the full repository initialization sequence."""

import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from . import git as git_ops
from . import github as gh
from . import reporter
from . import templates
from .constants import FIRST_COMMIT_MESSAGE, GITHUB_ORG
from .reporter import ErrorReport


@dataclass
class Result:
    """Outcome of a single initialization run."""

    success: bool
    repo_url: Optional[str] = None
    push_succeeded: Optional[bool] = None
    push_error: Optional[str] = None
    error_message: Optional[str] = None
    error_report_path: Optional[Path] = None


@dataclass
class _RollbackAction:
    name: str
    undo: Callable[[], None]


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
    rollback_journal: list[_RollbackAction] = []
    steps_completed: list[str] = []
    work_dir: Optional[Path] = None

    try:
        # Step 1: Create the repository.
        created_repo = gh.create_repo(client, repo_name, description)
        rollback_journal.append(
            _RollbackAction(
                name=f"Delete repository {GITHUB_ORG}/{repo_name}",
                undo=lambda: gh.delete_repo(client, repo_name),
            )
        )
        steps_completed.append("Create repository")
        on_step("Create repository", True)

        # Step 2: Apply R2PO labels.
        gh.apply_labels(client, repo_name)
        steps_completed.append("Apply labels")
        on_step("Apply labels", True)

        # Step 3: Seed templates into a local temp directory.
        work_dir = Path(tempfile.mkdtemp())
        templates.seed(work_dir, repo_name, description)
        steps_completed.append("Seed templates")
        on_step("Seed templates", True)

        # Step 4: Commit all seeded files and push.
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
        error_message = str(e)
        rollback_names = _rollback(rollback_journal)
        on_step("Rollback", True)

        error_report_path = reporter.write(
            ErrorReport(
                repo_name=repo_name,
                description=description,
                error_message=error_message,
                steps_completed=steps_completed,
                rollback_actions=rollback_names,
            )
        )
        return Result(
            success=False,
            error_message=error_message,
            error_report_path=error_report_path,
        )

    finally:
        if work_dir is not None:
            shutil.rmtree(work_dir, ignore_errors=True)


def _rollback(journal: list[_RollbackAction]) -> list[str]:
    """Execute rollback actions in reverse order.

    Returns:
        Names of rollback actions that were attempted.
    """
    attempted = []
    for action in reversed(journal):
        attempted.append(action.name)
        try:
            action.undo()
        except Exception:
            pass  # Best-effort; log is in the error report.
    return attempted
