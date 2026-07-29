# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **`ValidationError` exception class** for project integrity validation errors
- **`CODE_OF_CONDUCT.md`** — Contributor Covenant 2.0
- **`SECURITY.md`** — responsible disclosure policy and supported versions
- **`.github/workflows/publish.yml`** — automated PyPI publish on GitHub Release
- **`authors` field** in `pyproject.toml` for full PyPI metadata
- **`test_yaml_emitter.py`** — dedicated test suite for the YAML emitter (40+ tests)
- **`test_validator.py`** — dedicated test suite for the project validator (20+ tests)
- **`_VALID_PIP_LINE_PREFIXES`** and `_is_valid_pip_line()` in validator for accurate pip syntax recognition
- **`_EXCLUDED_DIR_NAMES`** in validator to skip virtualenvs during syntax scans
- **`index` parameter** on `OptionRegistry.valid_values()` for extracting values at arbitrary tuple positions
- **Thread-safety note** in `HookRegistry` docstring

### Changed
- **`SKILL_FILES`** is now `tuple[SkillFile, ...]` (was mutable `list`)
- **`UpgradeAction.status`** uses `Literal["updated", "new", "unchanged", "skipped"]`
- **`ValidationResult.status/category`** use `Literal` types for static safety
- **`ScriptsSection.render()`** iterates `_SCRIPT_NAMES` (single source of truth) instead of a separate hardcoded list
- **CI pipeline** now triggers on PRs to `develop` branch and includes `mypy` type-checking job
- **CI secret handling** uses `printf '%s\n'` instead of `echo` to prevent log exposure

### Removed
- **`_parse_version()`** dead code from `upgrader.py` (never called)

### Fixed
- **yaml_emitter multiline block scalar** in first list-item key no longer produces invalid YAML (body lines were prefixed with `- `)
- **CI builders** secret values no longer exposed via `echo` in shell trace mode
- **Upgrader** raises `ConfigError` instead of `KeyError` for missing `project_name` in manifest
- **Generator public methods** (`render_template_file`, `write_file`, `copy_static_file`) now raise clear `GenerationError` when called before initialization
- **Validator requirements check** correctly accepts `-r`, `-e`, `--index-url`, URL, and VCS install lines
- **Validator syntax scan** excludes `.venv/`, `__pycache__/`, and other non-project directories
- **`HookRegistry.fire()`** iterates a snapshot copy, safe when callbacks modify the registry
- **Template engine** `_FOR_OPEN_RE` regex moved to module level (was compiled inside hot function)

## [1.2.0] - 2026-07-01

### Added
- **HookRegistry lifecycle events**: `pre_generate`, `post_section`, `pre_atomic_move`, `post_generate`
- **Plugin system**: third-party `SectionRenderer` plugins via `entry_points`
- **`copy_static_file()` public API** on `ProjectGenerator` for non-template file copies
- **`--plugin` CLI flag** for loading plugin sections during `init`
- **`testspec upgrade` command** for upgrading framework-managed files in existing projects
- **`testspec validate` command** for project integrity checks
- **`--dry-run` flag** for previewing generated files without writing to disk
- **`--verbose` / `-v` global flag** for debug-level logging
- **FOR loop support** in template engine: `{{#FOR var IN LIST_KEY}}...{{/FOR}}`
- **Include directive** in template engine: `{{> partial_name}}`
- **Escape syntax**: `\{{` and `\}}` for literal braces in templates
- **`QuotedStr`** class in YAML emitter for explicit string quoting
- **`ProjectUpgrader`** with plan/apply two-phase upgrade strategy
- **English locale support** (`language_locale: "en"`)
- Python 3.13 support in CI matrix

### Changed
- **Refactored generator**: content builders extracted to `ci_builders.py`, rendering split into `sections.py`
- **`ProjectContext` now uses TypedDict + dataclass** dual-layer for type safety and runtime validation
- **OptionRegistry** replaces hardcoded option dicts for runtime extensibility
- **Data catalogs** (`TYPE_DESC_MAP`, `DB_PORT_MAP`, `SKILL_FILES`) extracted from `constants.py` to `catalogs.py`
- **CI YAML generation** uses structured `yaml_dump()` instead of f-string concatenation (GitHub Actions)
- **Deprecated** `_render()` and `_write_raw()` methods in favor of `render_template_file()` and `write_file()`

### Fixed
- Atomic move now uses rename-aside strategy to prevent data loss on failure
- Template engine correctly handles nested FOR blocks with depth-counting parser
- Residual placeholder detection filters out lowercase keys and double-underscore prefixes
- `MockSection` and `ProjectFilesSection` use public API instead of directly accessing `temp_dir`

## [1.1.0] - 2026-06-01

### Added
- `testspec` CLI entry point via `pyproject.toml` `[project.scripts]`
- Non-interactive mode: `testspec init --config project.json`
- `ProjectValidator` for project integrity checks
- `build_testspec_manifest()` for generating `testspec.json`
- Spec DSL v2.0: auth, structured constraints, SELECT operations, SLA definitions

### Changed
- `init.py` now delegates to `testspec.cli` (backward-compatible entry point)
- Template engine now iterates condition blocks until convergence

## [1.0.0] - 2026-05-01

### Added
- Initial release: spec-first test automation scaffolding framework
- Interactive wizard with 8-step guided setup
- Template engine with `{{KEY}}`, `{{#IF_KEY}}`, `{{#IF_NOT_KEY}}`, `{{#IF_KEY}}...{{#ELSE}}...{{/IF_KEY}}`
- 12 section renderers for complete project generation
- Atomic write with temp-dir + move strategy
- Support for 4 test types: api, unit, integ, e2e
- Support for 4 databases: SQL Server, MySQL, PostgreSQL, SQLite
- 15 Claude Code skill commands for 8-step workflow
- CI/CD templates for GitHub Actions and GitLab CI
- Docker compose templates for test databases
