"""Tests for diff module."""

from pathlib import Path

import yaml
import pytest

from copyback.diff import find_divergent_files


@pytest.fixture
def setup_project_and_template(tmp_path: Path) -> tuple[Path, Path, dict]:
    """Create a project and template directory for testing."""
    project_dir = tmp_path / "project"
    template_dir = tmp_path / "template-repo"
    template_subdir = template_dir / "template"

    project_dir.mkdir()
    template_dir.mkdir()
    template_subdir.mkdir()

    answers = {
        "_subdirectory": "template",
        "project_name": "testapp",
    }

    (project_dir / ".copier-answers.yml").write_text(yaml.dump(answers))

    return project_dir, template_dir, answers


def test_identical_files(setup_project_and_template: tuple[Path, Path, dict]) -> None:
    project_dir, template_dir, answers = setup_project_and_template
    template_subdir = template_dir / "template"

    # Create identical files
    (template_subdir / "config.js").write_text("export default {};")
    (project_dir / "config.js").write_text("export default {};")

    divergent = find_divergent_files(project_dir, template_dir, answers)
    assert len(divergent) == 0


def test_modified_file(setup_project_and_template: tuple[Path, Path, dict]) -> None:
    project_dir, template_dir, answers = setup_project_and_template
    template_subdir = template_dir / "template"

    (template_subdir / "config.js").write_text("export default {};")
    (project_dir / "config.js").write_text("export default { debug: true };")

    divergent = find_divergent_files(project_dir, template_dir, answers)
    assert len(divergent) == 1
    assert divergent[0].path == "config.js"
    assert divergent[0].status == "modified"


def test_template_only_file(setup_project_and_template: tuple[Path, Path, dict]) -> None:
    project_dir, template_dir, answers = setup_project_and_template
    template_subdir = template_dir / "template"

    (template_subdir / "missing.js").write_text("// new file")

    divergent = find_divergent_files(project_dir, template_dir, answers)
    assert len(divergent) == 1
    assert divergent[0].status == "template-only"


def test_jinja_template_rendered(setup_project_and_template: tuple[Path, Path, dict]) -> None:
    project_dir, template_dir, answers = setup_project_and_template
    template_subdir = template_dir / "template"

    # Template with Jinja
    (template_subdir / "package.json.jinja").write_text('{"name": "{{ project_name }}"}')
    # Project with rendered value
    (project_dir / "package.json").write_text('{"name": "testapp"}')

    divergent = find_divergent_files(project_dir, template_dir, answers)
    assert len(divergent) == 0  # Should match after rendering


def test_jinja_template_diverged(setup_project_and_template: tuple[Path, Path, dict]) -> None:
    project_dir, template_dir, answers = setup_project_and_template
    template_subdir = template_dir / "template"

    (template_subdir / "package.json.jinja").write_text('{"name": "{{ project_name }}"}')
    (project_dir / "package.json").write_text('{"name": "testapp", "version": "2.0.0"}')

    divergent = find_divergent_files(project_dir, template_dir, answers)
    assert len(divergent) == 1
    assert divergent[0].status == "modified"


def test_nested_files(setup_project_and_template: tuple[Path, Path, dict]) -> None:
    project_dir, template_dir, answers = setup_project_and_template
    template_subdir = template_dir / "template"

    (template_subdir / "src" / "lib").mkdir(parents=True)
    (template_subdir / "src" / "lib" / "utils.ts").write_text("export {};")
    (project_dir / "src" / "lib").mkdir(parents=True)
    (project_dir / "src" / "lib" / "utils.ts").write_text("export { foo };")

    divergent = find_divergent_files(project_dir, template_dir, answers)
    assert len(divergent) == 1
    assert divergent[0].path == "src/lib/utils.ts"
