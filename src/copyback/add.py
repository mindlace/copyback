"""Add new project files to the template with interactive variable detection."""

import re
from pathlib import Path

import yaml
from rich.console import Console

from .config import get_template_subdirectory, get_variable_values
from .reverse import reverse_substitute
from .sync import copy_to_template


def _find_candidates(content: str, answers: dict) -> list[dict[str, str]]:
    """Find strings in content that might need to become template variables.

    Flags:
    - Strings containing the project name
    - ALL_CAPS constants (potential project-specific config)
    """
    variables = get_variable_values(answers)
    project_name = answers.get("project_name", "")
    candidates: list[dict[str, str]] = []

    # Find strings containing the project name
    if project_name:
        for match in re.finditer(re.escape(project_name), content):
            start = max(0, match.start() - 20)
            end = min(len(match.string), match.end() + 20)
            context = content[start:end]
            candidates.append({
                "match": match.group(),
                "context": context.strip(),
                "reason": "contains project name",
                "existing_var": "project_name",
            })

    # Find ALL_CAPS constants that aren't common ones
    common_caps = {
        "GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS", "PATCH",
        "URL", "API", "SQL", "CSS", "HTML", "JSON", "XML", "UTF",
        "OK", "ID", "UUID", "NULL", "TRUE", "FALSE", "ON", "OFF",
    }
    for match in re.finditer(r'\b[A-Z][A-Z0-9_]{2,}\b', content):
        word = match.group()
        if word not in common_caps and word not in variables.values():
            start = max(0, match.start() - 20)
            end = min(len(match.string), match.end() + 20)
            context = content[start:end]
            candidates.append({
                "match": word,
                "context": context.strip(),
                "reason": "ALL_CAPS constant",
                "existing_var": None,
            })

    # Deduplicate by match value
    seen = set()
    unique: list[dict[str, str]] = []
    for c in candidates:
        if c["match"] not in seen:
            seen.add(c["match"])
            unique.append(c)

    return unique


def add_files_to_template(
    files: list[str],
    project_dir: Path,
    template_dir: Path,
    answers: dict,
    dry_run: bool,
    console: Console,
) -> None:
    """Add new files to the template, interactively prompting for variable substitution."""
    subdirectory = get_template_subdirectory(answers)

    for file_path in files:
        src = project_dir / file_path
        if not src.exists():
            console.print(f"[red]File not found:[/red] {file_path}")
            continue

        content = src.read_text()
        candidates = _find_candidates(content, answers)

        if candidates:
            console.print(f"\n[bold]Potential template variables in {file_path}:[/bold]")

            for i, c in enumerate(candidates, 1):
                reason = c["reason"]
                existing = c.get("existing_var")
                context = c["context"]
                console.print(f"  {i}. [cyan]{c['match']}[/cyan] ({reason})")
                console.print(f"     Context: ...{context}...")
                if existing:
                    console.print(f"     Suggested var: [green]{existing}[/green]")

            console.print("\nFor each match, choose:")
            console.print("  [k]eep as-is | [e]xisting var | [n]ew var | [s]kip all")

            use_reverse = False
            for c in candidates:
                if c.get("existing_var"):
                    # Auto-substitute known variables
                    use_reverse = True
                else:
                    choice = console.input(
                        f"  {c['match']}: [k/e/n/s]? "
                    ).strip().lower()
                    if choice == "s":
                        break
                    elif choice == "e":
                        use_reverse = True
                    elif choice == "n":
                        var_name = console.input("    Variable name: ").strip()
                        if var_name:
                            # Add to copier.yml
                            if not dry_run:
                                _add_variable_to_copier_yml(
                                    template_dir, var_name, c["match"]
                                )
                            console.print(
                                f"    [green]Added variable {var_name}[/green]"
                            )
                            use_reverse = True

            if use_reverse:
                reversed_content, is_templated = reverse_substitute(content, answers)
            else:
                reversed_content = content
                is_templated = False
        else:
            reversed_content = content
            is_templated = False

        if dry_run:
            dest = file_path + (".jinja" if is_templated else "")
            console.print(f"[dim]Would add:[/dim] {dest}")
        else:
            copy_to_template(file_path, reversed_content, is_templated, template_dir, answers)
            console.print(f"[green]Added:[/green] {file_path}")


def _add_variable_to_copier_yml(template_dir: Path, var_name: str, default: str) -> None:
    """Add a new variable to copier.yml in the template directory."""
    copier_path = template_dir / "copier.yml"
    if not copier_path.exists():
        return

    with open(copier_path) as f:
        config = yaml.safe_load(f) or {}

    if var_name not in config:
        config[var_name] = {
            "type": "str",
            "default": default,
            "help": f"Value for {var_name}",
        }

        with open(copier_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
