"""CLI entry point for copyback."""

import subprocess
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.table import Table

from .diff import find_divergent_files
from .reverse import reverse_substitute
from .sync import copy_to_template, commit_template_changes
from .add import add_files_to_template
from .config import load_copier_answers, resolve_template_dir

app = typer.Typer(help="Reverse-sync project changes back to a Copier template.")
console = Console()

EXCLUDED_FILES = {".copier-answers.yml"}


def _expand_paths(files: list[str], project_dir: Path) -> list[str]:
    """Expand directory entries into individual file paths.

    Uses ``git ls-files`` when inside a git repo, falling back to
    ``Path.rglob`` otherwise. Always filters out EXCLUDED_FILES.
    """
    expanded: list[str] = []
    for entry in files:
        p = (project_dir / entry).resolve()
        if p.is_dir():
            expanded.extend(_list_files_in_dir(entry, p, project_dir))
        else:
            rel = str(p.relative_to(project_dir))
            if rel not in EXCLUDED_FILES:
                expanded.append(rel)
    # deduplicate while preserving order, then sort
    return sorted(dict.fromkeys(expanded))


def _list_files_in_dir(entry: str, abs_dir: Path, project_dir: Path) -> list[str]:
    """List files in a directory, preferring git ls-files."""
    try:
        result = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", entry],
            cwd=project_dir,
            capture_output=True,
            text=True,
            check=True,
        )
        paths = [line for line in result.stdout.splitlines() if line]
    except (subprocess.CalledProcessError, FileNotFoundError):
        paths = [
            str(f.relative_to(project_dir))
            for f in abs_dir.rglob("*")
            if f.is_file()
        ]
    return [p for p in paths if Path(p).name not in EXCLUDED_FILES]


@app.command()
def status(
    project_dir: Annotated[
        Path, typer.Argument(help="Project directory (default: current dir)")
    ] = Path("."),
    template_dir: Annotated[
        Optional[Path],
        typer.Option("--template-dir", "-t", help="Template repo directory"),
    ] = None,
) -> None:
    """Show which project files differ from the template."""
    project_dir = project_dir.resolve()
    answers = load_copier_answers(project_dir)
    tmpl = resolve_template_dir(answers, template_dir)

    divergent = find_divergent_files(project_dir, tmpl, answers)

    if not divergent:
        console.print("[green]All template-managed files are in sync.[/green]")
        return

    table = Table(title="Divergent Files")
    table.add_column("File", style="cyan")
    table.add_column("Status", style="yellow")

    for item in divergent:
        table.add_row(item.path, item.status)

    console.print(table)
    console.print(f"\n[bold]{len(divergent)}[/bold] file(s) differ from template.")


@app.command()
def push(
    files: Annotated[
        Optional[list[str]], typer.Argument(help="Files to push (default: interactive)")
    ] = None,
    project_dir: Annotated[
        Path, typer.Option("--project-dir", "-p", help="Project directory")
    ] = Path("."),
    template_dir: Annotated[
        Optional[Path],
        typer.Option("--template-dir", "-t", help="Template repo directory"),
    ] = None,
    all_files: Annotated[
        bool, typer.Option("--all", help="Push all divergent files")
    ] = False,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Show what would be done without writing")
    ] = False,
    commit: Annotated[
        bool, typer.Option("--commit", help="Commit changes in the template repo")
    ] = False,
) -> None:
    """Push project file changes back to the template."""
    project_dir = project_dir.resolve()
    answers = load_copier_answers(project_dir)
    tmpl = resolve_template_dir(answers, template_dir)

    divergent = find_divergent_files(project_dir, tmpl, answers)
    if not divergent:
        console.print("[green]Nothing to push — all files in sync.[/green]")
        return

    if files:
        selected = [d for d in divergent if d.path in files]
    elif all_files:
        selected = divergent
    else:
        # Interactive selection
        console.print("\n[bold]Divergent files:[/bold]")
        for i, item in enumerate(divergent, 1):
            console.print(f"  {i}. {item.path} ({item.status})")

        choices = typer.prompt(
            "Enter file numbers to push (comma-separated, or 'all')"
        )
        if choices.strip().lower() == "all":
            selected = divergent
        else:
            indices = [int(x.strip()) - 1 for x in choices.split(",")]
            selected = [divergent[i] for i in indices if 0 <= i < len(divergent)]

    if not selected:
        console.print("[yellow]No files selected.[/yellow]")
        return

    for item in selected:
        src = project_dir / item.path
        content = src.read_text()

        # Reverse-substitute project values back to Jinja variables
        reversed_content, is_templated = reverse_substitute(content, answers)

        if dry_run:
            dest_name = item.template_path
            if is_templated and not dest_name.endswith(".jinja"):
                dest_name += ".jinja"
            console.print(f"[dim]Would write:[/dim] {dest_name}")
            if is_templated:
                console.print(f"  [dim]Substitutions applied for template variables[/dim]")
        else:
            copy_to_template(
                item.path, reversed_content, is_templated, tmpl, answers
            )
            console.print(f"[green]Pushed:[/green] {item.path}")

    if commit and not dry_run:
        project_name = answers.get("project_name", "unknown")
        commit_template_changes(tmpl, project_name, [s.path for s in selected])
        console.print("[green]Committed changes in template repo.[/green]")


@app.command()
def add(
    files: Annotated[list[str], typer.Argument(help="Files to add to the template")],
    project_dir: Annotated[
        Path, typer.Option("--project-dir", "-p", help="Project directory")
    ] = Path("."),
    template_dir: Annotated[
        Optional[Path],
        typer.Option("--template-dir", "-t", help="Template repo directory"),
    ] = None,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Show what would be done without writing")
    ] = False,
) -> None:
    """Add new project files to the template, interactively detecting template variables."""
    project_dir = project_dir.resolve()
    answers = load_copier_answers(project_dir)
    tmpl = resolve_template_dir(answers, template_dir)

    files = _expand_paths(files, project_dir)
    if not files:
        console.print("[yellow]No files found to add.[/yellow]")
        return

    add_files_to_template(
        files=files,
        project_dir=project_dir,
        template_dir=tmpl,
        answers=answers,
        dry_run=dry_run,
        console=console,
    )
