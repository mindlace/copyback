"""Tests for CLI path expansion (directory support in `copyback add`)."""

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from copyback.cli import _expand_paths, _list_files_in_dir


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """Create a minimal project directory with some files."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('hello')")
    (tmp_path / "src" / "util.py").write_text("# util")
    (tmp_path / "README.md").write_text("# readme")
    (tmp_path / ".copier-answers.yml").write_text("_commit: abc")
    return tmp_path


@pytest.fixture
def git_project(project: Path) -> Path:
    """Create a project that is also a git repo with tracked files."""
    subprocess.run(["git", "init"], cwd=project, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=project, capture_output=True, check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=project, capture_output=True, check=True,
    )
    subprocess.run(["git", "add", "."], cwd=project, capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=project, capture_output=True, check=True,
    )
    return project


# --- _expand_paths tests ---


def test_expand_single_file(project: Path) -> None:
    result = _expand_paths(["README.md"], project)
    assert result == ["README.md"]


def test_expand_preserves_explicit_files(project: Path) -> None:
    result = _expand_paths(["src/main.py", "README.md"], project)
    assert result == ["README.md", "src/main.py"]


def test_expand_directory_with_rglob_fallback(project: Path) -> None:
    """Without git, falls back to rglob."""
    with patch(
        "copyback.cli.subprocess.run",
        side_effect=FileNotFoundError("no git"),
    ):
        result = _expand_paths(["src"], project)
    assert sorted(result) == ["src/main.py", "src/util.py"]


def test_expand_directory_via_git(git_project: Path) -> None:
    result = _expand_paths(["src"], git_project)
    assert result == ["src/main.py", "src/util.py"]


def test_expand_dot_via_git(git_project: Path) -> None:
    result = _expand_paths(["."], git_project)
    assert "src/main.py" in result
    assert "README.md" in result


def test_expand_filters_copier_answers_from_dir(git_project: Path) -> None:
    result = _expand_paths(["."], git_project)
    assert ".copier-answers.yml" not in result


def test_expand_filters_copier_answers_explicit(project: Path) -> None:
    result = _expand_paths([".copier-answers.yml"], project)
    assert result == []


def test_expand_mixed_files_and_dirs(git_project: Path) -> None:
    result = _expand_paths(["README.md", "src"], git_project)
    assert "README.md" in result
    assert "src/main.py" in result
    assert "src/util.py" in result


def test_expand_deduplicates(git_project: Path) -> None:
    result = _expand_paths(["src/main.py", "src"], git_project)
    assert result.count("src/main.py") == 1


def test_expand_empty_dir(project: Path) -> None:
    (project / "empty").mkdir()
    with patch(
        "copyback.cli.subprocess.run",
        side_effect=FileNotFoundError("no git"),
    ):
        result = _expand_paths(["empty"], project)
    assert result == []


def test_expand_nested_subdirectories(git_project: Path) -> None:
    """Expanding a directory should include files in nested subdirs."""
    deep = git_project / "src" / "sub" / "deep"
    deep.mkdir(parents=True)
    (deep / "nested.py").write_text("# nested")
    subprocess.run(["git", "add", "."], cwd=git_project, capture_output=True, check=True)

    result = _expand_paths(["src"], git_project)
    assert "src/sub/deep/nested.py" in result
    assert "src/main.py" in result


def test_expand_git_untracked_files_included(git_project: Path) -> None:
    """Untracked (but not ignored) files should be picked up by git ls-files."""
    (git_project / "new_file.py").write_text("# brand new")

    result = _expand_paths(["."], git_project)
    assert "new_file.py" in result


def test_expand_gitignored_files_excluded(git_project: Path) -> None:
    """Files matching .gitignore should not appear in expansion."""
    (git_project / ".gitignore").write_text("*.log\n")
    (git_project / "debug.log").write_text("some log")
    subprocess.run(["git", "add", ".gitignore"], cwd=git_project, capture_output=True, check=True)

    result = _expand_paths(["."], git_project)
    assert "debug.log" not in result


def test_expand_nonexistent_file_passes_through(project: Path) -> None:
    """A nonexistent file path is kept as-is (downstream handles the error)."""
    result = _expand_paths(["no_such_file.py"], project)
    assert result == ["no_such_file.py"]


def test_expand_path_outside_project_raises(project: Path) -> None:
    """A path resolving outside project_dir should raise ValueError."""
    with pytest.raises(ValueError):
        _expand_paths(["../../etc/passwd"], project)


# --- _list_files_in_dir tests ---


def test_list_files_git_fallback_on_error(project: Path) -> None:
    abs_dir = project / "src"
    with patch(
        "copyback.cli.subprocess.run",
        side_effect=subprocess.CalledProcessError(1, "git"),
    ):
        result = _list_files_in_dir("src", abs_dir, project)
    assert sorted(result) == ["src/main.py", "src/util.py"]


def test_list_files_excludes_copier_answers(project: Path) -> None:
    """Even via rglob fallback, .copier-answers.yml is excluded."""
    with patch(
        "copyback.cli.subprocess.run",
        side_effect=FileNotFoundError("no git"),
    ):
        result = _list_files_in_dir(".", project, project)
    assert ".copier-answers.yml" not in result
    for p in result:
        assert Path(p).name != ".copier-answers.yml"
