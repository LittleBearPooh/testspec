"""testspec.validator 模块的单元测试。

覆盖 ProjectValidator 的各检查方法：文件结构、manifest、
业务线、Python 语法、requirements 格式和 JSON 校验。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from testspec.validator import (
    ProjectValidator,
    ValidationResult,
    CHECKS,
    _is_valid_pip_line,
    _VALID_PIP_LINE_PREFIXES,
    _EXCLUDED_DIR_NAMES,
    _is_excluded_dir,
)


# ---------------------------------------------------------------------------
# 辅助 fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def minimal_project(tmp_path: Path) -> Path:
    """创建一个包含所有必需文件的最小项目。"""
    # 必需文件
    (tmp_path / "testspec.json").write_text(
        json.dumps({
            "testspec_version": "1.2.0",
            "project_name": "test-project",
            "test_types": ["api"],
            "language": "python",
            "framework": "pytest",
            "database": "none",
        }),
        encoding="utf-8",
    )
    (tmp_path / "requirements.txt").write_text("pytest>=7.4\n", encoding="utf-8")
    (tmp_path / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    (tmp_path / "conftest.py").write_text("# root conftest\n", encoding="utf-8")
    (tmp_path / "variables.yaml").write_text("key: value\n", encoding="utf-8")
    (tmp_path / ".gitignore").write_text("__pycache__/\n", encoding="utf-8")
    # testcase/conftest.py
    testcase = tmp_path / "testcase"
    testcase.mkdir()
    (testcase / "conftest.py").write_text("# testcase conftest\n", encoding="utf-8")
    return tmp_path


# ---------------------------------------------------------------------------
# ValidationResult
# ---------------------------------------------------------------------------

class TestValidationResult:
    """ValidationResult NamedTuple 结构。"""

    def test_fields(self) -> None:
        r = ValidationResult("ok", "structure", "test.py", "exists")
        assert r.status == "ok"
        assert r.category == "structure"
        assert r.path == "test.py"
        assert r.message == "exists"


# ---------------------------------------------------------------------------
# 文件结构检查
# ---------------------------------------------------------------------------

class TestFileStructureCheck:
    """_check_file_structure 方法。"""

    def test_all_required_files_present(self, minimal_project: Path) -> None:
        validator = ProjectValidator(minimal_project)
        results = validator.validate()
        structure_results = [r for r in results if r.category == "structure"]
        errors = [r for r in structure_results if r.status == "error"]
        assert len(errors) == 0, f"不应有 error: {errors}"

    def test_missing_required_file(self, tmp_path: Path) -> None:
        """缺少必需文件应返回 error。"""
        # 空目录
        validator = ProjectValidator(tmp_path)
        results = validator.validate()
        errors = [r for r in results if r.status == "error" and r.category == "structure"]
        assert len(errors) > 0

    def test_missing_optional_file_is_warning(self, minimal_project: Path) -> None:
        """缺少可选文件应返回 warning。"""
        validator = ProjectValidator(minimal_project)
        results = validator.validate()
        warnings = [r for r in results if r.status == "warning" and r.category == "structure"]
        # CLAUDE.md 是可选的
        claude_warnings = [r for r in warnings if "CLAUDE.md" in r.path]
        assert len(claude_warnings) == 1


# ---------------------------------------------------------------------------
# Manifest 检查
# ---------------------------------------------------------------------------

class TestManifestCheck:
    """_check_manifest 方法。"""

    def test_valid_manifest(self, minimal_project: Path) -> None:
        validator = ProjectValidator(minimal_project)
        results = validator.validate()
        manifest_results = [r for r in results if r.category == "manifest"]
        assert len(manifest_results) == 1
        assert manifest_results[0].status == "ok"
        assert "test-project" in manifest_results[0].message

    def test_missing_manifest(self, tmp_path: Path) -> None:
        validator = ProjectValidator(tmp_path)
        results = validator.validate()
        manifest_errors = [r for r in results if r.category == "manifest"]
        assert len(manifest_errors) == 1
        assert manifest_errors[0].status == "error"

    def test_malformed_json(self, tmp_path: Path) -> None:
        (tmp_path / "testspec.json").write_text("{invalid json", encoding="utf-8")
        validator = ProjectValidator(tmp_path)
        results = validator.validate()
        manifest_errors = [r for r in results if r.category == "manifest"]
        assert any(r.status == "error" for r in manifest_errors)


# ---------------------------------------------------------------------------
# 业务线检查
# ---------------------------------------------------------------------------

class TestBusinessLinesCheck:
    """_check_business_lines 方法。"""

    def test_biz_dirs_found(self, minimal_project: Path) -> None:
        biz = minimal_project / "testcase" / "order"
        biz.mkdir()
        validator = ProjectValidator(minimal_project)
        results = validator.validate()
        biz_results = [r for r in results if r.category == "business"]
        assert len(biz_results) == 1
        assert biz_results[0].status == "ok"
        assert "order" in biz_results[0].message

    def test_no_biz_dirs_warning(self, minimal_project: Path) -> None:
        validator = ProjectValidator(minimal_project)
        results = validator.validate()
        biz_results = [r for r in results if r.category == "business"]
        # testcase 目录存在但无业务线子目录（只有 conftest.py 文件）
        assert len(biz_results) == 1
        assert biz_results[0].status == "warning"


# ---------------------------------------------------------------------------
# Python 语法检查
# ---------------------------------------------------------------------------

class TestPythonSyntaxCheck:
    """_check_python_syntax 方法。"""

    def test_valid_py_files(self, minimal_project: Path) -> None:
        validator = ProjectValidator(minimal_project)
        results = validator.validate()
        syntax_results = [r for r in results if r.category == "syntax"]
        errors = [r for r in syntax_results if r.status == "error"]
        assert len(errors) == 0

    def test_invalid_py_file(self, minimal_project: Path) -> None:
        bad_py = minimal_project / "bad_syntax.py"
        bad_py.write_text("def foo(\n", encoding="utf-8")
        validator = ProjectValidator(minimal_project)
        results = validator.validate()
        syntax_errors = [r for r in results if r.category == "syntax" and r.status == "error"]
        assert len(syntax_errors) > 0

    def test_excludes_venv(self, minimal_project: Path) -> None:
        """虚拟环境中的 .py 文件不应被扫描。"""
        venv_dir = minimal_project / ".venv" / "lib"
        venv_dir.mkdir(parents=True)
        (venv_dir / "bad_syntax.py").write_text("def foo(\n", encoding="utf-8")
        validator = ProjectValidator(minimal_project)
        results = validator.validate()
        syntax_errors = [r for r in results if r.category == "syntax" and r.status == "error"]
        # 即使 .venv 中有语法错误的文件，也不应报错
        assert len(syntax_errors) == 0

    def test_excludes_egg_info(self, minimal_project: Path) -> None:
        """.egg-info 目录中的 .py 文件不应被扫描。"""
        egg_dir = minimal_project / "my_package.egg-info"
        egg_dir.mkdir()
        (egg_dir / "bad_syntax.py").write_text("def foo(\n", encoding="utf-8")
        validator = ProjectValidator(minimal_project)
        results = validator.validate()
        syntax_errors = [r for r in results if r.category == "syntax" and r.status == "error"]
        assert len(syntax_errors) == 0

    def test_excludes_egg_info_json(self, minimal_project: Path) -> None:
        """.egg-info 目录中的 .json 文件不应被扫描。"""
        egg_dir = minimal_project / "my_package.egg-info"
        egg_dir.mkdir()
        (egg_dir / "bad.json").write_text("{invalid", encoding="utf-8")
        validator = ProjectValidator(minimal_project)
        results = validator.validate()
        json_errors = [r for r in results if r.category == "json" and r.status == "error"]
        assert len(json_errors) == 0


# ---------------------------------------------------------------------------
# Requirements 格式检查 (H5 回归测试)
# ---------------------------------------------------------------------------

class TestRequirementsCheck:
    """_check_requirements_fmt 方法。"""

    def test_standard_deps_pass(self, minimal_project: Path) -> None:
        validator = ProjectValidator(minimal_project)
        results = validator.validate()
        req_results = [r for r in results if r.category == "requirements"]
        assert len(req_results) == 1
        assert req_results[0].status == "ok"

    def test_pip_options_pass(self, minimal_project: Path) -> None:
        """H5 回归测试：合法 pip 语法不应被误报。"""
        req_content = (
            "pytest>=7.4\n"
            "-r base-requirements.txt\n"
            "-e .\n"
            "--index-url https://pypi.org/simple\n"
            "https://example.com/package.tar.gz\n"
            "git+https://github.com/foo/bar.git\n"
        )
        (minimal_project / "requirements.txt").write_text(req_content, encoding="utf-8")
        validator = ProjectValidator(minimal_project)
        results = validator.validate()
        req_results = [r for r in results if r.category == "requirements"]
        assert len(req_results) == 1
        assert req_results[0].status == "ok", f"不应误报: {req_results[0].message}"

    def test_truly_invalid_line(self, minimal_project: Path) -> None:
        """真正无效的行应被标记。"""
        (minimal_project / "requirements.txt").write_text(
            "pytest>=7.4\n@@@invalid-package\n", encoding="utf-8",
        )
        validator = ProjectValidator(minimal_project)
        results = validator.validate()
        req_errors = [r for r in results if r.category == "requirements" and r.status == "error"]
        assert len(req_errors) > 0


class TestIsValidPipLine:
    """_is_valid_pip_line 辅助函数。"""

    def test_normal_package(self) -> None:
        assert _is_valid_pip_line("pytest>=7.4") is True

    def test_recursive_requirement(self) -> None:
        assert _is_valid_pip_line("-r base.txt") is True

    def test_editable_install(self) -> None:
        assert _is_valid_pip_line("-e .") is True

    def test_long_option(self) -> None:
        assert _is_valid_pip_line("--index-url https://pypi.org") is True

    def test_url_install(self) -> None:
        assert _is_valid_pip_line("https://example.com/pkg.tar.gz") is True

    def test_vcs_install(self) -> None:
        assert _is_valid_pip_line("git+https://github.com/foo/bar") is True

    def test_invalid_line(self) -> None:
        assert _is_valid_pip_line("@@@invalid") is False


# ---------------------------------------------------------------------------
# JSON 检查
# ---------------------------------------------------------------------------

class TestJsonCheck:
    """_check_json_files 方法。"""

    def test_valid_json(self, minimal_project: Path) -> None:
        (minimal_project / "data.json").write_text('{"key": "value"}', encoding="utf-8")
        validator = ProjectValidator(minimal_project)
        results = validator.validate()
        json_results = [r for r in results if r.category == "json"]
        assert all(r.status == "ok" for r in json_results)

    def test_invalid_json(self, minimal_project: Path) -> None:
        (minimal_project / "bad.json").write_text("{invalid", encoding="utf-8")
        validator = ProjectValidator(minimal_project)
        results = validator.validate()
        json_errors = [r for r in results if r.category == "json" and r.status == "error"]
        assert len(json_errors) > 0


# ---------------------------------------------------------------------------
# Counts
# ---------------------------------------------------------------------------

class TestCounts:
    """counts 属性。"""

    def test_counts_sum(self, minimal_project: Path) -> None:
        validator = ProjectValidator(minimal_project)
        validator.validate()
        passed, warnings, errors = validator.counts
        total = passed + warnings + errors
        assert total > 0
        assert total == len(validator._results)


# ---------------------------------------------------------------------------
# _is_excluded_dir 辅助函数
# ---------------------------------------------------------------------------

class TestIsExcludedDir:
    """_is_excluded_dir 辅助函数。"""

    def test_exact_match(self) -> None:
        assert _is_excluded_dir(".venv") is True
        assert _is_excluded_dir("__pycache__") is True
        assert _is_excluded_dir(".git") is True

    def test_egg_info_suffix(self) -> None:
        assert _is_excluded_dir("my_package.egg-info") is True
        assert _is_excluded_dir("testspec.egg-info") is True

    def test_non_excluded(self) -> None:
        assert _is_excluded_dir("src") is False
        assert _is_excluded_dir("testspec") is False
        assert _is_excluded_dir("egg-info") is False  # 不以 .egg-info 结尾
