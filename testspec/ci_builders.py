"""TestSpec 内容构建器。

从 generator.py 提取的纯函数，负责根据 ProjectContext 生成各类文件内容。
包括 requirements.txt、.gitignore、CI YAML、testspec.json 清单等。
"""

from __future__ import annotations

import json
import warnings
from typing import Any

from .constants import (
    VERSION, DB_DEPS,
    CI_PYTHON_VERSION, CI_COVERAGE_THRESHOLD, CI_FLAKY_THRESHOLD,
    CI_TEST_RERUNS, CI_RERUNS_DELAY,
    DatabaseType, CISystem,
)
from .context import ProjectContext
from .yaml_emitter import yaml_dump, QuotedStr

__all__ = [
    "build_requirements",
    "build_gitignore",
    "build_github_actions_yaml",
    "build_gitlab_ci_yaml",
    "build_testspec_manifest",
]


# ---------------------------------------------------------------------------
# 动态 requirements.txt
# ---------------------------------------------------------------------------

def build_requirements(ctx: ProjectContext) -> str:
    """根据上下文动态生成 requirements.txt。"""
    deps = [
        "# TestSpec 框架自动生成的依赖",
        f"# 项目: {ctx['PROJECT_NAME']}",
        f"# 测试类型: {', '.join(ctx['TEST_TYPES'])}",
        "",
        "# 测试框架核心",
        "pytest>=7.4",
        "pytest-xdist>=3.5",
    ]

    if ctx["HAS_ALLURE"]:
        deps.extend(["", "# 报告 - Allure", "allure-pytest>=2.13.0"])
    if ctx["HAS_HTML_REPORT"]:
        deps.extend(["", "# 报告 - HTML", "pytest-html>=4.1"])

    deps.extend(["", "# 测试辅助", "pytest-rerunfailures>=12.0"])

    if ctx["IS_UNIT"]:
        deps.extend(["", "# Property-Based Testing", "hypothesis>=6.0"])

    if ctx["HAS_HTTP"]:
        deps.extend(["", "# HTTP", "requests>=2.31"])

    deps.extend([
        "", "# 配置与数据",
        "PyYAML>=6.0", "faker>=19.0.0", "openpyxl>=3.1.0",
    ])

    if ctx["HAS_DB"]:
        db = ctx["DB_TYPE"]
        if db in DB_DEPS:
            deps.extend(["", "# 数据库"])
            deps.extend(DB_DEPS[db])
        elif db not in {dt.value for dt in DatabaseType}:
            warnings.warn(
                f"未知数据库类型 '{db}'，未生成对应驱动依赖。"
                f"已知类型: {', '.join(DB_DEPS)}",
                stacklevel=2,
            )

    deps.extend([
        "", "# 并发安全", "filelock>=3.12",
        "", "# 数据校验", "pydantic>=2.6",
        "", "# Mock 服务", "responses>=0.25",
        "", "# Git Hooks", "pre-commit>=3.6",
    ])

    return "\n".join(deps) + "\n"


# ---------------------------------------------------------------------------
# .gitignore
# ---------------------------------------------------------------------------

def build_gitignore(ctx: ProjectContext) -> str:
    """生成 .gitignore 内容，根据项目配置动态调整。"""
    lines = [
        "# Python",
        "__pycache__/",
        "*.py[cod]",
        "*$py.class",
        "*.egg-info/",
        "dist/",
        "build/",
        ".eggs/",
        "",
        "# 虚拟环境",
        ".venv/",
        "venv/",
        "env/",
        "",
        "# IDE",
        ".idea/",
        ".vscode/",
        "*.swp",
        "*.swo",
        "",
        "# 测试产物",
        "logs/",
        "reports/",
        "htmlcov/",
        ".coverage",
        "junit-*.xml",
    ]

    if ctx["HAS_ALLURE"]:
        lines.extend([".allure/"])

    lines.extend([
        "",
        "# 敏感配置（高优先级覆盖）",
        "variables_override.yaml",
        "*.override.yaml",
        "",
        "# 本地 token 缓存",
        "*.local.yaml",
        "",
        "# 环境变量文件",
        ".env",
        ".env.*",
        "!.env.example",
        "",
        "# OS",
        ".DS_Store",
        "Thumbs.db",
    ])

    if ctx["HAS_DB"] and ctx["DB_TYPE"] == "sqlite":
        lines.extend(["", "# SQLite", "*.db", "*.sqlite3"])

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# CI YAML 生成（非注释，直接可用）
# ---------------------------------------------------------------------------

def _build_e2e_args(has_allure: bool) -> str:
    """构建 E2E 测试阶段的 pytest 参数字符串。"""
    args = (
        f'testcase/ -m "not smoke" -v --junit-xml=reports/e2e.xml'
        f" --reruns {CI_TEST_RERUNS} --reruns-delay {CI_RERUNS_DELAY}"
    )
    if has_allure:
        args += " --alluredir=reports/allure-results"
    return args


def build_github_actions_yaml(ctx: ProjectContext) -> str:
    """生成可直接使用的 GitHub Actions workflow YAML（结构化构建）。

    使用 yaml_dump 将 Python dict 序列化为 YAML，替代 f-string 拼接。
    条件步骤（如 Allure）通过 dict 操作添加/移除。
    """
    has_allure = ctx["HAS_ALLURE"]
    e2e_args = _build_e2e_args(has_allure)

    # -- 构建步骤列表 --
    steps: list[dict[str, Any]] = [
        {"uses": "actions/checkout@v4", "with": {"fetch-depth": 0}},
        {
            "name": "Set up Python",
            "uses": "actions/setup-python@v5",
            "with": {
                "python-version": QuotedStr(CI_PYTHON_VERSION),
                "cache": QuotedStr("pip"),
            },
        },
        {"name": "Install dependencies", "run": "pip install -r requirements.txt"},
        {"name": "Configure override", "run": "echo \"${{ secrets.VARIABLES_OVERRIDE }}\" > variables_override.yaml"},
        {"name": "Validate Specs", "run": "python scripts/validate_specs.py"},
        {
            "name": "Check Coverage",
            "run": f"python scripts/check_coverage.py --threshold {CI_COVERAGE_THRESHOLD}",
        },
        {
            "name": "Spec Change Impact",
            "if": "github.event_name == 'pull_request'",
            "run": "python scripts/spec_diff.py --branch origin/main",
        },
        {"name": "Compliance Check", "run": "python scripts/check_compliance.py"},
        {
            "name": "Run Smoke Tests",
            "run": "pytest testcase/ -m smoke -v -n auto --junit-xml=reports/smoke.xml",
        },
        {"name": "Run E2E Tests", "run": f"pytest {e2e_args}"},
        {
            "name": "Generate Metrics",
            "if": "always()",
            "run": "python scripts/generate_metrics.py --output reports/metrics.json --pretty",
        },
        {
            "name": "Detect Flaky Tests",
            "if": "always()",
            "run": f"python scripts/detect_flaky.py --threshold {CI_FLAKY_THRESHOLD}",
        },
        {
            "name": "Upload JUnit Results",
            "if": "always()",
            "uses": "actions/upload-artifact@v4",
            "with": {"name": "test-results", "path": "reports/*.xml"},
        },
        {
            "name": "Upload Metrics",
            "if": "always()",
            "uses": "actions/upload-artifact@v4",
            "with": {"name": "quality-metrics", "path": "reports/metrics.json"},
        },
    ]

    if has_allure:
        steps.append({
            "name": "Publish Allure Report",
            "if": "always()",
            "uses": "simple-elf/allure-report-action@v1.9",
            "with": {
                "allure_results": "reports/allure-results",
                "allure_report": "reports/allure-report",
            },
        })

    # -- 构建完整 workflow 结构 --
    workflow: dict[str, Any] = {
        "name": "TestSpec CI",
        "on": {
            "push": {"branches": ["main", "develop"]},
            "pull_request": {"branches": ["main"]},
            "schedule": [{"cron": "0 2 * * *"}],
        },
        "jobs": {
            "testspec": {
                "runs-on": "ubuntu-latest",
                "steps": steps,
            },
        },
    }

    header = (
        f"# TestSpec CI Pipeline — {ctx['PROJECT_NAME_TITLE']}\n"
        f"# Auto-generated by TestSpec v{ctx['TESTSPEC_VERSION']}\n"
    )
    return header + "\n" + yaml_dump(workflow)


def _build_gitlab_job_dict(
    stage: str,
    script: list[str],
    *,
    artifacts_junit: str = "",
    artifact_paths: list[str] | None = None,
    only: list[str] | None = None,
    when: str = "",
) -> dict[str, Any]:
    """构建单个 GitLab CI job 的 dict 结构（使用 extends: .python_setup）。

    替代原 ``_build_gitlab_job`` 的 f-string 拼接方式，
    返回纯 dict 以便统一通过 ``yaml_dump`` 序列化。

    Args:
        stage: 所属阶段（``"validate"`` / ``"test"`` / ``"quality"``）
        script: 执行的脚本命令列表
        artifacts_junit: JUnit 报告路径（空字符串表示不配置）
        artifact_paths: 额外产物路径列表
        only: 触发条件列表（如 ``["merge_requests"]``）
        when: 执行条件（如 ``"always"``）
    """
    job: dict[str, Any] = {
        "extends": ".python_setup",
        "stage": stage,
        "script": script,
    }
    if artifacts_junit or artifact_paths:
        artifacts: dict[str, Any] = {}
        if artifacts_junit:
            artifacts["reports"] = {"junit": artifacts_junit}
        if artifact_paths:
            artifacts["paths"] = artifact_paths
        job["artifacts"] = artifacts
    if only:
        job["only"] = only
    if when:
        job["when"] = when
    return job


def build_gitlab_ci_yaml(ctx: ProjectContext) -> str:
    """生成可直接使用的 GitLab CI YAML（纯 dict + yaml_dump）。

    使用 ``extends: .python_setup``（GitLab CI 原生关键字）替代
    YAML merge key ``<<: *python_setup``，使整个 pipeline 可通过
    ``yaml_dump`` 统一序列化，消除 f-string 拼接。

    ``.python_setup`` 是 GitLab CI 的隐藏 job（以 ``.`` 开头），
    各阶段 job 通过 ``extends`` 引用它来共享 Python 环境配置。
    """
    has_allure = ctx["HAS_ALLURE"]
    e2e_args = _build_e2e_args(has_allure)

    e2e_artifact_paths: list[str] = ["reports/e2e.xml"]
    if has_allure:
        e2e_artifact_paths.append("reports/allure-results")

    pipeline: dict[str, Any] = {
        "stages": ["validate", "test", "quality"],
        "variables": {
            "PIP_CACHE_DIR": "$CI_PROJECT_DIR/.cache/pip",
        },
        ".python_setup": {
            "image": f"python:{CI_PYTHON_VERSION}",
            "before_script": [
                "pip install -r requirements.txt",
                "echo \"$VARIABLES_OVERRIDE\" > variables_override.yaml",
            ],
        },
        "validate-specs": _build_gitlab_job_dict(
            "validate",
            [
                "python scripts/validate_specs.py",
                f"python scripts/check_coverage.py --threshold {CI_COVERAGE_THRESHOLD}",
                "python scripts/check_compliance.py",
            ],
        ),
        "spec-impact": _build_gitlab_job_dict(
            "validate",
            ["python scripts/spec_diff.py --branch origin/$CI_DEFAULT_BRANCH"],
            only=["merge_requests"],
        ),
        "test-smoke": _build_gitlab_job_dict(
            "test",
            ["pytest testcase/ -m smoke -v --junit-xml=reports/smoke.xml"],
            artifacts_junit="reports/smoke.xml",
        ),
        "test-e2e": _build_gitlab_job_dict(
            "test",
            [f"pytest {e2e_args}"],
            artifacts_junit="reports/e2e.xml",
            artifact_paths=e2e_artifact_paths,
        ),
        "quality-metrics": _build_gitlab_job_dict(
            "quality",
            [
                "python scripts/generate_metrics.py --output reports/metrics.json --pretty",
                f"python scripts/detect_flaky.py --threshold {CI_FLAKY_THRESHOLD}",
            ],
            artifact_paths=["reports/metrics.json"],
            when="always",
        ),
    }

    if has_allure:
        pipeline["pages"] = {
            "stage": "quality",
            "image": "node:lts",
            "before_script": ["npm install -g allure-commandline"],
            "script": [
                "allure generate reports/allure-results -o public/ --clean",
            ],
            "artifacts": {"paths": ["public"]},
            "only": ["main"],
            "when": "always",
        }

    header = (
        f"# TestSpec CI Pipeline — {ctx['PROJECT_NAME_TITLE']}\n"
        f"# Auto-generated by TestSpec v{ctx['TESTSPEC_VERSION']}\n"
    )
    return header + "\n" + yaml_dump(pipeline)


# ---------------------------------------------------------------------------
# TestSpec 版本标记文件
# ---------------------------------------------------------------------------

def build_testspec_manifest(ctx: ProjectContext) -> str:
    """生成 testspec.json 版本标记文件，用于升级追踪。"""
    manifest = {
        "testspec_version": ctx["TESTSPEC_VERSION"],
        "project_name": ctx["PROJECT_NAME"],
        "test_types": ctx["TEST_TYPES"],
        "language": ctx["LANGUAGE"],
        "framework": ctx["TEST_FRAMEWORK"],
        "database": ctx["DB_TYPE"],
        "ci_system": ctx["CI_SYSTEM"],
        "report_tool": ctx["REPORT_TOOL"],
        "business_lines": ctx["BUSINESS_LINES_RAW"],
        "language_locale": "zh" if ctx["LANG_ZH"] else "en",
    }
    return json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
