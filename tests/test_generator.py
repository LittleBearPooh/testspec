"""TestSpec 项目生成器测试。"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

import pytest

from testspec.generator import (
    ProjectGenerator,
    build_requirements,
    build_gitignore,
    build_github_actions_yaml,
    build_gitlab_ci_yaml,
    build_testspec_manifest,
    generate_project,
    print_results,
)
from testspec.constants import (
    CI_PYTHON_VERSION,
    CI_COVERAGE_THRESHOLD,
    CI_FLAKY_THRESHOLD,
    CI_TEST_RERUNS,
    CI_RERUNS_DELAY,
)
from testspec.context import build_context_from_wizard


# ---------------------------------------------------------------------------
# Fixtures（特有于 generator 测试的变体 ctx）
# ---------------------------------------------------------------------------


@pytest.fixture
def no_allure_ctx(base_ctx: dict[str, Any]) -> dict[str, Any]:
    return {**base_ctx, "HAS_ALLURE": False, "REPORT_TOOL": "html", "HAS_HTML_REPORT": True}


@pytest.fixture
def mysql_ctx(base_ctx: dict[str, Any]) -> dict[str, Any]:
    return {
        **base_ctx,
        "DB_TYPE": "mysql", "DB_SQLSERVER": False, "DB_MYSQL": True,
        "DB_DEFAULT_PORT": "3306", "DB_DRIVER": "pymysql",
    }


@pytest.fixture
def no_db_ctx(base_ctx: dict[str, Any]) -> dict[str, Any]:
    return {
        **base_ctx,
        "HAS_DB": False, "DB_TYPE": "none", "DB_SQLSERVER": False,
        "DB_DEFAULT_PORT": "", "DB_DRIVER": "",
    }


@pytest.fixture
def gitlab_ctx(base_ctx: dict[str, Any]) -> dict[str, Any]:
    return {
        **base_ctx,
        "CI_SYSTEM": "gitlab", "CI_GITHUB": False, "CI_GITLAB": True,
    }


# ---------------------------------------------------------------------------
# build_requirements 测试
# ---------------------------------------------------------------------------

class TestBuildRequirements:

    def test_core_deps_always_present(self, base_ctx: dict[str, Any]) -> None:
        txt = build_requirements(base_ctx)
        assert "pytest>=7.4" in txt
        assert "pytest-xdist>=3.5" in txt
        assert "PyYAML>=6.0" in txt
        assert "faker>=19.0.0" in txt

    def test_allure_dep_included(self, base_ctx: dict[str, Any]) -> None:
        txt = build_requirements(base_ctx)
        assert "allure-pytest" in txt

    def test_allure_dep_absent_when_html_only(self, no_allure_ctx: dict[str, Any]) -> None:
        txt = build_requirements(no_allure_ctx)
        assert "allure-pytest" not in txt
        assert "pytest-html" in txt

    def test_db_deps_sqlserver(self, base_ctx: dict[str, Any]) -> None:
        txt = build_requirements(base_ctx)
        assert "pymssql" in txt

    def test_db_deps_mysql(self, mysql_ctx: dict[str, Any]) -> None:
        txt = build_requirements(mysql_ctx)
        assert "PyMySQL" in txt

    def test_no_db_deps(self, no_db_ctx: dict[str, Any]) -> None:
        txt = build_requirements(no_db_ctx)
        assert "pymssql" not in txt
        assert "PyMySQL" not in txt
        assert "psycopg2" not in txt

    def test_http_deps_included(self, base_ctx: dict[str, Any]) -> None:
        txt = build_requirements(base_ctx)
        assert "requests>=2.31" in txt

    def test_unknown_db_emits_warning(self, base_ctx: dict[str, Any]) -> None:
        ctx = {**base_ctx, "HAS_DB": True, "DB_TYPE": "oracle"}
        with pytest.warns(UserWarning, match="未知数据库类型"):
            build_requirements(ctx)

    def test_ends_with_newline(self, base_ctx: dict[str, Any]) -> None:
        assert build_requirements(base_ctx).endswith("\n")


# ---------------------------------------------------------------------------
# build_gitignore 测试
# ---------------------------------------------------------------------------

class TestBuildGitignore:

    def test_python_section(self, base_ctx: dict[str, Any]) -> None:
        txt = build_gitignore(base_ctx)
        assert "__pycache__/" in txt
        assert "*.py[cod]" in txt

    def test_allure_entry_when_enabled(self, base_ctx: dict[str, Any]) -> None:
        assert ".allure/" in build_gitignore(base_ctx)

    def test_allure_entry_absent_when_disabled(self, no_allure_ctx: dict[str, Any]) -> None:
        assert ".allure/" not in build_gitignore(no_allure_ctx)

    def test_sqlite_entries(self, base_ctx: dict[str, Any]) -> None:
        ctx = {**base_ctx, "DB_TYPE": "sqlite"}
        txt = build_gitignore(ctx)
        assert "*.db" in txt
        assert "*.sqlite3" in txt

    def test_sensitive_config_gitignored(self, base_ctx: dict[str, Any]) -> None:
        txt = build_gitignore(base_ctx)
        assert "variables_override.yaml" in txt
        assert ".env" in txt

    def test_ends_with_newline(self, base_ctx: dict[str, Any]) -> None:
        assert build_gitignore(base_ctx).endswith("\n")


# ---------------------------------------------------------------------------
# build_github_actions_yaml 测试
# ---------------------------------------------------------------------------

class TestBuildGithubActionsYaml:

    def test_project_name_in_header(self, base_ctx: dict[str, Any]) -> None:
        yaml = build_github_actions_yaml(base_ctx)
        assert "Order Service" in yaml

    def test_python_version_uses_constant(self, base_ctx: dict[str, Any]) -> None:
        yaml = build_github_actions_yaml(base_ctx)
        # yaml_dump 使用双引号包裹 QuotedStr 值
        assert f'python-version: "{CI_PYTHON_VERSION}"' in yaml

    def test_coverage_threshold_uses_constant(self, base_ctx: dict[str, Any]) -> None:
        yaml = build_github_actions_yaml(base_ctx)
        assert f"--threshold {CI_COVERAGE_THRESHOLD}" in yaml

    def test_flaky_threshold_uses_constant(self, base_ctx: dict[str, Any]) -> None:
        yaml = build_github_actions_yaml(base_ctx)
        assert f"--threshold {CI_FLAKY_THRESHOLD}" in yaml

    def test_rerun_params_uses_constants(self, base_ctx: dict[str, Any]) -> None:
        yaml = build_github_actions_yaml(base_ctx)
        assert f"--reruns {CI_TEST_RERUNS} --reruns-delay {CI_RERUNS_DELAY}" in yaml

    def test_allure_step_present(self, base_ctx: dict[str, Any]) -> None:
        yaml = build_github_actions_yaml(base_ctx)
        assert "allure-report-action" in yaml

    def test_allure_step_absent(self, no_allure_ctx: dict[str, Any]) -> None:
        yaml = build_github_actions_yaml(no_allure_ctx)
        assert "allure-report-action" not in yaml

    def test_e2e_alluredir_when_allure(self, base_ctx: dict[str, Any]) -> None:
        yaml = build_github_actions_yaml(base_ctx)
        assert "--alluredir=reports/allure-results" in yaml


# ---------------------------------------------------------------------------
# build_gitlab_ci_yaml 测试
# ---------------------------------------------------------------------------

class TestBuildGitlabCiYaml:

    def test_project_name_in_header(self, base_ctx: dict[str, Any]) -> None:
        yaml = build_gitlab_ci_yaml(base_ctx)
        assert "Order Service" in yaml

    def test_python_version_uses_constant(self, base_ctx: dict[str, Any]) -> None:
        yaml = build_gitlab_ci_yaml(base_ctx)
        assert f"image: python:{CI_PYTHON_VERSION}" in yaml

    def test_coverage_threshold(self, base_ctx: dict[str, Any]) -> None:
        yaml = build_gitlab_ci_yaml(base_ctx)
        assert f"--threshold {CI_COVERAGE_THRESHOLD}" in yaml

    def test_allure_job_present(self, base_ctx: dict[str, Any]) -> None:
        yaml = build_gitlab_ci_yaml(base_ctx)
        assert "allure generate" in yaml

    def test_allure_job_absent(self, no_allure_ctx: dict[str, Any]) -> None:
        yaml = build_gitlab_ci_yaml(no_allure_ctx)
        assert "allure generate" not in yaml


# ---------------------------------------------------------------------------
# build_testspec_manifest 测试
# ---------------------------------------------------------------------------

class TestBuildTestspecManifest:

    def test_valid_json(self, base_ctx: dict[str, Any]) -> None:
        manifest = build_testspec_manifest(base_ctx)
        data = json.loads(manifest)
        assert data["project_name"] == "order-service"
        from testspec.constants import VERSION
        assert data["testspec_version"] == VERSION

    def test_contains_all_fields(self, base_ctx: dict[str, Any]) -> None:
        data = json.loads(build_testspec_manifest(base_ctx))
        assert "test_types" in data
        assert "language" in data
        assert "framework" in data
        assert "database" in data
        assert "ci_system" in data

    def test_ends_with_newline(self, base_ctx: dict[str, Any]) -> None:
        assert build_testspec_manifest(base_ctx).endswith("\n")


# ---------------------------------------------------------------------------
# ProjectGenerator 集成测试
# ---------------------------------------------------------------------------

class TestProjectGenerator:

    def test_generate_creates_output_dir(
        self, base_ctx: dict[str, Any], templates_dir: Path, tmp_path: Path,
    ) -> None:
        output = tmp_path / "output"
        ctx = {**base_ctx, "OUTPUT_DIR": str(output)}
        result = ProjectGenerator(ctx, templates_dir).generate()
        assert output.is_dir()
        assert len(result) > 0

    def test_generate_returns_section_filepath_tuples(
        self, base_ctx: dict[str, Any], templates_dir: Path, tmp_path: Path,
    ) -> None:
        ctx = {**base_ctx, "OUTPUT_DIR": str(tmp_path / "output")}
        result = ProjectGenerator(ctx, templates_dir).generate()
        for section, filepath in result:
            assert isinstance(section, str)
            assert isinstance(filepath, str)

    def test_context_manager_does_not_leak_temp_dir(
        self, base_ctx: dict[str, Any], templates_dir: Path, tmp_path: Path,
    ) -> None:
        ctx = {**base_ctx, "OUTPUT_DIR": str(tmp_path / "output")}
        before = set(Path(tempfile.gettempdir()).glob("testspec_*"))
        with ProjectGenerator(ctx, templates_dir) as gen:
            gen.generate()
        after = set(Path(tempfile.gettempdir()).glob("testspec_*"))
        leaked = after - before
        assert not leaked, f"Leaked temp dirs: {leaked}"

    def test_generate_without_context_manager(
        self, base_ctx: dict[str, Any], templates_dir: Path, tmp_path: Path,
    ) -> None:
        """不使用 with 语句也能正常工作。"""
        ctx = {**base_ctx, "OUTPUT_DIR": str(tmp_path / "output")}
        gen = ProjectGenerator(ctx, templates_dir)
        result = gen.generate()
        assert len(result) > 0


# ---------------------------------------------------------------------------
# generate_project 集成测试
# ---------------------------------------------------------------------------

class TestGenerateProject:

    def test_returns_file_list(
        self, base_ctx: dict[str, Any], templates_dir: Path, tmp_path: Path,
    ) -> None:
        ctx = {**base_ctx, "OUTPUT_DIR": str(tmp_path / "proj")}
        result = generate_project(ctx, templates_dir)
        assert len(result) > 10

    def test_creates_requirements_txt(
        self, base_ctx: dict[str, Any], templates_dir: Path, tmp_path: Path,
    ) -> None:
        output = tmp_path / "proj"
        ctx = {**base_ctx, "OUTPUT_DIR": str(output)}
        generate_project(ctx, templates_dir)
        assert (output / "requirements.txt").exists()

    def test_creates_gitignore(
        self, base_ctx: dict[str, Any], templates_dir: Path, tmp_path: Path,
    ) -> None:
        output = tmp_path / "proj"
        ctx = {**base_ctx, "OUTPUT_DIR": str(output)}
        generate_project(ctx, templates_dir)
        assert (output / ".gitignore").exists()

    def test_creates_github_ci(
        self, base_ctx: dict[str, Any], templates_dir: Path, tmp_path: Path,
    ) -> None:
        output = tmp_path / "proj"
        ctx = {**base_ctx, "OUTPUT_DIR": str(output)}
        generate_project(ctx, templates_dir)
        assert (output / ".github" / "workflows" / "testspec.yml").exists()

    def test_creates_gitlab_ci(
        self, gitlab_ctx: dict[str, Any], templates_dir: Path, tmp_path: Path,
    ) -> None:
        output = tmp_path / "proj"
        ctx = {**gitlab_ctx, "OUTPUT_DIR": str(output)}
        generate_project(ctx, templates_dir)
        assert (output / ".gitlab-ci.yml").exists()

    def test_creates_testspec_json(
        self, base_ctx: dict[str, Any], templates_dir: Path, tmp_path: Path,
    ) -> None:
        output = tmp_path / "proj"
        ctx = {**base_ctx, "OUTPUT_DIR": str(output)}
        generate_project(ctx, templates_dir)
        assert (output / "testspec.json").exists()
        data = json.loads((output / "testspec.json").read_text(encoding="utf-8"))
        assert data["project_name"] == "order-service"

    def test_creates_business_line_dirs(
        self, base_ctx: dict[str, Any], templates_dir: Path, tmp_path: Path,
    ) -> None:
        output = tmp_path / "proj"
        ctx = {**base_ctx, "OUTPUT_DIR": str(output)}
        generate_project(ctx, templates_dir)
        assert (output / "testcase" / "order").is_dir()
        assert (output / "testcase" / "payment").is_dir()

    def test_no_db_skips_docker_compose(
        self, no_db_ctx: dict[str, Any], templates_dir: Path, tmp_path: Path,
    ) -> None:
        output = tmp_path / "proj"
        ctx = {**no_db_ctx, "OUTPUT_DIR": str(output)}
        generate_project(ctx, templates_dir)
        assert not (output / "docker-compose.test.yml").exists()

    def test_dry_run_no_output_dir(
        self, base_ctx: dict[str, Any], templates_dir: Path, tmp_path: Path,
    ) -> None:
        """dry-run 模式不应创建输出目录。"""
        output = tmp_path / "proj"
        ctx = {**base_ctx, "OUTPUT_DIR": str(output)}
        result = ProjectGenerator(ctx, templates_dir, dry_run=True).generate()
        assert not output.exists()
        assert len(result) > 0

    def test_dry_run_returns_file_list(
        self, base_ctx: dict[str, Any], templates_dir: Path, tmp_path: Path,
    ) -> None:
        """dry-run 模式仍应返回完整的文件列表。"""
        output = tmp_path / "proj"
        ctx = {**base_ctx, "OUTPUT_DIR": str(output)}
        result = ProjectGenerator(ctx, templates_dir, dry_run=True).generate()
        sections = {s for s, _ in result}
        assert "项目文件" in sections


# ---------------------------------------------------------------------------
# print_results 测试
# ---------------------------------------------------------------------------

class TestPrintResults:

    def test_github_ci_output(self, base_ctx: dict[str, Any], capsys: Any) -> None:
        generated = [("AI规则层", "CLAUDE.md"), ("项目文件", "requirements.txt")]
        print_results(base_ctx, generated)
        captured = capsys.readouterr().out
        assert "生成完成" in captured
        assert "testspec.yml" in captured
        assert "order-service" in captured

    def test_gitlab_ci_output(self, gitlab_ctx: dict[str, Any], capsys: Any) -> None:
        generated = [("项目文件", ".gitignore")]
        print_results(gitlab_ctx, generated)
        captured = capsys.readouterr().out
        assert ".gitlab-ci.yml" in captured

    def test_no_ci_output(self, base_ctx: dict[str, Any], capsys: Any) -> None:
        ctx = {**base_ctx, "CI_SYSTEM": "none"}
        generated = [("项目文件", "requirements.txt")]
        print_results(ctx, generated)
        captured = capsys.readouterr().out
        assert "run_order_service_tests" in captured

    def test_db_section_shown(self, base_ctx: dict[str, Any], capsys: Any) -> None:
        generated = [("项目文件", "requirements.txt")]
        print_results(base_ctx, generated)
        captured = capsys.readouterr().out
        assert "variables_override" in captured

    def test_no_db_section_hidden(self, no_db_ctx: dict[str, Any], capsys: Any) -> None:
        generated = [("项目文件", "requirements.txt")]
        print_results(no_db_ctx, generated)
        captured = capsys.readouterr().out
        assert "variables_override" not in captured


# ---------------------------------------------------------------------------
# Dry-run 模块级函数测试
# ---------------------------------------------------------------------------

class TestDryRunModule:

    def test_dry_run_no_output(
        self, base_ctx: dict[str, Any], templates_dir: Path, tmp_path: Path,
    ) -> None:
        """模块级 generate_project(dry_run=True) 不应创建输出目录。"""
        output = tmp_path / "proj"
        ctx = {**base_ctx, "OUTPUT_DIR": str(output)}
        result = generate_project(ctx, templates_dir, dry_run=True)
        assert not output.exists()
        assert len(result) > 10

    def test_dry_run_cleans_temp_dir(
        self, base_ctx: dict[str, Any], templates_dir: Path, tmp_path: Path,
    ) -> None:
        """dry-run 模式不应泄漏临时目录。"""
        output = tmp_path / "proj"
        ctx = {**base_ctx, "OUTPUT_DIR": str(output)}
        before = set(Path(tempfile.gettempdir()).glob("testspec_*"))
        generate_project(ctx, templates_dir, dry_run=True)
        after = set(Path(tempfile.gettempdir()).glob("testspec_*"))
        leaked = after - before
        assert not leaked, f"Leaked temp dirs: {leaked}"


# ---------------------------------------------------------------------------
# progress_callback 测试
# ---------------------------------------------------------------------------

class TestProgressCallback:

    def test_callback_receives_messages(
        self, base_ctx: dict[str, Any], templates_dir: Path, tmp_path: Path,
    ) -> None:
        """progress_callback 应在每个生成阶段被调用。"""
        messages: list[str] = []
        output = tmp_path / "proj"
        ctx = {**base_ctx, "OUTPUT_DIR": str(output)}
        generate_project(
            ctx, templates_dir, progress_callback=messages.append,
        )
        assert len(messages) > 5, f"应收到多个进度消息，实际: {len(messages)}"
        assert any("目录" in m for m in messages)
        assert any("AI" in m for m in messages)

    def test_no_callback_works(
        self, base_ctx: dict[str, Any], templates_dir: Path, tmp_path: Path,
    ) -> None:
        """不传 progress_callback 时应正常工作（不崩溃）。"""
        output = tmp_path / "proj"
        ctx = {**base_ctx, "OUTPUT_DIR": str(output)}
        result = generate_project(ctx, templates_dir)
        assert len(result) > 0

    def test_callback_dry_run(
        self, base_ctx: dict[str, Any], templates_dir: Path, tmp_path: Path,
    ) -> None:
        """dry-run 模式下 progress_callback 也应正常工作。"""
        messages: list[str] = []
        output = tmp_path / "proj"
        ctx = {**base_ctx, "OUTPUT_DIR": str(output)}
        generate_project(
            ctx, templates_dir, dry_run=True, progress_callback=messages.append,
        )
        assert len(messages) > 0


# ---------------------------------------------------------------------------
# _atomic_move 与错误恢复测试
# ---------------------------------------------------------------------------

class TestAtomicMove:
    """原子写入 staging/rollback 路径测试。"""

    def test_overwrite_existing_directory(
        self, base_ctx: dict[str, Any], templates_dir: Path, tmp_path: Path,
    ) -> None:
        """覆盖已有目录时，旧内容应被替换，不残留 staging。"""
        output = tmp_path / "proj"
        # 先创建旧目录和文件
        output.mkdir()
        (output / "old_file.txt").write_text("should be gone", encoding="utf-8")

        ctx = {**base_ctx, "OUTPUT_DIR": str(output)}
        generate_project(ctx, templates_dir)

        # 新文件应存在
        assert (output / "requirements.txt").exists()
        # 旧文件应被清除
        assert not (output / "old_file.txt").exists()
        # staging 目录应被清理
        staging = tmp_path / ".proj.staging"
        assert not staging.exists()

    def test_overwrite_preserves_on_failure(
        self, base_ctx: dict[str, Any], templates_dir: Path, tmp_path: Path,
    ) -> None:
        """当生成过程中发生异常时，临时目录应被清理。"""
        output = tmp_path / "proj"
        ctx = {**base_ctx, "OUTPUT_DIR": str(output)}

        # 记录生成前的临时目录
        before = set(Path(tempfile.gettempdir()).glob("testspec_*"))

        gen = ProjectGenerator(ctx, templates_dir)
        gen.temp_dir = Path(tempfile.mkdtemp(prefix="testspec_"))
        temp_path = gen.temp_dir

        # 模拟生成中途失败
        try:
            gen._create_directory_structure()
            raise RuntimeError("模拟生成失败")
        except RuntimeError:
            gen._cleanup()

        # 临时目录应被清理
        assert not temp_path.exists()

    def test_context_manager_cleanup_on_exception(
        self, base_ctx: dict[str, Any], templates_dir: Path, tmp_path: Path,
    ) -> None:
        """上下文管理器在异常时也应清理临时目录。"""
        output = tmp_path / "proj"
        ctx = {**base_ctx, "OUTPUT_DIR": str(output)}

        before = set(Path(tempfile.gettempdir()).glob("testspec_*"))

        try:
            with ProjectGenerator(ctx, templates_dir) as gen:
                temp_path = gen.temp_dir
                assert temp_path is not None
                raise ValueError("模拟错误")
        except ValueError:
            pass

        # 上下文管理器退出时应清理临时目录
        assert not temp_path.exists()

    def test_multiple_overwrites(
        self, base_ctx: dict[str, Any], templates_dir: Path, tmp_path: Path,
    ) -> None:
        """多次覆盖同一目录应每次都成功。"""
        output = tmp_path / "proj"
        ctx = {**base_ctx, "OUTPUT_DIR": str(output)}

        # 第一次生成
        generate_project(ctx, templates_dir)
        assert (output / "requirements.txt").exists()

        # 第二次覆盖
        generate_project(ctx, templates_dir)
        assert (output / "requirements.txt").exists()
        # staging 应被清理
        staging = tmp_path / ".proj.staging"
        assert not staging.exists()


from testspec.exceptions import GenerationError


class TestGenerationError:
    """GenerationError 捕获路径测试。"""

    def test_generation_error_is_caught_by_runtime_error(self) -> None:
        """GenerationError 继承 RuntimeError，旧代码 except RuntimeError 仍可捕获。"""
        with pytest.raises(RuntimeError):
            raise GenerationError("测试错误")

    def test_atomic_move_nonexistent_parent_raises(
        self, base_ctx: dict[str, Any], templates_dir: Path, tmp_path: Path,
    ) -> None:
        """当输出目录的父路径是一个文件（非目录）时，_atomic_move 应抛出 GenerationError。"""
        # 创建一个文件作为"父目录"，使其无法创建子目录
        fake_parent = tmp_path / "not_a_dir"
        fake_parent.write_text("I am a file", encoding="utf-8")
        output = fake_parent / "proj"

        ctx = {**base_ctx, "OUTPUT_DIR": str(output)}
        with pytest.raises((GenerationError, OSError)):
            gen = ProjectGenerator(ctx, templates_dir)
            gen.generate()


# ---------------------------------------------------------------------------
# copy_static_file 测试
# ---------------------------------------------------------------------------

class TestCopyStaticFile:
    """ProjectGenerator.copy_static_file() 单元测试。"""

    def test_copies_existing_file(
        self, base_ctx: dict[str, Any], tmp_path: Path,
    ) -> None:
        """源文件存在时应正确复制到临时目录。"""
        tpl_dir = tmp_path / "templates"
        tpl_dir.mkdir()
        src_file = tpl_dir / "data.json"
        src_file.write_text('{"key": "value"}', encoding="utf-8")

        gen = ProjectGenerator(base_ctx, tpl_dir)
        gen.temp_dir = Path(tempfile.mkdtemp(prefix="testspec_test_"))
        try:
            gen.copy_static_file("测试", "data.json", "output/data.json")
            result = gen.temp_dir / "output" / "data.json"
            assert result.exists()
            assert result.read_text(encoding="utf-8") == '{"key": "value"}'
            assert ("测试", "output/data.json") in gen.generated
        finally:
            import shutil
            shutil.rmtree(gen.temp_dir, ignore_errors=True)

    def test_missing_source_warns_and_skips(
        self, base_ctx: dict[str, Any], tmp_path: Path,
    ) -> None:
        """源文件不存在时应发出 warning 并跳过，不追加到 generated。"""
        tpl_dir = tmp_path / "templates"
        tpl_dir.mkdir()

        gen = ProjectGenerator(base_ctx, tpl_dir)
        gen.temp_dir = Path(tempfile.mkdtemp(prefix="testspec_test_"))
        try:
            gen.copy_static_file("测试", "nonexistent.json", "output/data.json")
            assert not (gen.temp_dir / "output" / "data.json").exists()
            assert ("测试", "output/data.json") not in gen.generated
        finally:
            import shutil
            shutil.rmtree(gen.temp_dir, ignore_errors=True)

    def test_creates_parent_directories(
        self, base_ctx: dict[str, Any], tmp_path: Path,
    ) -> None:
        """目标路径的父目录不存在时应自动创建。"""
        tpl_dir = tmp_path / "templates"
        tpl_dir.mkdir()
        (tpl_dir / "file.txt").write_text("content", encoding="utf-8")

        gen = ProjectGenerator(base_ctx, tpl_dir)
        gen.temp_dir = Path(tempfile.mkdtemp(prefix="testspec_test_"))
        try:
            gen.copy_static_file("测试", "file.txt", "deep/nested/dir/file.txt")
            assert (gen.temp_dir / "deep" / "nested" / "dir" / "file.txt").exists()
        finally:
            import shutil
            shutil.rmtree(gen.temp_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# 路径安全校验测试
# ---------------------------------------------------------------------------

class TestPathValidation:
    """render_template_file / copy_static_file 路径穿越防护。"""

    def test_render_template_file_rejects_path_traversal(
        self, base_ctx: dict[str, Any], tmp_path: Path,
    ) -> None:
        """render_template_file 应拒绝包含 .. 的 tpl_subpath。"""
        gen = ProjectGenerator(base_ctx, tmp_path)
        gen.temp_dir = Path(tempfile.mkdtemp(prefix="testspec_test_"))
        try:
            with pytest.raises(ValueError, match="路径段"):
                gen.render_template_file("测试", "../etc/passwd", "out.txt")
        finally:
            import shutil
            shutil.rmtree(gen.temp_dir, ignore_errors=True)

    def test_copy_static_file_rejects_path_traversal(
        self, base_ctx: dict[str, Any], tmp_path: Path,
    ) -> None:
        """copy_static_file 应拒绝包含 .. 的 src_subpath。"""
        gen = ProjectGenerator(base_ctx, tmp_path)
        gen.temp_dir = Path(tempfile.mkdtemp(prefix="testspec_test_"))
        try:
            with pytest.raises(ValueError, match="路径段"):
                gen.copy_static_file("测试", "../../sensitive.yaml", "out.yaml")
        finally:
            import shutil
            shutil.rmtree(gen.temp_dir, ignore_errors=True)

    def test_normal_subpath_is_allowed(
        self, base_ctx: dict[str, Any], tmp_path: Path,
    ) -> None:
        """正常子路径（不含 ..）应正常通过校验。"""
        tpl_dir = tmp_path / "templates"
        tpl_dir.mkdir()
        (tpl_dir / "safe.txt").write_text("ok", encoding="utf-8")

        gen = ProjectGenerator(base_ctx, tpl_dir)
        gen.temp_dir = Path(tempfile.mkdtemp(prefix="testspec_test_"))
        try:
            gen.copy_static_file("测试", "safe.txt", "out.txt")
            assert (gen.temp_dir / "out.txt").read_text(encoding="utf-8") == "ok"
        finally:
            import shutil
            shutil.rmtree(gen.temp_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Shell 脚本可执行权限测试
# ---------------------------------------------------------------------------


class TestShellScriptPermission:
    """生成的 .sh 脚本应具有可执行权限（POSIX 平台）。"""

    @pytest.mark.skipif(
        __import__("sys").platform == "win32",
        reason="Windows 不支持 POSIX execute bit",
    )
    def test_sh_script_has_executable_bit(
        self, base_ctx: dict[str, Any], templates_dir: Path, tmp_path: Path,
    ) -> None:
        """生成的 .sh 文件应具有 owner execute bit。"""
        import os
        output = tmp_path / "proj"
        ctx = {**base_ctx, "OUTPUT_DIR": str(output)}
        generate_project(ctx, templates_dir)
        run_sh = output / f"{base_ctx['RUN_SCRIPT_NAME']}.sh"
        assert run_sh.exists(), f"Expected {run_sh} to be generated"
        assert os.access(run_sh, os.X_OK), (
            f"{run_sh.name} should have execute permission"
        )

    def test_maybe_set_executable_on_sh_file(self, tmp_path: Path) -> None:
        """_maybe_set_executable 应对 .sh 文件设置权限（不抛异常）。"""
        sh_file = tmp_path / "test.sh"
        sh_file.write_text("#!/bin/bash\necho ok", encoding="utf-8")
        ProjectGenerator._maybe_set_executable(sh_file)
        # 在 Windows 上此检查无意义，但至少验证不抛异常

    def test_maybe_set_executable_ignores_non_sh(self, tmp_path: Path) -> None:
        """_maybe_set_executable 对非 .sh 文件不做任何操作。"""
        py_file = tmp_path / "test.py"
        py_file.write_text("print('ok')", encoding="utf-8")
        original_mode = py_file.stat().st_mode
        ProjectGenerator._maybe_set_executable(py_file)
        assert py_file.stat().st_mode == original_mode

