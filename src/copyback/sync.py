"""Copy files to the template repo and optionally commit."""

import subprocess
from pathlib import Path

from .config import get_template_subdirectory


def copy_to_template(
    project_path: str,
    content: str,
    is_templated: bool,
    template_dir: Path,
    answers: dict,
) -> Path:
    """Write content to the correct location in the template directory.

    Returns the destination path.
    """
    subdirectory = get_template_subdirectory(answers)
    template_subdir = template_dir / subdirectory

    # Determine destination filename
    dest_name = project_path
    if is_templated and not dest_name.endswith(".jinja"):
        dest_name += ".jinja"

    dest = template_subdir / dest_name
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content)

    return dest


def commit_template_changes(
    template_dir: Path,
    project_name: str,
    files: list[str],
) -> None:
    """Stage and commit changes in the template repo."""
    subprocess.run(
        ["git", "add", "-A"],
        cwd=template_dir,
        check=True,
        capture_output=True,
    )

    file_list = ", ".join(files[:5])
    if len(files) > 5:
        file_list += f" (+{len(files) - 5} more)"

    message = f"chore: sync from {project_name}\n\nFiles: {file_list}"

    subprocess.run(
        ["git", "commit", "-m", message],
        cwd=template_dir,
        check=True,
        capture_output=True,
    )
