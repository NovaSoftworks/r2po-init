"""CLI entry point for r2po-init."""

import re
from typing import Optional

import typer
from rich.console import Console

from .constants import GITHUB_ORG, REPO_NAME_PATTERN, REPO_NAME_MAX_LENGTH
from . import initializer

app = typer.Typer(help="Initialize a new R2PO project repository in NovaSoftworks.")
console = Console()


def _is_valid_repo_name(name: str) -> bool:
    """Return True if name matches GitHub repo naming rules for R2PO projects."""
    return bool(re.match(REPO_NAME_PATTERN, name)) and len(name) <= REPO_NAME_MAX_LENGTH


@app.command()
def main(
    repo_name: Optional[str] = typer.Argument(
        None,
        help="Repository name (lowercase letters, digits, hyphens; max 100 chars).",
    ),
    description: Optional[str] = typer.Option(
        None,
        "--description",
        "-d",
        help="Repository description. Defaults to 'R2PO project: <name>'.",
    ),
) -> None:
    """Initialize a new R2PO project repository in the NovaSoftworks organization."""
    interactive = repo_name is None

    # Resolve repo_name: validate if provided as arg, prompt if missing.
    if repo_name is not None:
        if not _is_valid_repo_name(repo_name):
            raise typer.BadParameter(
                "must be lowercase letters, digits, and hyphens only (max 100 chars).",
                param_hint="repo_name",
            )
    else:
        while True:
            repo_name = typer.prompt("Repository name")
            if _is_valid_repo_name(repo_name):
                break
            console.print(
                "[red]Invalid name:[/red] lowercase letters, digits, and hyphens only "
                "(max 100 chars). Try again."
            )

    # Resolve description: auto-generate in arg mode; prompt (with default) in interactive mode.
    if description is None:
        if interactive:
            description = typer.prompt(
                "Description",
                default=f"R2PO project: {repo_name}",
            )
        else:
            description = f"R2PO project: {repo_name}"

    # Run initialization, printing each step as it completes.
    def on_step(step: str, success: bool) -> None:
        icon = "[green]✓[/green]" if success else "[red]✗[/red]"
        console.print(f"  [{icon}] {step}")

    console.print(f"\nInitializing [bold]{GITHUB_ORG}/{repo_name}[/bold]…\n")
    result = initializer.run(repo_name, description, on_step=on_step)

    if result.success:
        console.print(f"\n[green]Done.[/green] {result.repo_url}")
        if result.push_succeeded is False:
            console.print(
                f"\n[yellow]Warning:[/yellow] push failed — {result.push_error}\n"
                f"Push manually:  git push origin main"
            )
    else:
        console.print(f"\n[red]Failed:[/red] {result.error_message}")
        if result.error_report_path:
            console.print(f"Error report:   {result.error_report_path}")
        raise typer.Exit(code=1)
