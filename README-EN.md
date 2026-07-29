# TestSpec — Spec-First Test Automation Engineering Framework

**English** | **[中文](README.md)**

[![CI](https://github.com/testspec/testspec/actions/workflows/testspec.yml/badge.svg)](https://github.com/testspec/testspec/actions/workflows/testspec.yml)
[![PyPI version](https://img.shields.io/pypi/v/testspec.svg)](https://pypi.org/project/testspec/)
[![Python](https://img.shields.io/pypi/pyversions/testspec.svg)](https://pypi.org/project/testspec/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> A spec-first test automation engineering framework — like OpenSpec, but for testing projects.
> One command to scaffold a new test project with full AI-guided workflow.

---

## Core Philosophy

```
Spec → Cases → Data → Code → Assertion → Verify → Report → Compliance
```

TestSpec enforces: **write the spec document first, then write the test code.**

- The `specs/` directory is the "single source of truth" consumed by both AI and humans
- An 8-step workflow ensures every test case has complete coverage dimensions, data strategy, assertion plan, and compliance checks
- AI strictly follows the spec at each step — no "free improvisation"

---

## Quick Start

```bash
# Install
pip install testspec

# Interactive initialization
testspec init

# Non-interactive (from config file)
testspec init --config project.json

# Quick generate with defaults
testspec init -y

# Validate an existing project
testspec validate ./my-project

# Upgrade framework-managed files
testspec upgrade ./my-project
```

### Generated Project Structure

```
your-project/
├── CLAUDE.md                        ← AI behavior rules + architecture guide
├── testspec.json                    ← TestSpec version marker
├── .claude/commands/                ← 15 AI skill commands (8-step workflow)
├── config/variable_loader.py        ← Deep-merge variable loader
├── utils/                           ← 9 utility modules (HTTP, DB, logger, etc.)
├── testcase/                        ← Test cases (you write these)
├── specs/                           ← Spec documents (you write these)
├── scripts/                         ← 10 tool scripts (compliance, coverage, etc.)
├── ci/                              ← CI/CD configuration
├── variables.yaml                   ← Non-sensitive defaults (committed)
├── variables_override.yaml.template ← Sensitive config guide (committed)
└── requirements.txt                 ← Dynamic dependencies
```

---

## 8-Step Workflow

| Step | Command | Required | Description |
|---|---|---|---|
| — | `/AutomatedTesting` | Entry | Smart dispatcher: analyzes inputs, plans skill sequence |
| 0 | (inline) | ✓ | Read `specs/`, build traceability matrix |
| 1 | `/case-design` | ✓ | Design test case list with coverage dimensions |
| 2 | `/test-data` | Recommended | Design YAML parameterized data |
| 3 | `/write-tests` | ✓ | Generate pytest code skeleton |
| 4 | `/assertion-design` | Recommended | Design assertion strategy |
| 5 | `/data-verify` | ✓ (writes) | Add DB verification for write operations |
| 6 | `/report-decorate` | ✓ | Add Allure annotations |
| 7 | `/compliance-check` | ✓ | Final compliance gate scan |

---

## Supported Test Types

| Type | Description | Step 5 (Data Verify) Meaning |
|---|---|---|
| **api** | HTTP API automation | DB query verification |
| **unit** | Unit tests | Mock call verification |
| **integ** | Integration tests | System state verification |
| **e2e** | End-to-end tests | Multi-layer verification |

## Supported Databases

| Database | Python Driver |
|---|---|
| SQL Server | pymssql + DBUtils |
| MySQL | PyMySQL + DBUtils |
| PostgreSQL | psycopg2 + DBUtils |
| SQLite | sqlite3 (stdlib) |

---

## Key Features

- **Zero external dependencies** for the scaffolder itself (pure Python stdlib)
- **Atomic writes**: temp-dir + rename strategy, auto-cleanup on failure
- **Plugin system**: extend via Python `entry_points` without modifying framework source
- **Hook registry**: lifecycle callbacks at `pre_generate`, `post_section`, `pre_atomic_move`, `post_generate`
- **Project upgrader**: re-generate framework-managed files while preserving user test code
- **Custom template engine**: `{{KEY}}`, `{{#IF_KEY}}`, `{{#FOR var IN LIST}}`, `{{> partial}}`
- **CI/CD**: generates ready-to-use GitHub Actions and GitLab CI configs
- **Non-interactive mode**: `testspec init --config project.json` for CI automation

---

## Extending TestSpec

### Adding a Plugin Section

```python
# my_plugin/sections.py
from testspec import BaseSectionRenderer

class MyCustomSection(BaseSectionRenderer):
    name = "Generate Custom Config"

    @classmethod
    def managed_files(cls):
        return frozenset({"custom-config.yaml"})

    def render(self, ctx, generator):
        generator.write_file("Custom", "custom-config.yaml", "...")
```

Register in your plugin's `pyproject.toml`:

```toml
[project.entry-points."testspec.sections"]
my_custom = "my_plugin.sections:MyCustomSection"
```

Use it:

```bash
testspec init --plugin
```

### Using Lifecycle Hooks

```python
from testspec import HookRegistry, ProjectGenerator

hooks = HookRegistry()
hooks.register("post_generate", lambda ctx, generated: print(f"Generated {len(generated)} files"))

gen = ProjectGenerator(ctx, templates_dir, hook_registry=hooks)
gen.generate()
```

---

## Documentation

| Document | Description |
|---|---|
| [USER-GUIDE.md](USER-GUIDE.md) | Complete user guide (Chinese) |
| [PLAYBOOK.md](PLAYBOOK.md) | Hands-on playbook with e-commerce examples (Chinese) |
| [docs/philosophy.md](docs/philosophy.md) | Spec-first development philosophy |
| [docs/workflow-guide.md](docs/workflow-guide.md) | 8-step workflow detailed guide |
| [docs/extension-guide.md](docs/extension-guide.md) | Framework extension guide |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Contribution guidelines |

> **Note**: Detailed documentation is currently available in Chinese. English translations are planned. Community contributions for translation are welcome!

---

## Requirements

- Python 3.9+
- No external dependencies for the scaffolder itself

---

## Development

```bash
git clone https://github.com/testspec/testspec.git
cd testspec
pip install -e ".[dev]"
pytest
```

---

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## License

[MIT](LICENSE) — free to use and modify.
