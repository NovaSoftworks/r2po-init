"""Orchestrates the full repository initialization sequence."""

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional


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
    # Implemented incrementally across stories #4, #6, #7.
    # Story #8 establishes this stub so cli.py has something to call.
    raise NotImplementedError("Initializer not yet implemented — see stories #4, #6, #7")
