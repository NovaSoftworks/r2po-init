"""Writes a plain-text error report when initialization is aborted."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .constants import ERROR_REPORT_FILENAME_PATTERN


@dataclass
class ErrorReport:
    """All information captured at the point of an initialization failure."""

    repo_name: str
    description: str
    error_message: str
    steps_completed: list[str] = field(default_factory=list)
    rollback_actions: list[str] = field(default_factory=list)


def write(report: ErrorReport, dest_dir: Path | None = None) -> Path:
    """Write the error report to dest_dir and return the file path.

    Args:
        report: Error details to serialize.
        dest_dir: Directory to write the file into. Defaults to cwd.

    Returns:
        Path of the written report file.
    """
    if dest_dir is None:
        dest_dir = Path.cwd()

    timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    filename = ERROR_REPORT_FILENAME_PATTERN.format(timestamp=timestamp)
    path = dest_dir / filename

    lines = [
        "r2po-init error report",
        "=" * 40,
        f"Time:        {timestamp}",
        f"Repository:  {report.repo_name}",
        f"Description: {report.description}",
        "",
        "Error",
        "-" * 40,
        report.error_message,
        "",
    ]

    if report.steps_completed:
        lines += ["Steps completed", "-" * 40]
        lines += [f"  ✓ {step}" for step in report.steps_completed]
        lines.append("")

    if report.rollback_actions:
        lines += ["Rollback actions taken", "-" * 40]
        lines += [f"  - {action}" for action in report.rollback_actions]
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    return path
