"""Configuration loading — reads .copier-answers.yml and resolves template directory."""

import os
from pathlib import Path

import yaml


def load_copier_answers(project_dir: Path) -> dict:
    """Load and return the .copier-answers.yml from the project directory."""
    answers_path = project_dir / ".copier-answers.yml"
    if not answers_path.exists():
        raise FileNotFoundError(
            f"No .copier-answers.yml found in {project_dir}. "
            "Is this a Copier-managed project?"
        )

    with open(answers_path) as f:
        answers = yaml.safe_load(f)

    return answers or {}


def resolve_template_dir(answers: dict, override: Path | None = None) -> Path:
    """Resolve the template directory from override, env var, or answers."""
    if override:
        tmpl = override.resolve()
    elif env_dir := os.environ.get("COPIER_TEMPLATE_DIR"):
        tmpl = Path(env_dir).resolve()
    elif src_path := answers.get("_src_path"):
        tmpl = Path(src_path).resolve()
    else:
        raise ValueError(
            "Cannot determine template directory. Use --template-dir, "
            "set COPIER_TEMPLATE_DIR, or ensure _src_path is in .copier-answers.yml"
        )

    if not tmpl.is_dir():
        raise FileNotFoundError(f"Template directory not found: {tmpl}")

    return tmpl


def get_template_subdirectory(answers: dict) -> str:
    """Get the template subdirectory from answers (default: 'template')."""
    return answers.get("_subdirectory", "template")


def get_variable_values(answers: dict) -> dict[str, str]:
    """Extract user-defined variable values (non-underscore keys) from answers."""
    return {
        k: str(v)
        for k, v in answers.items()
        if not k.startswith("_") and v is not None and str(v).strip()
    }
