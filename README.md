# copyback

Reverse-sync tool for [Copier](https://copier.readthedocs.io/) templates — push project changes back to the template.

## The problem

When you use Copier to generate a project, changes flow one way: template → project. But sometimes you improve files in the generated project and want those changes reflected in the template. Manually copying files back and re-inserting Jinja variables is tedious and error-prone.

**copyback** automates this by detecting divergent files, reverse-substituting project values back into Jinja template variables, and writing the results to your template repo.

## Installation

```
pip install copyback
```

Requires Python 3.12+.

## Usage

Run commands from within a Copier-generated project directory (one that contains a `.copier-answers.yml` file).

### `copyback status`

Show which project files have diverged from the template:

```
copyback status
```

Pass a specific project directory:

```
copyback status /path/to/project
```

### `copyback push`

Push changed files back to the template, reverse-substituting project values into Jinja variables:

```
# Interactive selection of divergent files
copyback push

# Push specific files
copyback push src/config.py pyproject.toml

# Push all divergent files
copyback push --all

# Preview without writing
copyback push --all --dry-run

# Push and commit in the template repo
copyback push --all --commit
```

### `copyback add`

Add new project files (ones that don't yet exist in the template) with interactive detection of template variables:

```
# Add files to the template
copyback add src/new_module.py tests/test_new.py

# Preview what would be added
copyback add src/new_module.py --dry-run
```

## Options

All commands accept:

- `--template-dir`, `-t` — Path to the template repo (auto-detected from `.copier-answers.yml` if possible)
- `--project-dir`, `-p` — Project directory (defaults to current directory, positional arg for `status`)

## License

MIT
