"""Tests for reverse substitution."""

from copyback.reverse import reverse_substitute, preview_substitutions


def test_basic_substitution() -> None:
    content = 'const db = platform.env.myapp;'
    answers = {"project_name": "myapp"}
    result, templated = reverse_substitute(content, answers)
    assert templated is True
    assert result == 'const db = platform.env.{{ project_name }};'


def test_multiple_occurrences() -> None:
    content = 'name: myapp\nbinding: myapp\ndatabase: myapp'
    answers = {"project_name": "myapp"}
    result, templated = reverse_substitute(content, answers)
    assert templated is True
    assert result.count("{{ project_name }}") == 3


def test_no_substitution_needed() -> None:
    content = "const x = 42;"
    answers = {"project_name": "myapp"}
    result, templated = reverse_substitute(content, answers)
    assert templated is False
    assert result == content


def test_longest_first_substitution() -> None:
    """Longer values should be substituted first to avoid partial matches."""
    content = 'database_id: abc-123-def-456'
    answers = {
        "d1_database_id": "abc-123-def-456",
        "short_id": "abc",
    }
    result, templated = reverse_substitute(content, answers)
    assert templated is True
    assert "{{ d1_database_id }}" in result
    # The short_id should not have partially matched inside the longer value
    assert "{{ short_id }}" not in result


def test_empty_variables() -> None:
    content = "some content"
    answers = {"project_name": ""}
    result, templated = reverse_substitute(content, answers)
    assert templated is False
    assert result == content


def test_compound_string() -> None:
    content = 'queue: "myapp-thumbnails"'
    answers = {"project_name": "myapp"}
    result, templated = reverse_substitute(content, answers)
    assert templated is True
    assert "{{ project_name }}-thumbnails" in result


def test_preview_substitutions() -> None:
    content = 'name: myapp\nid: abc-123'
    answers = {"project_name": "myapp", "d1_database_id": "abc-123"}
    previews = preview_substitutions(content, answers)
    assert len(previews) == 2
    vars_found = {p["variable"] for p in previews}
    assert "project_name" in vars_found
    assert "d1_database_id" in vars_found
