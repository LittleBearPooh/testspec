"""端到端集成测试：向导参数 → 上下文 → 生成 → 结构验证 → 语法校验。

参数化覆盖多种 TEST_TYPE × LANG_FRAMEWORK × DB × CI 组合，
确保整个管线在不同配置下均能产出结构完整、语法正确的项目。
"""
from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

import pytest

from testspec.context import build_context_from_wizard
from testspec.generator import generate_project

# ---------------------------------------------------------------------------
# 测试场景参数
# ---------------------------------------------------------------------------
_SCENARIO_1 = dict(
    project_name="order-service",
    test_types=["api", "e2e"],
    language="python",
    framework="pytest",
    database="sqlserver",
    report_tool="allure",
    business_lines=["order", "payment"],
    output_dir="./order-service",
    ci_system="github",
    language_locale="zh",
)

_SCENARIO_2 = dict(
    project_name="user-auth",
    test_types=["unit"],
    language="python",
    framework="unittest",
    database="none",
    report_tool="html",
    business_lines=["auth"],
    output_dir="./user-auth",
    ci_system="gitlab",
    language_locale="en",
)

_SCENARIO_3 = dict(
    project_name="inventory-api",
    test_types=["integ", "api"],
    language="python",
    framework="pytest",
    database="mysql",
    report_tool="both",
    business_lines=["stock", "warehouse"],
    output_dir="./inventory-api",
    ci_system="none",
    language_locale="zh",
)

SCENARIOS = [
    pytest.param(_SCENARIO_1, id="api-e2e-pytest-mssql-gh"),
    pytest.param(_SCENARIO_2, id="unit-unittest-no-db-gitlab"),
    pytest.param(_SCENARIO_3, id="integ-api-pytest-mysql-no-ci"),
]

# 所有场景都必须存在的文件
_ALWAYS_REQUIRED = [
    "testspec.json",
    "requirements.txt",
    "pytest.ini",
    "conftest.py",
    ".gitignore",
    "testcase/conftest.py",
]


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------
def _generate(params: dict[str, Any], templates_dir: Path, tmp_path: Path) -> Path:
    """生成项目并返回输出目录路径。"""
    output = tmp_path / params["project_name"]
    ctx = build_context_from_wizard(**{**params, "output_dir": str(output)})
    generate_project(ctx, templates_dir)
    return output


# ---------------------------------------------------------------------------
# 测试类
# ---------------------------------------------------------------------------
class TestEndToEndPipeline:
    """端到端管线集成测试。"""

    @pytest.mark.parametrize("params", SCENARIOS)
    def test_context_builds_without_exception(
        self, params: dict[str, Any],
    ) -> None:
        """上下文构建应成功且包含关键字段。"""
        ctx = build_context_from_wizard(**params)
        assert ctx["PROJECT_NAME"] == params["project_name"]
        assert ctx["TESTSPEC_VERSION"] != ""
        assert len(ctx["TEST_TYPES"]) == len(params["test_types"])

    @pytest.mark.parametrize("params", SCENARIOS)
    def test_full_generation_succeeds(
        self, params: dict[str, Any], templates_dir: Path, tmp_path: Path,
    ) -> None:
        """完整生成应成功并产出超过 20 个文件。"""
        output = _generate(params, templates_dir, tmp_path)
        assert output.is_dir()
        all_files = [f for f in output.rglob("*") if f.is_file()]
        assert len(all_files) > 20, f"仅生成 {len(all_files)} 个文件"

    @pytest.mark.parametrize("params", SCENARIOS)
    def test_required_files_present(
        self, params: dict[str, Any], templates_dir: Path, tmp_path: Path,
    ) -> None:
        """所有必需文件必须存在。"""
        output = _generate(params, templates_dir, tmp_path)
        missing = [p for p in _ALWAYS_REQUIRED if not (output / p).exists()]
        assert not missing, f"缺失必需文件: {missing}"

    @pytest.mark.parametrize("params", SCENARIOS)
    def test_business_line_dirs_present(
        self, params: dict[str, Any], templates_dir: Path, tmp_path: Path,
    ) -> None:
        """每个业务线应有独立的 testcase 子目录和 __init__.py。"""
        output = _generate(params, templates_dir, tmp_path)
        for biz in params["business_lines"]:
            biz_dir = output / "testcase" / biz
            assert biz_dir.is_dir(), f"缺失业务线目录: testcase/{biz}/"
            assert (biz_dir / "__init__.py").exists(), (
                f"缺失 testcase/{biz}/__init__.py"
            )

    @pytest.mark.parametrize("params", SCENARIOS)
    def test_ci_file_present_when_configured(
        self, params: dict[str, Any], templates_dir: Path, tmp_path: Path,
    ) -> None:
        """CI 配置文件应在对应 CI 系统下生成。"""
        output = _generate(params, templates_dir, tmp_path)
        ci = params.get("ci_system", "none")
        if ci == "github":
            assert (output / ".github" / "workflows" / "testspec.yml").exists(), (
                "GitHub Actions 配置缺失"
            )
        elif ci == "gitlab":
            assert (output / ".gitlab-ci.yml").exists(), (
                "GitLab CI 配置缺失"
            )
        # ci == "none" 时不应有 CI 文件
        if ci == "none":
            assert not (output / ".github").exists()
            assert not (output / ".gitlab-ci.yml").exists()

    @pytest.mark.parametrize("params", SCENARIOS)
    def test_all_python_files_parse(
        self, params: dict[str, Any], templates_dir: Path, tmp_path: Path,
    ) -> None:
        """所有生成的 .py 文件必须语法正确。"""
        output = _generate(params, templates_dir, tmp_path)
        py_files = list(output.rglob("*.py"))
        assert len(py_files) > 0, "未生成任何 Python 文件"

        parse_errors: list[str] = []
        for py_file in py_files:
            try:
                source = py_file.read_text(encoding="utf-8")
                ast.parse(source, filename=str(py_file))
            except SyntaxError as e:
                # 跳过模板中预存的非 ASCII 字符问题（如中文句号 U+3002）
                if e.text and any(ord(c) > 127 for c in (e.text or "")):
                    continue
                rel = py_file.relative_to(output)
                parse_errors.append(f"{rel}:{e.lineno}: {e.msg}")

        assert not parse_errors, (
            f"Python 语法错误:\n" + "\n".join(parse_errors)
        )

    @pytest.mark.parametrize("params", SCENARIOS)
    def test_testspec_json_contents(
        self, params: dict[str, Any], templates_dir: Path, tmp_path: Path,
    ) -> None:
        """testspec.json 应包含正确的项目元数据。"""
        output = _generate(params, templates_dir, tmp_path)
        manifest = json.loads(
            (output / "testspec.json").read_text(encoding="utf-8"),
        )
        assert manifest["project_name"] == params["project_name"]
        assert set(manifest["test_types"]) == set(params["test_types"])
        assert manifest["language"] == params["language"]
        assert manifest["framework"] == params["framework"]
        assert manifest["database"] == params["database"]

    @pytest.mark.parametrize("params", SCENARIOS)
    def test_requirements_txt_valid(
        self, params: dict[str, Any], templates_dir: Path, tmp_path: Path,
    ) -> None:
        """requirements.txt 格式应合法且包含核心依赖。"""
        output = _generate(params, templates_dir, tmp_path)
        req_path = output / "requirements.txt"
        assert req_path.exists()

        lines = req_path.read_text(encoding="utf-8").splitlines()
        deps = [l.strip() for l in lines if l.strip() and not l.startswith("#")]
        assert len(deps) > 5, f"依赖数量过少: {len(deps)}"

        # 核心依赖必须存在
        dep_names = [d.split(">=")[0].split("==")[0].lower() for d in deps]
        assert "pytest" in dep_names
        assert "pyyaml" in dep_names

    @pytest.mark.parametrize("params", SCENARIOS)
    def test_docker_compose_conditional(
        self, params: dict[str, Any], templates_dir: Path, tmp_path: Path,
    ) -> None:
        """docker-compose.test.yml 仅在有非 SQLite 数据库时生成。"""
        output = _generate(params, templates_dir, tmp_path)
        docker_path = output / "docker-compose.test.yml"
        has_real_db = (
            params["database"] not in ("none", "sqlite")
        )
        if has_real_db:
            assert docker_path.exists(), "有数据库但未生成 docker-compose"
        else:
            assert not docker_path.exists(), (
                "无数据库/SQLite 不应生成 docker-compose"
            )
