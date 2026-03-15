"""Tests for config module."""

import os
from pathlib import Path

import pytest
import yaml

from copyback.config import (
    load_copier_answers,
    resolve_template_dir,
    get_template_subdirectory,
    get_variable_values,
)


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    answers = {
        "_src_path": str(tmp_path / "template-repo"),
        "_subdirectory": "template",
        "project_name": "myapp",
        "project_description": "My cool app",
        "d1_database_id": "abc-123",
        "use_r2": True,
    }
    (tmp_path / ".copier-answers.yml").write_text(yaml.dump(answers))
    (tmp_path / "template-repo").mkdir()
    return tmp_path


def test_load_copier_answers(project_dir: Path) -> None:
    answers = load_copier_answers(project_dir)
    assert answers["project_name"] == "myapp"
    assert answers["_src_path"] == str(project_dir / "template-repo")


def test_load_copier_answers_missing(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="No .copier-answers.yml"):
        load_copier_answers(tmp_path)


def test_resolve_template_dir_override(project_dir: Path) -> None:
    answers = load_copier_answers(project_dir)
    override = project_dir / "template-repo"
    result = resolve_template_dir(answers, override)
    assert result == override.resolve()


def test_resolve_template_dir_env_var(project_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    answers = load_copier_answers(project_dir)
    env_dir = project_dir / "template-repo"
    monkeypatch.setenv("COPIER_TEMPLATE_DIR", str(env_dir))
    result = resolve_template_dir(answers)
    assert result == env_dir.resolve()


def test_resolve_template_dir_from_answers(project_dir: Path) -> None:
    answers = load_copier_answers(project_dir)
    result = resolve_template_dir(answers)
    assert result == (project_dir / "template-repo").resolve()


def test_resolve_template_dir_missing() -> None:
    with pytest.raises(ValueError, match="Cannot determine template directory"):
        resolve_template_dir({})


def test_get_template_subdirectory() -> None:
    assert get_template_subdirectory({"_subdirectory": "tmpl"}) == "tmpl"
    assert get_template_subdirectory({}) == "template"


def test_get_variable_values() -> None:
    answers = {
        "_src_path": "/some/path",
        "_subdirectory": "template",
        "project_name": "myapp",
        "project_description": "",
        "d1_database_id": "abc-123",
        "use_r2": True,
    }
    result = get_variable_values(answers)
    assert result == {
        "project_name": "myapp",
        "d1_database_id": "abc-123",
        "use_r2": "True",
    }
    # Underscore-prefixed and empty values excluded
    assert "_src_path" not in result
    assert "project_description" not in result
