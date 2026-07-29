"""TestSpec 项目生成器。

负责目录创建、模板渲染、动态文件生成、原子写入和错误处理。

v1.1.0 重构：
  - 内容构建函数提取到 :mod:`testspec.ci_builders`
  - 渲染阶段拆分为 :mod:`testspec.sections` 中的 SectionRenderer 类
  - 新增 :class:`~testspec.hooks.HookRegistry` 生命周期事件机制
  - 所有原有公共 API 通过 re-export 保持向后兼容
"""

from __future__ import annotations

import logging
import os
import shutil
import sys
import tempfile
import warnings
from itertools import count
from pathlib import Path
from types import TracebackType
from typing import Callable

from .constants import SEPARATOR, CISystem
from .renderer import render_file
from .exceptions import GenerationError
from .context import ProjectContext

# Re-export：从 ci_builders 导入，保持向后兼容的 import 路径
from .ci_builders import (  # noqa: F401
    build_requirements,
    build_gitignore,
    build_github_actions_yaml,
    build_gitlab_ci_yaml,
    build_testspec_manifest,
)
from .hooks import HookRegistry
from .sections import BaseSectionRenderer, default_renderers

__all__ = [
    "ProjectGenerator",
    "generate_project",
    "print_results",
    "build_requirements",
    "build_gitignore",
    "build_github_actions_yaml",
    "build_gitlab_ci_yaml",
    "build_testspec_manifest",
]

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 路径安全校验
# ---------------------------------------------------------------------------

def _validate_subpath(subpath: str, param_name: str = "subpath") -> None:
    """验证子路径不包含路径穿越（``..`` 段）。

    防止通过 ``../`` 访问 templates_dir 之外的文件。

    Args:
        subpath: 待验证的相对路径
        param_name: 参数名称（用于错误消息）

    Raises:
        ValueError: 路径包含 ``..`` 段
    """
    normalized = subpath.replace("\\", "/")
    parts = normalized.split("/")
    if ".." in parts:
        raise ValueError(
            f"{param_name} 包含非法路径段 '..'：{subpath!r}。"
            f"不允许访问模板目录之外的文件。"
        )


# ---------------------------------------------------------------------------
# ProjectGenerator — 核心生成器类
# ---------------------------------------------------------------------------

class ProjectGenerator:
    """项目生成器，使用原子写入确保生成过程的完整性。

    先生成到临时目录，全部成功后再移动到最终位置。
    任何阶段的失败都会清理临时目录并抛出 RuntimeError。

    通过 ``section_renderers`` 参数可自定义生成阶段（默认 12 个 section）。
    通过 ``hook_registry`` 参数可注册生命周期事件回调。

    Usage::

        gen = ProjectGenerator(ctx, templates_dir)
        generated = gen.generate()

        # 使用 Hook 扩展
        hooks = HookRegistry()
        hooks.register("post_generate", my_callback)
        gen = ProjectGenerator(ctx, templates_dir, hook_registry=hooks)
    """

    def __init__(
        self,
        ctx: ProjectContext,
        templates_dir: Path,
        *,
        dry_run: bool = False,
        progress_callback: Callable[[str], None] | None = None,
        hook_registry: HookRegistry | None = None,
        section_renderers: list[BaseSectionRenderer] | None = None,
    ) -> None:
        self.ctx = ctx
        self.templates_dir = templates_dir
        self.dry_run = dry_run
        self._progress_callback = progress_callback
        self._hook_registry = hook_registry if hook_registry is not None else HookRegistry()
        self._renderers = section_renderers if section_renderers is not None else default_renderers()
        self.temp_dir: Path | None = None
        self.generated: list[tuple[str, str]] = []

    def __enter__(self) -> ProjectGenerator:
        if self.temp_dir is None:
            self.temp_dir = Path(tempfile.mkdtemp(prefix="testspec_"))
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self._cleanup()

    def generate(self) -> list[tuple[str, str]]:
        """执行完整的项目生成流程。

        流程：
        1. 触发 ``pre_generate`` Hook
        2. 创建目录骨架
        3. 依次执行每个 SectionRenderer（触发 ``post_section`` Hook）
        4. 原子移动到最终位置（触发 ``pre_atomic_move`` Hook，仅非 dry-run）
        5. 触发 ``post_generate`` Hook

        Returns:
            生成的文件列表 [(section, filepath), ...]

        Raises:
            RuntimeError: 生成过程中出现 IO/权限/编码错误
        """
        if self.temp_dir is None:
            self.temp_dir = Path(tempfile.mkdtemp(prefix="testspec_"))
        success = False
        try:
            self._hook_registry.fire("pre_generate", ctx=self.ctx)
            self._progress("创建目录结构")
            self._create_directory_structure()

            for renderer in self._renderers:
                self._progress(renderer.name)
                renderer.render(self.ctx, self)
                self._hook_registry.safe_fire(
                    "post_section", section=renderer.name, ctx=self.ctx,
                )

            if not self.dry_run:
                self._progress("写入最终目录")
                self._hook_registry.fire("pre_atomic_move", ctx=self.ctx)
                self._atomic_move()
            success = True
        finally:
            if not success:
                self._cleanup()

        # dry-run 模式：生成完毕但无需移动，清理临时目录
        if self.dry_run:
            self._cleanup()

        self._hook_registry.safe_fire(
            "post_generate", ctx=self.ctx, generated=self.generated,
        )

        return self.generated

    # -- 内部方法 --

    def _progress(self, message: str) -> None:
        """发送进度通知（如设置了 progress_callback）。"""
        if self._progress_callback is not None:
            self._progress_callback(message)

    @staticmethod
    def _maybe_set_executable(path: Path) -> None:
        """为 .sh 文件设置可执行权限（POSIX 平台）。

        Windows 上 os.chmod 对 execute bit 是 noop，不会影响 Windows 用户。
        文件系统不支持时静默忽略。
        """
        if path.suffix == ".sh":
            try:
                path.chmod(0o755)
            except OSError:
                pass  # 只读文件系统或平台不支持 execute bit

    def render_template_file(self, section: str, tpl_subpath: str, out_subpath: str) -> None:
        """渲染单个模板文件（公共 API）。

        Section Renderer 通过此方法将模板文件渲染后写入临时目录。

        Args:
            section: 所属 section 名称（用于进度显示和文件分组）
            tpl_subpath: 相对于 templates_dir 的模板路径
            out_subpath: 相对于项目根目录的输出路径

        Raises:
            GenerationError: temp_dir 未初始化（未调用 generate() 或 with 块）
            ValueError: tpl_subpath 包含路径穿越（``..`` 段）
        """
        if self.temp_dir is None:
            raise GenerationError(
                "render_template_file() 在 temp_dir 初始化前被调用。"
                "请使用 generate() 或 with 语句。"
            )
        _validate_subpath(tpl_subpath, "tpl_subpath")
        src = self.templates_dir / tpl_subpath
        dst = self.temp_dir / out_subpath
        if src.exists():
            actual = render_file(
                src, dst, self.ctx, templates_dir=self.templates_dir,
            )
            self.generated.append((section, str(actual.relative_to(self.temp_dir))))
            self._maybe_set_executable(actual)
        else:
            logger.warning("模板不存在: %s", src)

    def _render(self, section: str, tpl_subpath: str, out_subpath: str) -> None:
        """Deprecated: 使用 :meth:`render_template_file` 代替。"""
        warnings.warn(
            "_render() is deprecated, use render_template_file() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.render_template_file(section, tpl_subpath, out_subpath)

    def write_file(self, section: str, out_subpath: str, content: str) -> None:
        """写入动态生成的纯文本文件（公共 API）。

        Section Renderer 通过此方法将动态内容写入临时目录。

        Args:
            section: 所属 section 名称
            out_subpath: 相对于项目根目录的输出路径
            content: 文件内容

        Raises:
            GenerationError: temp_dir 未初始化
        """
        if self.temp_dir is None:
            raise GenerationError(
                "write_file() 在 temp_dir 初始化前被调用。"
                "请使用 generate() 或 with 语句。"
            )
        dst = self.temp_dir / out_subpath
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(content, encoding="utf-8")
        self.generated.append((section, out_subpath))
        self._maybe_set_executable(dst)

    def copy_static_file(
        self, section: str, src_subpath: str, out_subpath: str,
    ) -> None:
        """复制静态文件到输出目录（公共 API）。

        用于不需要模板渲染、只需原样复制的文件（如 JSON 数据、二进制资源等）。

        Args:
            section: 所属 section 名称
            src_subpath: 相对于 templates_dir 的源文件路径
            out_subpath: 相对于项目根目录的输出路径

        Raises:
            GenerationError: temp_dir 未初始化
            ValueError: src_subpath 包含路径穿越（``..`` 段）
        """
        if self.temp_dir is None:
            raise GenerationError(
                "copy_static_file() 在 temp_dir 初始化前被调用。"
                "请使用 generate() 或 with 语句。"
            )
        _validate_subpath(src_subpath, "src_subpath")
        src = self.templates_dir / src_subpath
        dst = self.temp_dir / out_subpath
        if not src.exists():
            logger.warning("静态文件不存在: %s", src)
            return
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(src), str(dst))
        self.generated.append((section, out_subpath))
        self._maybe_set_executable(dst)

    def _write_raw(self, section: str, out_subpath: str, content: str) -> None:
        """Deprecated: 使用 :meth:`write_file` 代替。"""
        warnings.warn(
            "_write_raw() is deprecated, use write_file() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.write_file(section, out_subpath, content)

    def _create_directory_structure(self) -> None:
        """创建项目目录骨架。"""
        ctx = self.ctx
        dirs = [
            self.temp_dir,
            self.temp_dir / "config",
            self.temp_dir / "utils",
            self.temp_dir / ctx["PROJECT_NAME_SNAKE"] / "client",
            self.temp_dir / "testcase",
            self.temp_dir / "data" / "yaml",
            self.temp_dir / "data" / "json",
            self.temp_dir / "data" / "excel",
            self.temp_dir / "specs",
            self.temp_dir / "schemas",
            self.temp_dir / "mock_responses",
            self.temp_dir / "logs",
            self.temp_dir / "reports",
            self.temp_dir / "scripts",
            self.temp_dir / "ci",
            self.temp_dir / ".claude" / "commands",
        ]
        for biz in ctx["BUSINESS_LINES_RAW"]:
            dirs.append(self.temp_dir / "testcase" / biz)
            dirs.append(self.temp_dir / "specs" / biz)

        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

    def _atomic_move(self) -> None:
        """原子移动：从临时目录到最终位置。

        使用 staging 策略避免数据丢失：
        1. 旧目录 rename 到 staging（原子操作）
        2. 新目录移到目标位置
        3. 成功后清理 staging；失败则回滚 staging → output
        """
        output = Path(self.ctx["OUTPUT_DIR"]).resolve()
        output.parent.mkdir(parents=True, exist_ok=True)

        if not output.exists():
            # 无旧目录，直接移动
            shutil.move(str(self.temp_dir), str(output))
            self.temp_dir = None
            return

        # 有旧目录 — 使用 rename-aside 策略
        staging = output.with_name(f".{output.name}.staging")
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)

        # 阶段 1: 旧目录 rename 到 staging（原子操作）
        try:
            output.rename(staging)
        except OSError as e:
            raise GenerationError(
                f"无法移走已有目录 {output}: {e}\n"
                f"请检查是否有进程正在使用该目录。"
            ) from e

        # 阶段 2: 新目录移到目标位置
        try:
            shutil.move(str(self.temp_dir), str(output))
            self.temp_dir = None
        except OSError as e:
            # 回滚：staging → output
            if staging.exists():
                staging.rename(output)
            raise GenerationError(
                f"无法将生成的项目移动到 {output}: {e}\n"
                f"已回滚到原始目录。"
            ) from e

        # 阶段 3: 成功后清理 staging
        shutil.rmtree(staging, ignore_errors=True)

    def _cleanup(self) -> None:
        """清理临时目录。"""
        if self.temp_dir is not None and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            self.temp_dir = None


# ---------------------------------------------------------------------------
# 向后兼容的模块级函数
# ---------------------------------------------------------------------------

def generate_project(
    ctx: ProjectContext,
    templates_dir: Path,
    *,
    dry_run: bool = False,
    progress_callback: Callable[[str], None] | None = None,
) -> list[tuple[str, str]]:
    """生成完整的测试项目（向后兼容的模块级入口）。

    使用原子写入：先生成到临时目录，成功后再移动到最终位置。

    Args:
        ctx: 上下文字典
        templates_dir: 模板目录路径
        dry_run: 预览模式，只生成到临时目录但不移动到最终位置
        progress_callback: 可选的进度回调，每完成一个生成阶段被调用一次，
                          签名: (message: str) -> None

    Returns:
        生成的文件列表 [(section, filepath), ...]

    Raises:
        RuntimeError: 生成过程中出现 IO/权限/编码错误
    """
    gen = ProjectGenerator(
        ctx, templates_dir, dry_run=dry_run, progress_callback=progress_callback,
    )
    return gen.generate()


# ---------------------------------------------------------------------------
# 输出结果
# ---------------------------------------------------------------------------

def print_results(
    ctx: ProjectContext,
    generated: list[tuple[str, str]],
) -> None:
    """打印生成结果和下一步指引。"""
    _print_file_list(generated)
    _print_next_steps(ctx)
    _print_toolchain_reference(ctx)


def _print_file_list(generated: list[tuple[str, str]]) -> None:
    """打印生成的文件列表。"""
    print(f"\n{SEPARATOR}")
    print(f"  生成完成！共 {len(generated)} 个文件")

    # 按 section 聚合（保持插入顺序），避免 groupby 对不连续键的重复分组
    sections: dict[str, list[str]] = {}
    for section, filepath in generated:
        sections.setdefault(section, []).append(filepath)

    for section, files in sections.items():
        print(f"\n  [{section}]")
        for filepath in files:
            print(f"  [OK] {filepath}")


def _print_next_steps(ctx: ProjectContext) -> None:
    """打印下一步操作指引。"""
    project_name = ctx["PROJECT_NAME"]
    output = ctx["OUTPUT_DIR"]

    print(f"\n{SEPARATOR}")
    print(f"  项目 {project_name} 生成完毕！\n")
    print("  下一步操作：")
    step = count(1)
    print(f"    {next(step)}. cd {output}")
    print(f"    {next(step)}. pip install -r requirements.txt")
    if ctx["HAS_DB"]:
        print(f"    {next(step)}. cp variables_override.yaml.template variables_override.yaml")
        print("       （填写 DB 密码、API 密钥等敏感配置）")
    print(f"    {next(step)}. 编辑 specs/registry.yaml，注册你的 spec 文档")
    print(f"    {next(step)}. 在 specs/ 下添加规格文档（参考 specs/spec-template.md）")
    print(f"    {next(step)}. python scripts/validate_specs.py  （校验 spec 注册表）")
    print(f"    {next(step)}. python scripts/generate_skeletons.py  （自动生成测试骨架）")
    print(f"    {next(step)}. 使用 /test-workflow 开始编写第一批测试")
    print(f"    {next(step)}. pre-commit install  （安装 Git Hooks 质量门禁）")

    ci_system = ctx["CI_SYSTEM"]
    if ci_system == CISystem.GITHUB.value:
        print(f"    {next(step)}. CI 已配置: .github/workflows/testspec.yml（push 后自动运行）")
    elif ci_system == CISystem.GITLAB.value:
        print(f"    {next(step)}. CI 已配置: .gitlab-ci.yml（push 后自动运行）")
    else:
        if sys.platform == "win32":
            print(f"    {next(step)}. .\\{ctx['RUN_SCRIPT_NAME']}.ps1")
        else:
            print(f"    {next(step)}. bash {ctx['RUN_SCRIPT_NAME']}.sh")


def _print_toolchain_reference(ctx: ProjectContext) -> None:
    """打印工具链命令速查。"""
    print("\n  工具链命令速查：")
    print("    python scripts/validate_specs.py      # 校验 spec 注册表")
    print("    python scripts/check_coverage.py      # spec→test 覆盖率")
    print("    python scripts/generate_skeletons.py  # 生成测试骨架")
    print("    python scripts/generate_skeletons.py --append  # 追加缺失测试函数")
    print("    python scripts/generate_clients.py    # 生成 API Client 桩")
    print("    python scripts/import_openapi.py <swagger.yaml>  # 导入 OpenAPI 接口")
    print("    python scripts/spec_diff.py           # spec 变更影响分析")
    print("    python scripts/detect_flaky.py        # Flaky Test 检测")
    print("    python scripts/generate_metrics.py    # 质量度量数据")
    print("    python scripts/check_compliance.py    # 合规自检")
    print("    python scripts/mcp_server.py          # 启动 MCP Server（AI 工具链）")
    if ctx["HAS_DB"]:
        print("    docker-compose -f docker-compose.test.yml up -d  # 启动测试数据库")
    print()
