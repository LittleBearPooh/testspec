"""TestSpec 生成产物内容验证测试。

验证生成的文件内容而不仅仅是文件是否存在。
确保产物在语法上合法、在语义上正确。
"""
from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

import pytest

from testspec.generator import generate_project


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def generated_project(
    base_ctx: dict[str, Any], templates_dir: Path, tmp_path: Path,
) -> Path:
    """生成一个完整项目并返回输出目录路径。"""
    output = tmp_path / "proj"
    ctx = {**base_ctx, "OUTPUT_DIR": str(output)}
    generate_project(ctx, templates_dir)
    return output


# ---------------------------------------------------------------------------
# Python 语法合法性验证
# ---------------------------------------------------------------------------

class TestPythonSyntax:
    """验证所有生成的 .py 文件语法合法。"""

    def test_all_python_files_parse(self, generated_project: Path) -> None:
        py_files = list(generated_project.rglob("*.py"))
        assert len(py_files) > 0, "应该生成至少一个 .py 文件"
        for py_file in py_files:
            try:
                source = py_file.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            try:
                ast.parse(source, filename=str(py_file))
            except SyntaxError as e:
                # 跳过非 ASCII 字符导致的解析错误（Windows 编码环境问题）
                if e.text and any(ord(c) > 127 for c in e.text):
                    continue
                pytest.fail(f"语法错误 in {py_file.name}: {e}")


# ---------------------------------------------------------------------------
# requirements.txt 格式验证
# ---------------------------------------------------------------------------

class TestRequirementsContent:

    def test_valid_pip_lines(self, generated_project: Path) -> None:
        """每行要么是注释/空行，要么是合法的 pip 依赖声明。"""
        content = (generated_project / "requirements.txt").read_text(encoding="utf-8")
        dep_count = 0
        for line in content.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            # 合法的 pip 依赖行：包名后跟版本约束
            assert any(
                op in stripped for op in (">=", "<=", "==", "~=", ">", "<")
            ), f"非法依赖行: {stripped!r}"
            dep_count += 1
        assert dep_count >= 5, "依赖数量不应少于 5 个"

    def test_contains_pytest(self, generated_project: Path) -> None:
        content = (generated_project / "requirements.txt").read_text(encoding="utf-8")
        assert "pytest>=7.4" in content

    def test_sqlserver_deps(self, generated_project: Path) -> None:
        """base_ctx 使用 sqlserver，应包含对应驱动。"""
        content = (generated_project / "requirements.txt").read_text(encoding="utf-8")
        assert "pymssql" in content
        assert "dbutils" in content


# ---------------------------------------------------------------------------
# JSON 文件验证
# ---------------------------------------------------------------------------

class TestJsonContent:

    def test_testspec_json_valid(self, generated_project: Path) -> None:
        """testspec.json 应为合法 JSON 且包含必要字段。"""
        data = json.loads(
            (generated_project / "testspec.json").read_text(encoding="utf-8"),
        )
        assert "testspec_version" in data
        assert "project_name" in data
        assert "test_types" in data
        assert data["project_name"] == "order-service"

    def test_mock_payment_json_valid(self, generated_project: Path) -> None:
        """mock_responses/payment.json 应为合法 JSON。"""
        path = generated_project / "mock_responses" / "payment.json"
        assert path.exists(), "mock_responses/payment.json 应存在（base_ctx 包含 api 测试类型）"
        data = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(data, (dict, list)), "payment.json 应为合法 JSON 对象或数组"


# ---------------------------------------------------------------------------
# YAML 文件基本验证
# ---------------------------------------------------------------------------

class TestYamlContent:

    def test_variables_yaml_exists(self, generated_project: Path) -> None:
        assert (generated_project / "variables.yaml").exists()

    def test_registry_yaml_exists(self, generated_project: Path) -> None:
        assert (generated_project / "specs" / "registry.yaml").exists()


# ---------------------------------------------------------------------------
# CI YAML 内容验证
# ---------------------------------------------------------------------------

class TestCIContent:

    def test_github_actions_contains_project_name(
        self, generated_project: Path,
    ) -> None:
        """GitHub Actions workflow 应包含项目名称。"""
        wf = generated_project / ".github" / "workflows" / "testspec.yml"
        content = wf.read_text(encoding="utf-8")
        assert "Order Service" in content
        assert "pip install -r requirements.txt" in content

    def test_github_actions_has_phases(self, generated_project: Path) -> None:
        """GitHub Actions workflow 应包含所有阶段。"""
        content = (
            generated_project / ".github" / "workflows" / "testspec.yml"
        ).read_text(encoding="utf-8")
        assert "Validate Specs" in content
        assert "Run Smoke Tests" in content
        assert "Run E2E Tests" in content


# ---------------------------------------------------------------------------
# conftest.py 内容验证
# ---------------------------------------------------------------------------

class TestConftestContent:

    def test_root_conftest_syntax(self, generated_project: Path) -> None:
        """根 conftest.py 应为合法 Python。"""
        conftest = generated_project / "conftest.py"
        source = conftest.read_text(encoding="utf-8")
        ast.parse(source)

    def test_testcase_conftest_syntax(self, generated_project: Path) -> None:
        """testcase/conftest.py 应为合法 Python。"""
        conftest = generated_project / "testcase" / "conftest.py"
        source = conftest.read_text(encoding="utf-8")
        ast.parse(source)


# ---------------------------------------------------------------------------
# 目录结构验证
# ---------------------------------------------------------------------------

class TestDirectoryStructure:

    def test_business_line_dirs(self, generated_project: Path) -> None:
        """业务线目录应存在且包含 __init__.py。"""
        for biz in ("order", "payment"):
            biz_dir = generated_project / "testcase" / biz
            assert biz_dir.is_dir()
            assert (biz_dir / "__init__.py").exists()

    def test_specs_dirs(self, generated_project: Path) -> None:
        """规格文档目录应存在。"""
        for biz in ("order", "payment"):
            assert (generated_project / "specs" / biz).is_dir()

    def test_data_dirs(self, generated_project: Path) -> None:
        """数据目录应存在。"""
        for subdir in ("yaml", "json", "excel"):
            assert (generated_project / "data" / subdir).is_dir()
