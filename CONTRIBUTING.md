# Contributing to TestSpec

Thank you for your interest in contributing to TestSpec! This document provides guidelines and information for contributors.

## Code of Conduct

Please read our [Code of Conduct](CODE_OF_CONDUCT.md). By participating in this project, you agree to maintain a respectful and inclusive environment for everyone.

## How to Contribute

### Reporting Bugs

1. Check existing [issues](../../issues) to avoid duplicates
2. Use the bug report template
3. Include:
   - Python version (`python --version`)
   - TestSpec version (`testspec version`)
   - Steps to reproduce
   - Expected vs actual behavior
   - Relevant error messages

### Suggesting Features

1. Open a [discussion](../../discussions) or [issue](../../issues) with the `enhancement` label
2. Describe the use case and motivation
3. If possible, propose an API or interface design

### Submitting Pull Requests

1. Fork the repository and create a feature branch from `main`
2. Set up the development environment (see below)
3. Make your changes with clear, focused commits
4. Add or update tests as needed
5. Ensure all tests pass and coverage stays above 80%
6. Update documentation if you change behavior
7. Submit a pull request with a clear description

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/testspec.git
cd testspec

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install in development mode with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run linting
ruff check testspec/
ruff format --check testspec/

# Run type checking (optional)
mypy testspec/
```

## Project Structure

```
testspec/
├── testspec/          # Python package (CLI + modules)
│   ├── cli.py         # CLI entry point
│   ├── generator.py   # Project generator (atomic write)
│   ├── renderer.py    # Template engine
│   ├── sections.py    # 12 section renderers
│   ├── context.py     # Context builder (TypedDict + dataclass)
│   ├── hooks.py       # Lifecycle hook registry
│   ├── plugins.py     # Plugin discovery (entry_points)
│   ├── upgrader.py    # Project upgrader
│   ├── validator.py   # Project validator
│   ├── ci_builders.py # Dynamic file content builders
│   ├── yaml_emitter.py# Zero-dependency YAML serializer
│   ├── catalogs.py    # Data mappings and skill file list
│   ├── constants.py   # Version, enums, validation sets
│   ├── registry.py    # OptionRegistry mechanism
│   ├── exceptions.py  # Exception hierarchy
│   ├── wizard.py      # Interactive wizard
│   └── templates/     # All template files
├── tests/             # Unit tests
├── docs/              # Documentation
├── .github/           # CI/CD workflows
│   ├── workflows/testspec.yml   # Lint + test + mypy
│   └── workflows/publish.yml   # PyPI publish on release
├── CODE_OF_CONDUCT.md # Contributor Covenant
├── SECURITY.md        # Security policy
└── init.py            # Backward-compatible script entry
```

## Coding Standards

- **Python 3.9+** compatible (use `from __future__ import annotations`)
- **Type hints** on all public functions and methods
- **Docstrings** in Google/NumPy style on all public APIs
- **Ruff** for linting and formatting (config in `pyproject.toml`)
- **100 char line length** (configured in ruff)
- All new features must include tests
- Keep backward compatibility for public APIs

## Architecture Guidelines

### Adding a New Section Renderer

1. Create a class extending `BaseSectionRenderer` in `sections.py`
2. Set `name` attribute (displayed in progress messages)
3. Implement `render(ctx, generator)` using `generator.render_template_file()` or `generator.write_file()`
4. Implement `managed_files()` returning a `frozenset` of relative paths (used by upgrader)
5. Add the class to `ALL_SECTION_CLASSES` list
6. Add tests in `tests/test_sections.py`

### Adding a New Template

1. Place the template in `testspec/templates/<category>/`
2. Use `.tpl` extension for files that need placeholder substitution
3. Register it in the appropriate `SectionRenderer.render()` method
4. Use template engine syntax: `{{KEY}}`, `{{#IF_KEY}}`, `{{#FOR var IN LIST_KEY}}`

### Adding a New Context Key

Update all four locations:
1. `ProjectContext` TypedDict in `context.py`
2. `_ProjectContextModel` dataclass in `context.py`
3. The appropriate `_build_xxx_ctx()` sub-builder in `context.py`
4. `__post_init__` if cross-field validation is needed

## Testing

```bash
# Run all tests with coverage
pytest --cov=testspec --cov-report=term-missing -v

# Run specific test file
pytest tests/test_renderer.py -v

# Run with specific marker
pytest -m "not slow"
```

Coverage must stay above **80%**. The CI pipeline enforces this.

## Documentation

- User-facing docs: `README.md`, `USER-GUIDE.md`, `PLAYBOOK.md`
- Developer docs: `docs/extension-guide.md`
- Inline docs: docstrings on all public APIs
- When changing behavior, update all relevant docs

## Commit Message Convention

```
type: short description

[optional body]
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `perf`, `ci`

## Release Process

1. Update `VERSION` in `testspec/constants.py`
2. Update `CHANGELOG.md` with the new version section (move items from `[Unreleased]`)
3. Create a git tag: `git tag v1.x.x`
4. Push to GitHub and create a Release — the `.github/workflows/publish.yml` workflow will automatically build and publish to PyPI

## Questions?

Open a [discussion](../../discussions) or reach out to the maintainers.
