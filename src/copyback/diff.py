"""Compare project files against the rendered template."""

from dataclasses import dataclass
from pathlib import Path

from jinja2 import Environment

from .config import get_template_subdirectory, get_variable_values


@dataclass
class DivergentFile:
    """A file that differs between the project and the template."""

    path: str  # Relative path in the project
    template_path: str  # Relative path in the template subdir
    status: str  # 'modified', 'project-only', 'template-only'


def _render_template_file(path: Path, variables: dict[str, str]) -> str:
    """Render a Jinja template file with the given variables."""
    env = Environment(keep_trailing_newline=True)
    content = path.read_text()
    template = env.from_string(content)
    return template.render(**variables)


def _template_files(template_dir: Path, subdirectory: str) -> dict[str, Path]:
    """Get all files in the template subdirectory, mapped by their output path."""
    subdir = template_dir / subdirectory
    if not subdir.exists():
        return {}

    files: dict[str, Path] = {}
    for path in subdir.rglob("*"):
        if path.is_file():
            rel = str(path.relative_to(subdir))
            # Strip .jinja suffix for the output path
            output_rel = rel.removesuffix(".jinja")
            files[output_rel] = path

    return files


def find_divergent_files(
    project_dir: Path,
    template_dir: Path,
    answers: dict,
) -> list[DivergentFile]:
    """Find files that differ between the project and the rendered template."""
    subdirectory = get_template_subdirectory(answers)
    variables = get_variable_values(answers)
    template_files = _template_files(template_dir, subdirectory)

    divergent: list[DivergentFile] = []

    for output_path, tmpl_path in sorted(template_files.items()):
        # Skip meta files
        if output_path == ".gitkeep":
            continue

        project_file = project_dir / output_path
        template_rel = str(tmpl_path.relative_to(template_dir / subdirectory))

        if not project_file.exists():
            divergent.append(
                DivergentFile(
                    path=output_path,
                    template_path=template_rel,
                    status="template-only",
                )
            )
            continue

        # Render template and compare
        try:
            if tmpl_path.suffix == ".jinja" or ".jinja" in tmpl_path.suffixes:
                rendered = _render_template_file(tmpl_path, variables)
            else:
                rendered = tmpl_path.read_text()
        except Exception:
            rendered = tmpl_path.read_text()

        project_content = project_file.read_text()
        if project_content != rendered:
            divergent.append(
                DivergentFile(
                    path=output_path,
                    template_path=template_rel,
                    status="modified",
                )
            )

    return divergent
