"""Tests for sync module."""

from pathlib import Path

import pytest

from copyback.sync import copy_to_template


@pytest.fixture
def template_dir(tmp_path: Path) -> Path:
    (tmp_path / "template").mkdir()
    return tmp_path


def test_copy_verbatim(template_dir: Path) -> None:
    answers = {"_subdirectory": "template"}
    content = "export default {};"

    dest = copy_to_template("config.js", content, False, template_dir, answers)

    assert dest.exists()
    assert dest.name == "config.js"
    assert dest.read_text() == content


def test_copy_templated(template_dir: Path) -> None:
    answers = {"_subdirectory": "template"}
    content = '{"name": "{{ project_name }}"}'

    dest = copy_to_template("package.json", content, True, template_dir, answers)

    assert dest.exists()
    assert dest.name == "package.json.jinja"
    assert dest.read_text() == content


def test_copy_already_jinja_suffix(template_dir: Path) -> None:
    answers = {"_subdirectory": "template"}
    content = "{{ project_name }}"

    dest = copy_to_template("app.d.ts.jinja", content, True, template_dir, answers)

    # Should not double the .jinja suffix
    assert dest.name == "app.d.ts.jinja"


def test_copy_nested_path(template_dir: Path) -> None:
    answers = {"_subdirectory": "template"}
    content = "nested content"

    dest = copy_to_template("src/lib/server/db/index.ts", content, False, template_dir, answers)

    assert dest.exists()
    assert dest.relative_to(template_dir / "template") == Path("src/lib/server/db/index.ts")
    assert dest.read_text() == content
