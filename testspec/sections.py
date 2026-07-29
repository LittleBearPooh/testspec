"""TestSpec Section Renderers — 可插拔的项目生成阶段。

将 ProjectGenerator 的 12 个渲染阶段拆分为 12 个独立的 SectionRenderer 类。
每个 section 负责渲染一组逻辑相关的文件，并声明自己管理的文件集合
（供 upgrader 使用）。

循环引用解决：sections.py 通过 ``TYPE_CHECKING`` 守卫引用 ProjectGenerator，
generator.py 在运行时 import sections.py，不会产生循环依赖。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from .context import ProjectContext
    from .generator import ProjectGenerator

from .catalogs import SKILL_FILES
from .ci_builders import (
    build_github_actions_yaml,
    build_gitlab_ci_yaml,
    build_requirements,
    build_gitignore,
    build_testspec_manifest,
)
from .constants import CISystem

__all__ = [
    "SectionRenderer",
    "BaseSectionRenderer",
    "ALL_SECTION_CLASSES",
    "default_renderers",
    "load_plugin_renderers",
    "VersionMarkerSection",
    "AIRulesSection",
    "SkillsSection",
    "ConfigSection",
    "UtilsSection",
    "ExecutionSection",
    "ScriptsSection",
    "SpecsSection",
    "MockSection",
    "CISection",
    "DockerSection",
    "ProjectFilesSection",
]


# ---------------------------------------------------------------------------
# Protocol 和基类
# ---------------------------------------------------------------------------

@runtime_checkable
class SectionRenderer(Protocol):
    """Section Renderer 协议。

    定义所有 section 必须实现的接口：
    - ``name``: 进度消息中显示的名称
    - ``render(ctx, generator)``: 渲染逻辑
    """
    name: str

    def render(self, ctx: ProjectContext, generator: ProjectGenerator) -> None:
        ...


class BaseSectionRenderer:
    """Section Renderer 基类。

    提供 ``managed_files()`` 类方法（供 upgrader 动态推导）和
    默认的 ``render()`` 实现（抛出 NotImplementedError）。
    """
    name: str = ""

    @classmethod
    def managed_files(cls) -> frozenset[str]:
        """返回此 section 管理的文件路径集合（相对路径，正斜杠）。

        由 upgrader 用于判断哪些文件可以安全覆盖。
        默认返回空集合（表示此 section 不管理任何文件，如 specs 是用户文件）。
        """
        return frozenset()

    def render(self, ctx: ProjectContext, generator: ProjectGenerator) -> None:
        """渲染此 section 的文件。子类必须重写。"""
        raise NotImplementedError(
            f"{self.__class__.__name__} 未实现 render() 方法"
        )


# ---------------------------------------------------------------------------
# 12 个具体 Section Renderer
# ---------------------------------------------------------------------------

class VersionMarkerSection(BaseSectionRenderer):
    """写入 testspec.json 版本标记。"""
    name = "生成版本标记"

    @classmethod
    def managed_files(cls) -> frozenset[str]:
        return frozenset({"testspec.json"})

    def render(self, ctx: ProjectContext, generator: ProjectGenerator) -> None:
        generator.write_file("项目文件", "testspec.json", build_testspec_manifest(ctx))


class AIRulesSection(BaseSectionRenderer):
    """渲染 AI 规则层（CLAUDE.md）。"""
    name = "生成 AI 规则层"

    @classmethod
    def managed_files(cls) -> frozenset[str]:
        return frozenset({"CLAUDE.md"})

    def render(self, ctx: ProjectContext, generator: ProjectGenerator) -> None:
        generator.render_template_file("AI规则层", "ai_rules/CLAUDE.md.tpl", "CLAUDE.md")


class SkillsSection(BaseSectionRenderer):
    """渲染技能层（.claude/commands/）。"""
    name = "生成技能层"

    @classmethod
    def managed_files(cls) -> frozenset[str]:
        return frozenset(
            f".claude/commands/{sf.name}.md" for sf in SKILL_FILES
        )

    def render(self, ctx: ProjectContext, generator: ProjectGenerator) -> None:
        for sf in SKILL_FILES:
            generator.render_template_file(
                "技能层", f"skills/{sf.template}", f".claude/commands/{sf.name}.md",
            )


class ConfigSection(BaseSectionRenderer):
    """渲染配置层。"""
    name = "生成配置层"

    @classmethod
    def managed_files(cls) -> frozenset[str]:
        # variables.yaml 可能被用户自定义，不纳入 managed
        return frozenset({"config/variable_loader.py"})

    def render(self, ctx: ProjectContext, generator: ProjectGenerator) -> None:
        generator.render_template_file("配置层", "config/variables.yaml.tpl", "variables.yaml")
        generator.render_template_file(
            "配置层", "config/variables_override.yaml.template.tpl",
            "variables_override.yaml.template",
        )
        generator.render_template_file(
            "配置层", "config_loader/variable_loader.py.tpl",
            "config/variable_loader.py",
        )


class UtilsSection(BaseSectionRenderer):
    """渲染工具层。"""
    name = "生成工具层"

    # 始终生成的 utils 文件
    _ALWAYS_UTILS = (
        "http_client", "logger", "data_reader", "data_factory",
        "contract_checker", "assertions", "poll_helper",
    )

    @classmethod
    def managed_files(cls) -> frozenset[str]:
        files = {f"utils/{name}.py" for name in cls._ALWAYS_UTILS}
        files.add("utils/db_client.py")  # 条件生成，但升级时始终检查
        return frozenset(files)

    def render(self, ctx: ProjectContext, generator: ProjectGenerator) -> None:
        for name in self._ALWAYS_UTILS:
            generator.render_template_file("工具层", f"utils/{name}.py.tpl", f"utils/{name}.py")
        if ctx["HAS_DB"]:
            generator.render_template_file("工具层", "utils/db_client.py.tpl", "utils/db_client.py")


class ExecutionSection(BaseSectionRenderer):
    """渲染执行层。"""
    name = "生成执行层"

    @classmethod
    def managed_files(cls) -> frozenset[str]:
        # run scripts 的文件名依赖项目名，由 _is_managed() 的模式匹配处理
        return frozenset({
            "conftest.py",
            "testcase/conftest.py",
            "pytest.ini",
        })

    def render(self, ctx: ProjectContext, generator: ProjectGenerator) -> None:
        generator.render_template_file(
            "执行层", "execution/run_tests.ps1.tpl",
            f"{ctx['RUN_SCRIPT_NAME']}.ps1",
        )
        generator.render_template_file(
            "执行层", "execution/run_tests.sh.tpl",
            f"{ctx['RUN_SCRIPT_NAME']}.sh",
        )
        generator.render_template_file("执行层", "pytest_config/pytest.ini.tpl", "pytest.ini")
        generator.render_template_file("执行层", "pytest_config/conftest_root.py.tpl", "conftest.py")
        generator.render_template_file(
            "执行层", "pytest_config/conftest_testcase.py.tpl",
            "testcase/conftest.py",
        )


class ScriptsSection(BaseSectionRenderer):
    """渲染合规自检与工具链脚本。"""
    name = "生成工具链脚本"

    _SCRIPT_NAMES = (
        "check_compliance", "validate_specs", "check_coverage",
        "generate_skeletons", "spec_diff", "detect_flaky",
        "generate_metrics", "import_openapi", "generate_clients",
        "mcp_server",
    )

    @classmethod
    def managed_files(cls) -> frozenset[str]:
        return frozenset(f"scripts/{name}.py" for name in cls._SCRIPT_NAMES)

    def render(self, ctx: ProjectContext, generator: ProjectGenerator) -> None:
        for name in self._SCRIPT_NAMES:
            section_label = "合规自检" if name == "check_compliance" else "工具链"
            generator.render_template_file(
                section_label, f"scripts/{name}.py.tpl", f"scripts/{name}.py",
            )


class SpecsSection(BaseSectionRenderer):
    """渲染规格文档。"""
    name = "生成规格文档"

    @classmethod
    def managed_files(cls) -> frozenset[str]:
        # specs 是用户文件，升级时不覆盖
        return frozenset()

    def render(self, ctx: ProjectContext, generator: ProjectGenerator) -> None:
        generator.render_template_file(
            "规格文档", "specs/spec-template.md.tpl", "specs/spec-template.md",
        )
        generator.render_template_file("规格文档", "specs/spec-example.md", "specs/spec-example.md")
        generator.render_template_file("规格文档", "specs/registry.yaml.tpl", "specs/registry.yaml")


class MockSection(BaseSectionRenderer):
    """渲染 Mock 服务相关文件。"""
    name = "生成 Mock 服务"

    @classmethod
    def managed_files(cls) -> frozenset[str]:
        return frozenset({"utils/mock_server.py"})

    def render(self, ctx: ProjectContext, generator: ProjectGenerator) -> None:
        generator.render_template_file("Mock服务", "mock/mock_server.py.tpl", "utils/mock_server.py")
        generator.copy_static_file(
            "Mock服务", "mock/mock_responses/payment.json", "mock_responses/payment.json",
        )


class CISection(BaseSectionRenderer):
    """渲染 CI/CD 配置。"""
    name = "生成 CI/CD 配置"

    @classmethod
    def managed_files(cls) -> frozenset[str]:
        return frozenset({
            "ci/testspec-ci.yaml",
            ".pre-commit-config.yaml",
            "schemas/README.md",
            ".github/workflows/testspec.yml",
            ".gitlab-ci.yml",
        })

    def render(self, ctx: ProjectContext, generator: ProjectGenerator) -> None:
        ci_system = ctx["CI_SYSTEM"]
        if ci_system == CISystem.GITHUB.value:
            generator.write_file(
                "CI/CD", ".github/workflows/testspec.yml",
                build_github_actions_yaml(ctx),
            )
        elif ci_system == CISystem.GITLAB.value:
            generator.write_file(
                "CI/CD", ".gitlab-ci.yml", build_gitlab_ci_yaml(ctx),
            )

        # 始终生成参考模板
        generator.render_template_file("CI/CD", "ci/testspec-ci.yaml.tpl", "ci/testspec-ci.yaml")
        generator.render_template_file(
            "CI/CD", "ci/pre-commit-config.yaml.tpl",
            ".pre-commit-config.yaml",
        )

        # schemas README
        generator.render_template_file("CI/CD", "schemas/README.md.tpl", "schemas/README.md")


class DockerSection(BaseSectionRenderer):
    """渲染 Docker 测试环境配置。"""
    name = "生成 Docker 配置"

    @classmethod
    def managed_files(cls) -> frozenset[str]:
        return frozenset({"docker-compose.test.yml"})

    def render(self, ctx: ProjectContext, generator: ProjectGenerator) -> None:
        # SQLite 无需 Docker compose
        if ctx["HAS_DB"] and not ctx["DB_SQLITE"]:
            generator.render_template_file(
                "Docker", "docker/docker-compose.test.yml.tpl",
                "docker-compose.test.yml",
            )


class ProjectFilesSection(BaseSectionRenderer):
    """写入动态生成的项目文件（requirements.txt、.gitignore、__init__.py、.gitkeep）。"""
    name = "生成项目文件"

    @classmethod
    def managed_files(cls) -> frozenset[str]:
        return frozenset({"requirements.txt", ".gitignore"})

    def render(self, ctx: ProjectContext, generator: ProjectGenerator) -> None:
        # requirements.txt 和 .gitignore
        generator.write_file("项目文件", "requirements.txt", build_requirements(ctx))
        generator.write_file("项目文件", ".gitignore", build_gitignore(ctx))

        # 各业务线的 __init__.py
        for biz in ctx["BUSINESS_LINES_RAW"]:
            generator.write_file("测试目录", f"testcase/{biz}/__init__.py", "")

        # .gitkeep 占位文件
        for subdir in (
            "logs", "reports",
            "data/yaml", "data/json", "data/excel",
            "schemas", "mock_responses",
        ):
            generator.write_file("项目文件", f"{subdir}/.gitkeep", "")


# ---------------------------------------------------------------------------
# 导出
# ---------------------------------------------------------------------------

ALL_SECTION_CLASSES: list[type[BaseSectionRenderer]] = [
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
]


def default_renderers() -> list[BaseSectionRenderer]:
    """创建默认的 section renderer 列表（12 个 section，按生成顺序排列）。"""
    return [cls() for cls in ALL_SECTION_CLASSES]


def load_plugin_renderers(group: str = "testspec.sections") -> list[BaseSectionRenderer]:
    """从 entry_points 加载额外的 Section Renderer 插件实例。

    供 CLI 的 ``--plugin`` 流程使用。
    等同于调用 ``testspec.plugins.load_plugin_renderers()``。

    Args:
        group: entry_points 分组名称

    Returns:
        实例化的插件 SectionRenderer 列表（可能为空）
    """
    from .plugins import load_plugin_renderers as _load_plugins
    return _load_plugins(group=group)
