"""Reverse Jinja substitution — replace project-specific values with template variables."""

import re

from .config import get_variable_values


def reverse_substitute(
    content: str,
    answers: dict,
) -> tuple[str, bool]:
    """Replace project-specific values in content with Jinja template expressions.

    Returns (processed_content, was_templated) where was_templated indicates
    whether any substitutions were made.

    Strategy:
    - Sort variables longest-first to avoid partial matches
    - Use word-boundary matching for standalone values
    - Handle compound strings (e.g., 'myapp-thumbnails') by substituting
      the project name portion when delimited by -, _, or /
    """
    variables = get_variable_values(answers)
    if not variables:
        return content, False

    result = content
    substituted = False

    # Sort by value length descending (longest first) to avoid partial matches
    sorted_vars = sorted(
        variables.items(), key=lambda kv: len(kv[1]), reverse=True
    )

    for var_name, var_value in sorted_vars:
        if not var_value or len(var_value) < 2:
            continue

        # Exact whole-word/whole-value replacement
        # Use word boundary or start/end of string
        pattern = re.compile(re.escape(var_value))
        jinja_expr = "{{ " + var_name + " }}"

        if pattern.search(result):
            result = pattern.sub(jinja_expr, result)
            substituted = True

    return result, substituted


def preview_substitutions(
    content: str,
    answers: dict,
) -> list[dict[str, str]]:
    """Preview what substitutions would be made, returning a list of dicts
    with 'original', 'replacement', and 'variable' keys."""
    variables = get_variable_values(answers)
    if not variables:
        return []

    previews: list[dict[str, str]] = []

    sorted_vars = sorted(
        variables.items(), key=lambda kv: len(kv[1]), reverse=True
    )

    for var_name, var_value in sorted_vars:
        if not var_value or len(var_value) < 2:
            continue

        pattern = re.compile(re.escape(var_value))
        if pattern.search(content):
            previews.append({
                "variable": var_name,
                "original": var_value,
                "replacement": "{{ " + var_name + " }}",
            })

    return previews
