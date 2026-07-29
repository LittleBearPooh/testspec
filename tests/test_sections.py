"""testspec.sections 模块测试。

测试 SectionRenderer Protocol、BaseSectionRenderer、12 个具体 Section 类、
以及 default_renderers() 工厂函数。
"""

from __future__ import annotations

from testspec.sections import (
    SectionRenderer,
    BaseSectionRenderer,
    ALL_SECTION_CLASSES,
    default_renderers,
    VersionMarkerSection,
    AIRulesSection,
    SkillsSection,
    ConfigSection,
    UtilsSection,
    ExecutionSection,
    ScriptsSection,
    SpecsSection,
    MockSection,
    CISection,
    DockerSection,
    ProjectFilesSection,
)
from testspec.catalogs import SKILL_FILES
from testspec.upgrader import MANAGED_FILES


# ---------------------------------------------------------------------------
# Protocol 合规性
# ---------------------------------------------------------------------------

class TestProtocolCompliance:
    """所有 Section 类必须满足 SectionRenderer Protocol。"""

    def test_all_sections_satisfy_protocol(self) -> None:
        for cls in ALL_SECTION_CLASSES:
            instance = cls()
            assert isinstance(instance, SectionRenderer), (
                f"{cls.__name__} 不满足 SectionRenderer Protocol"
            )

    def test_all_sections_have_non_empty_name(self) -> None:
        for cls in ALL_SECTION_CLASSES:
            assert cls.name, f"{cls.__name__} 的 name 属性为空"

    def test_base_section_render_raises_not_implemented(self) -> None:
        base = BaseSectionRenderer()
        try:
            base.render(None, None)  # type: ignore
            assert False, "应抛出 NotImplementedError"
        except NotImplementedError:
            pass


# ---------------------------------------------------------------------------
# managed_files 正确性
# ---------------------------------------------------------------------------

class TestManagedFiles:
    """各 Section 的 managed_files() 返回值验证。"""

    def test_managed_files_returns_frozenset(self) -> None:
        for cls in ALL_SECTION_CLASSES:
            result = cls.managed_files()
            assert isinstance(result, frozenset), (
                f"{cls.__name__}.managed_files() 应返回 frozenset"
            )

    def test_version_marker_manages_testspec_json(self) -> None:
        assert "testspec.json" in VersionMarkerSection.managed_files()

    def test_ai_rules_manages_claude_md(self) -> None:
        assert "CLAUDE.md" in AIRulesSection.managed_files()

    def test_skills_section_covers_all_skill_files(self) -> None:
        managed = SkillsSection.managed_files()
        for sf in SKILL_FILES:
            path = f".claude/commands/{sf.name}.md"
            assert path in managed, f"SkillsSection 缺少 {path}"

    def test_utils_section_includes_core_utils(self) -> None:
        managed = UtilsSection.managed_files()
        assert "utils/http_client.py" in managed
        assert "utils/logger.py" in managed
        assert "utils/data_reader.py" in managed
        assert "utils/db_client.py" in managed

    def test_scripts_section_covers_all_scripts(self) -> None:
        managed = ScriptsSection.managed_files()
        assert "scripts/check_compliance.py" in managed
        assert "scripts/validate_specs.py" in managed
        assert "scripts/mcp_server.py" in managed

    def test_specs_section_has_no_managed_files(self) -> None:
        """Specs 是用户文件，升级时不应覆盖。"""
        assert len(SpecsSection.managed_files()) == 0

    def test_ci_section_includes_both_ci_systems(self) -> None:
        managed = CISection.managed_files()
        assert ".github/workflows/testspec.yml" in managed
        assert ".gitlab-ci.yml" in managed

    def test_combined_managed_files_covers_upgrader_set(self) -> None:
        """所有 Section 的 managed_files 并集应覆盖 MANAGED_FILES。"""
        derived: set[str] = set()
        for cls in ALL_SECTION_CLASSES:
            derived.update(cls.managed_files())
        # MANAGED_FILES 中的每个文件都应在 derived 中
        for f in MANAGED_FILES:
            assert f in derived, f"MANAGED_FILES 中的 {f} 未被任何 Section 覆盖"


# ---------------------------------------------------------------------------
# default_renderers 工厂函数
# ---------------------------------------------------------------------------

class TestDefaultRenderers:
    """default_renderers() 和 ALL_SECTION_CLASSES 验证。"""

    def test_all_section_classes_count(self) -> None:
        assert len(ALL_SECTION_CLASSES) == 12

    def test_default_renderers_returns_twelve(self) -> None:
        renderers = default_renderers()
        assert len(renderers) == 12

    def test_all_renderers_implement_protocol(self) -> None:
        for r in default_renderers():
            assert isinstance(r, SectionRenderer)

    def test_section_names_include_ai(self) -> None:
        """进度消息需要包含 'AI' 以供 TestProgressCallback 检查。"""
        names = [r.name for r in default_renderers()]
        assert any("AI" in n for n in names)

    def test_section_order_preserved(self) -> None:
        """Section 顺序应与 ALL_SECTION_CLASSES 一致。"""
        renderers = default_renderers()
        for i, cls in enumerate(ALL_SECTION_CLASSES):
            assert type(renderers[i]) is cls

    def test_renderers_are_independent_instances(self) -> None:
        """每次调用 default_renderers() 应返回新实例。"""
        r1 = default_renderers()
        r2 = default_renderers()
        assert r1 is not r2
        assert r1[0] is not r2[0]


# ---------------------------------------------------------------------------
# 具体 Section 类测试
# ---------------------------------------------------------------------------

class TestConcreteSections:
    """各个 Section 类的属性验证。"""

    def test_version_marker_name(self) -> None:
        assert VersionMarkerSection.name == "生成版本标记"

    def test_docker_section_name(self) -> None:
        assert DockerSection.name == "生成 Docker 配置"

    def test_project_files_section_name(self) -> None:
        assert ProjectFilesSection.name == "生成项目文件"

    def test_mock_section_managed(self) -> None:
        assert "utils/mock_server.py" in MockSection.managed_files()

    def test_execution_section_managed(self) -> None:
        managed = ExecutionSection.managed_files()
        assert "conftest.py" in managed
        assert "testcase/conftest.py" in managed
        assert "pytest.ini" in managed

    def test_config_section_managed(self) -> None:
        managed = ConfigSection.managed_files()
        assert "config/variable_loader.py" in managed

    def test_docker_section_managed(self) -> None:
        assert "docker-compose.test.yml" in DockerSection.managed_files()

    def test_project_files_managed(self) -> None:
        managed = ProjectFilesSection.managed_files()
        assert "requirements.txt" in managed
        assert ".gitignore" in managed


# ---------------------------------------------------------------------------
# Section render() 单元测试
# ---------------------------------------------------------------------------

class TestSectionRender:
    """MockSection / ProjectFilesSection render() 行为验证。"""

    def test_mock_section_render(
        self, base_ctx, templates_dir,
    ) -> None:
        """MockSection.render() 应通过公共 API 生成 mock_server.py 和 payment.json。"""
        import tempfile, shutil
        gen = __import__("testspec.generator", fromlist=["ProjectGenerator"]).ProjectGenerator(
            base_ctx, templates_dir,
        )
        gen.temp_dir = __import__("pathlib").Path(tempfile.mkdtemp(prefix="testspec_test_"))
        try:
            MockSection().render(base_ctx, gen)
            sections = [s for s, _ in gen.generated]
            # 归一化路径分隔符（Windows 使用反斜杠）
            paths = [p.replace("\\", "/") for _, p in gen.generated]
            assert "Mock服务" in sections
            assert "utils/mock_server.py" in paths
            assert "mock_responses/payment.json" in paths
            assert (gen.temp_dir / "utils" / "mock_server.py").exists()
            assert (gen.temp_dir / "mock_responses" / "payment.json").exists()
        finally:
            shutil.rmtree(gen.temp_dir, ignore_errors=True)

    def test_project_files_section_render(
        self, base_ctx, templates_dir,
    ) -> None:
        """ProjectFilesSection.render() 应生成 requirements.txt、.gitignore、__init__.py、.gitkeep。"""
        import tempfile, shutil
        gen = __import__("testspec.generator", fromlist=["ProjectGenerator"]).ProjectGenerator(
            base_ctx, templates_dir,
        )
        gen.temp_dir = __import__("pathlib").Path(tempfile.mkdtemp(prefix="testspec_test_"))
        try:
            # 先创建目录骨架（ProjectFilesSection 依赖目录已存在）
            gen._create_directory_structure()
            ProjectFilesSection().render(base_ctx, gen)
            # 归一化路径分隔符（Windows 使用反斜杠）
            paths = [p.replace("\\", "/") for _, p in gen.generated]
            assert "requirements.txt" in paths
            assert ".gitignore" in paths
            # 业务线 __init__.py
            for biz in base_ctx["BUSINESS_LINES_RAW"]:
                assert f"testcase/{biz}/__init__.py" in paths
            # .gitkeep 占位文件
            assert "logs/.gitkeep" in paths
            assert "data/yaml/.gitkeep" in paths
            # 验证文件内容
            assert (gen.temp_dir / "requirements.txt").exists()
            req_content = (gen.temp_dir / "requirements.txt").read_text(encoding="utf-8")
            assert "pytest" in req_content
        finally:
            shutil.rmtree(gen.temp_dir, ignore_errors=True)
