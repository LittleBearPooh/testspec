"""TestSpec CLI 入口。

提供 `testspec` 命令行工具：
    testspec init                     # 交互式初始化
    testspec init --config x.json     # 非交互式初始化
    testspec init --yes               # 使用默认值直接生成
    testspec validate [path]          # 校验已生成项目的完整性
    testspec version                  # 显示版本

全局参数：
    -v, --verbose                     # 显示详细日志输出
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import NoReturn

from .constants import VERSION, SEPARATOR
from .context import build_context_from_config, build_context_from_wizard, ProjectContext
from .wizard import run_wizard, confirm_wizard, ask_yes_no
from .generator import ProjectGenerator, generate_project, print_results
from .exceptions import ConfigError, GenerationError

__all__ = ["main", "_print_dry_run"]

# 模板目录：位于包内 testspec/templates/，支持环境变量覆盖
def _find_templates_dir() -> Path:
    """定位模板目录。

    查找顺序：
    1. 环境变量 ``TESTSPEC_TEMPLATES_DIR``（高级用户自定义路径）
    2. 包内 ``templates/`` 子目录（pip install 和开发模式通用）
    """
    env_dir = os.environ.get("TESTSPEC_TEMPLATES_DIR")
    if env_dir:
        p = Path(env_dir)
        if p.is_dir():
            return p

    pkg_templates = Path(__file__).resolve().parent / "templates"
    if pkg_templates.is_dir():
        return pkg_templates

    raise FileNotFoundError(
        f"找不到 templates 目录（已查找: {pkg_templates}）。\n"
        f"请确认安装完整，或设置环境变量 TESTSPEC_TEMPLATES_DIR 指向模板目录。"
    )


def _build_parser() -> argparse.ArgumentParser:
    """构建 CLI 参数解析器。"""
    parser = argparse.ArgumentParser(
        prog="testspec",
        description=f"TestSpec v{VERSION} — 规格优先的测试自动化工程化框架",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        default=False,
        help="显示详细日志输出（DEBUG 级别）",
    )
    subparsers = parser.add_subparsers(dest="command")

    # init 子命令
    init_parser = subparsers.add_parser("init", help="初始化新测试项目")
    init_parser.add_argument(
        "--config",
        metavar="FILE",
        help="JSON 配置文件路径（非交互式模式）",
    )
    init_parser.add_argument(
        "-y", "--yes",
        action="store_true",
        default=False,
        help="使用默认值直接生成，跳过确认",
    )
    init_parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="预览模式：只显示将生成的文件列表，不写入磁盘",
    )
    init_parser.add_argument(
        "--plugin",
        metavar="GROUP",
        nargs="?",
        const="testspec.sections",
        default=None,
        help="从 entry_points 加载插件 Section（可选：指定分组名称）",
    )

    # version 子命令
    subparsers.add_parser("version", help="显示版本信息")

    # validate 子命令
    validate_parser = subparsers.add_parser(
        "validate", help="校验已生成项目的完整性",
    )
    validate_parser.add_argument(
        "project_dir",
        nargs="?",
        default=".",
        help="待校验的项目目录路径（默认当前目录）",
    )

    # upgrade 子命令
    upgrade_parser = subparsers.add_parser(
        "upgrade",
        help="升级已生成项目的框架管理文件（保留用户测试代码）",
    )
    upgrade_parser.add_argument(
        "project_dir",
        nargs="?",
        default=".",
        help="待升级的项目目录路径（默认当前目录）",
    )
    upgrade_parser.add_argument(
        "-y", "--yes",
        action="store_true",
        default=False,
        help="跳过确认，直接执行升级",
    )
    upgrade_parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="预览模式：只显示将变更的文件，不实际修改",
    )

    return parser


def cmd_init(args: argparse.Namespace) -> None:
    """初始化新测试项目。"""
    try:
        templates_dir = _find_templates_dir()
    except FileNotFoundError as e:
        _fatal(str(e))

    ctx = _resolve_context(args)
    if ctx is None:
        return  # 用户取消或错误已报告

    dry_run = getattr(args, "dry_run", False)

    if not dry_run and not _confirm_output_dir(ctx, args.yes):
        print("  已取消。")
        return

    if dry_run:
        print("\n[DRY-RUN] 预览生成（不会写入磁盘）...\n")
    else:
        print(f"\n正在生成项目到 {Path(ctx['OUTPUT_DIR']).resolve()} ...\n")

    # 加载插件 Section Renderers（如指定了 --plugin）
    section_renderers = None
    plugin_group = getattr(args, "plugin", None)
    if plugin_group is not None:
        from .sections import default_renderers, load_plugin_renderers
        plugin_renderers = load_plugin_renderers(group=plugin_group)
        if plugin_renderers:
            section_renderers = default_renderers() + plugin_renderers
            print(f"  已加载 {len(plugin_renderers)} 个插件 Section Renderer")

    try:
        gen = ProjectGenerator(
            ctx, templates_dir, dry_run=dry_run,
            section_renderers=section_renderers,
        )
        generated = gen.generate()
    except GenerationError as e:
        _fatal(str(e))

    if dry_run:
        _print_dry_run(ctx, generated)
    else:
        print_results(ctx, generated)


def _resolve_context(args: argparse.Namespace) -> ProjectContext | None:
    """根据参数解析构建上下文，失败或取消时返回 None。"""
    if args.config:
        try:
            return build_context_from_config(args.config)
        except ConfigError as e:
            _fatal(f"配置文件错误: {e}")

    params = run_wizard()
    if not args.yes and not confirm_wizard(params):
        print("  已取消。")
        return None

    return build_context_from_wizard(**params)


def _confirm_output_dir(ctx: ProjectContext, auto_yes: bool) -> bool:
    """检查输出目录是否存在，必要时请求用户确认。"""
    output = Path(ctx["OUTPUT_DIR"]).resolve()
    if not output.exists() or auto_yes:
        return True
    return ask_yes_no(f"目录 {output} 已存在，是否覆盖？", default=False)


def _print_dry_run(
    ctx: ProjectContext, generated: list[tuple[str, str]],
) -> None:
    """打印 dry-run 预览结果，包含目录树和分区统计。"""
    output = Path(ctx["OUTPUT_DIR"]).resolve()
    print(f"\n{SEPARATOR}")
    print(f"  [DRY-RUN] 预览生成结果 — 共 {len(generated)} 个文件")
    print(f"  目标目录：{output}")
    print(f"  项目配置：{ctx['PROJECT_NAME']} | "
          f"测试类型: {', '.join(ctx['TEST_TYPES'])} | "
          f"语言: {ctx['LANGUAGE']}/{ctx['TEST_FRAMEWORK']}"
          f"{' | 数据库: ' + ctx['DB_TYPE'] if ctx['HAS_DB'] else ''}")

    # 按 section 聚合
    sections: dict[str, list[str]] = {}
    for section, filepath in generated:
        sections.setdefault(section, []).append(filepath)

    # 目录树预览（前3层）
    print(f"\n  [+] {output.name}/")
    _dirs_seen: set[str] = set()
    for _, filepath in generated:
        parts = filepath.replace("\\", "/").split("/")
        # 只显示前 2 层目录结构
        for depth in range(1, min(len(parts), 3)):
            dir_path = "/".join(parts[:depth])
            if dir_path not in _dirs_seen:
                _dirs_seen.add(dir_path)
                indent = "  " * (depth + 1)
                print(f"{indent}├── {parts[depth - 1]}/")

    # 分区文件列表
    print(f"\n  文件清单：")
    for section, files in sections.items():
        print(f"\n  [{section}] ({len(files)} 个文件)")
        for filepath in files[:20]:
            print(f"    [OK] {filepath}")
        if len(files) > 20:
            print(f"    ... 还有 {len(files) - 20} 个文件")

    # 汇总统计
    print(f"\n  ────────────────────────────────────────")
    print(f"  汇总：{len(sections)} 个分区, {len(generated)} 个文件")
    for section, files in sections.items():
        print(f"    {section:<12s}  {len(files):>3d} 个文件")
    print(f"\n  以上为预览结果，实际生成时文件内容相同。")
    print(f"  去掉 --dry-run 参数即可写入磁盘。")


def _fatal(msg: str, code: int = 1) -> NoReturn:
    """输出错误信息并终止程序。

    使用 ``raise SystemExit`` 而非 ``sys.exit()``，便于测试和库调用场景捕获。
    """
    print(f"[ERROR] {msg}", file=sys.stderr)
    raise SystemExit(code)


def cmd_version() -> None:
    """显示版本信息。"""
    print(f"TestSpec v{VERSION}")
    print("Spec-First Test Automation Engineering Framework")


# ---------------------------------------------------------------------------
# 项目完整性校验
# ---------------------------------------------------------------------------

def cmd_validate(args: argparse.Namespace) -> None:
    """校验已生成项目的完整性。"""
    from .validator import ProjectValidator

    project_dir = Path(args.project_dir).resolve()

    if not project_dir.is_dir():
        _fatal(f"目录不存在: {project_dir}")

    print(f"\n{SEPARATOR}")
    print(f"  TestSpec 项目完整性校验")
    print(f"  项目目录: {project_dir}")
    print(f"{SEPARATOR}\n")

    validator = ProjectValidator(project_dir)
    results = validator.validate()

    # 按类别分组输出
    _CATEGORY_HEADERS = {
        "structure": None,  # 文件检查无独立标题
        "manifest": None,
        "business": None,
        "skills": None,
        "syntax": "内容校验",
        "requirements": None,
        "json": None,
    }

    prev_cat = ""
    for r in results:
        # 在内容校验区域前插入分隔线
        if r.category == "syntax" and prev_cat != "syntax":
            print(f"\n  ── 内容校验 ──")

        if r.status == "ok":
            print(f"  [OK] {r.path:<45s} {r.message}")
        elif r.status == "error":
            print(f"  [!!] {r.path:<45s} {r.message}")
        else:
            print(f"  [--] {r.path:<45s} {r.message}")
        prev_cat = r.category

    # 汇总
    passed, warnings_count, errors = validator.counts
    total = passed + warnings_count + errors
    print(f"\n{SEPARATOR}")
    print(f"  校验结果: {total} 项检查")
    print(f"    [OK] 通过: {passed}")
    print(f"    [--] 警告: {warnings_count}")
    print(f"    [!!] 错误: {errors}")

    if errors > 0:
        print(f"\n  项目完整性校验失败，存在 {errors} 个必需文件缺失。")
        print(f"  建议重新运行 testspec init 生成项目。")
        raise SystemExit(1)
    elif warnings_count > 0:
        print(f"\n  项目基本完整，有 {warnings_count} 个可选文件缺失。")
    else:
        print(f"\n  项目完整性校验通过！")


# ---------------------------------------------------------------------------
# upgrade 子命令
# ---------------------------------------------------------------------------

def cmd_upgrade(args: argparse.Namespace) -> None:
    """升级已生成项目的框架管理文件。"""
    from .upgrader import ProjectUpgrader

    project_dir = Path(args.project_dir).resolve()
    if not project_dir.is_dir():
        _fatal(f"目录不存在: {project_dir}")

    try:
        templates_dir = _find_templates_dir()
    except FileNotFoundError as e:
        _fatal(str(e))

    print(f"\n{SEPARATOR}")
    print(f"  TestSpec 升级")
    print(f"  项目目录: {project_dir}")
    print(f"  框架版本: {VERSION}")
    if args.dry_run:
        print(f"  模式: 预览（不修改文件）")
    print(f"{SEPARATOR}\n")

    # 阶段 1：只做 diff 比对（一次性生成，结果缓存到 UpgradeAction.new_content）
    upgrader = ProjectUpgrader(project_dir, templates_dir, dry_run=args.dry_run)

    try:
        actions = upgrader.plan()
    except ConfigError as e:
        _fatal(str(e))

    updated = [r for r in actions if r.status == "updated"]
    new_files = [r for r in actions if r.status == "new"]
    unchanged = [r for r in actions if r.status == "unchanged"]

    for r in updated:
        print(f"  [CHANGED] {r.path}")
        if r.diff:
            diff_lines = r.diff.splitlines()[:20]
            for line in diff_lines:
                print(f"    {line}")
            if len(r.diff.splitlines()) > 20:
                print(f"    ... (diff truncated)")
            print()

    for r in new_files:
        print(f"  [NEW]     {r.path}")

    print(f"\n  摘要: {len(updated)} 个文件已更新, "
          f"{len(new_files)} 个新文件, "
          f"{len(unchanged)} 个文件无变化")

    if args.dry_run:
        print(f"\n  这是预览结果。去掉 --dry-run 参数即可应用更改。")
        return

    if not updated and not new_files:
        print(f"\n  项目已是最新版本，无需升级。")
        return

    if not args.yes:
        from .wizard import ask_yes_no
        if not ask_yes_no(f"确认升级 {len(updated) + len(new_files)} 个文件？", default=True):
            print("  已取消。")
            return

    # 阶段 2：使用缓存的 new_content 写入磁盘（无需重新生成）
    upgrader.apply(actions)
    print(f"\n  升级完成！")


def main(argv: list[str] | None = None) -> None:
    """CLI 主入口。"""
    parser = _build_parser()
    args = parser.parse_args(argv)

    # 设置日志级别
    log_level = logging.DEBUG if getattr(args, "verbose", False) else logging.WARNING
    logging.basicConfig(level=log_level, format="%(levelname)s: %(message)s")

    if not args.command:
        parser.print_help()
        return

    if args.command == "init":
        cmd_init(args)
    elif args.command == "validate":
        cmd_validate(args)
    elif args.command == "version":
        cmd_version()
    elif args.command == "upgrade":
        cmd_upgrade(args)


if __name__ == "__main__":
    main()
