"""TestSpec 交互式向导。

通过 stdin/stdout 收集用户输入，返回构建上下文所需的参数。
"""

from __future__ import annotations

import sys
from typing import Any

from .constants import (
    VERSION,
    TEST_TYPES,
    LANG_FRAMEWORKS,
    DB_TYPES,
    REPORT_TOOLS,
    CI_SYSTEMS,
    LANGUAGES,
    SEPARATOR,
    PROJECT_NAME_PATTERN,
)

__all__ = [
    "ask",
    "ask_choice",
    "ask_multi",
    "ask_yes_no",
    "run_wizard",
    "confirm_wizard",
]


# ---------------------------------------------------------------------------
# 交互辅助函数
# ---------------------------------------------------------------------------

def ask(prompt: str, default: str = "") -> str:
    """请求用户输入一行文本。"""
    if default:
        val = input(f"  {prompt} [{default}]: ").strip()
        return val if val else default
    return input(f"  {prompt}: ").strip()


def ask_choice(
    prompt: str,
    options: dict[str, tuple[str, ...]],
    default: str = "1",
) -> str:
    """显示选项列表并请求用户单选。"""
    print(f"\n  {prompt}")
    for k, v in options.items():
        desc = v[-1]
        marker = " (默认)" if k == default else ""
        print(f"    {k}. {desc}{marker}")
    while True:
        val = input(f"  请选择 [{default}]: ").strip()
        val = val if val else default
        if val in options:
            return val
        print(f"  [WARN] 无效选项 '{val}'，请从 {', '.join(options.keys())} 中选择")


def ask_multi(
    prompt: str,
    options: dict[str, tuple[str, ...]],
) -> list[str]:
    """显示编号选项列表并接受逗号分隔的多选输入。

    Args:
        prompt: 展示给用户的问题文本。
        options: 编号键 → 元组的映射，元组最后一个元素为展示描述，
                 第一个元素为返回的代码值。

    Returns:
        用户选中的代码值列表（元组的第一个元素）。
        若未输入有效选项则返回空列表。
    """
    print(f"\n  {prompt}")
    for k, v in options.items():
        print(f"    {k}. {v[-1]}")
    val = input("  可多选，逗号分隔（例如：1 或 1,4）: ").strip()
    keys = [v.strip() for v in val.split(",") if v.strip()]
    return [options[k][0] for k in keys if k in options]


def ask_yes_no(prompt: str, default: bool = True) -> bool:
    """请求用户 yes/no 确认。"""
    suffix = "Y/n" if default else "y/N"
    val = input(f"  {prompt} ({suffix}): ").strip().lower()
    if not val:
        return default
    return val in ("y", "yes", "是")


# ---------------------------------------------------------------------------
# 向导主流程
# ---------------------------------------------------------------------------

def run_wizard() -> dict[str, Any]:
    """运行交互式向导，返回用户选择的参数字典。

    Returns:
        dict with keys: project_name, test_types, language, framework,
        database, report_tool, business_lines, output_dir, ci_system,
        language_locale

    Raises:
        SystemExit: 用户按 Ctrl+C 或输入流结束时优雅退出。
    """
    try:
        return _run_wizard_impl()
    except (EOFError, KeyboardInterrupt):
        print("\n  已取消。")
        sys.exit(0)


def _run_wizard_impl() -> dict[str, Any]:
    """交互式向导实现细节。"""
    print(f"\n{SEPARATOR}")
    print(f"  TestSpec 框架脚手架 v{VERSION}")
    print(f"  规格优先的测试自动化工程化框架")
    print(f"{SEPARATOR}")

    result: dict[str, Any] = {}

    # 步骤 1: 项目名称
    print("\n[步骤 1/8] 项目基本信息")
    project_name = ask("请输入项目名称（英文连字符格式，例如：order-service-tests）")
    while not project_name or not PROJECT_NAME_PATTERN.match(project_name):
        print("  [WARN] 项目名称必须以小写字母开头，只含小写字母、数字和连字符")
        project_name = ask("请重新输入项目名称")
    result["project_name"] = project_name

    # 步骤 2: 测试类型
    print("\n[步骤 2/8] 测试类型（决定技能模板和工具桩的内容）")
    test_types = ask_multi("请选择测试类型：", TEST_TYPES)
    if not test_types:
        test_types = ["api"]
        print("  未选择，默认使用: api")
    result["test_types"] = test_types

    # 步骤 3: 语言与框架
    print("\n[步骤 3/8] 编程语言与测试框架")
    lang_choice = ask_choice("请选择语言与框架：", LANG_FRAMEWORKS, "1")
    lang, framework, _ = LANG_FRAMEWORKS[lang_choice]
    result["language"] = lang
    result["framework"] = framework
    if lang != "python":
        print(f"  [WARN] {lang} 的工具桩需手动移植，当前仅 Python 提供完整模板")

    # 步骤 4: 数据库
    print("\n[步骤 4/8] 数据库配置")
    use_db = ask_yes_no(
        "是否需要数据库校验？",
        default=("api" in test_types or "integ" in test_types),
    )
    if use_db:
        db_choice = ask_choice("请选择数据库类型：", DB_TYPES, "1")
        db_type, _ = DB_TYPES[db_choice]
        result["database"] = db_type
    else:
        result["database"] = "none"

    # 步骤 5: 报告工具
    print("\n[步骤 5/8] 测试报告工具")
    report_choice = ask_choice("请选择报告工具：", REPORT_TOOLS, "1")
    report_tool, _ = REPORT_TOOLS[report_choice]
    result["report_tool"] = report_tool

    # 步骤 6: CI 系统
    print("\n[步骤 6/8] CI/CD 系统")
    ci_choice = ask_choice("请选择 CI/CD 系统：", CI_SYSTEMS, "1")
    ci_system, _ = CI_SYSTEMS[ci_choice]
    result["ci_system"] = ci_system

    # 步骤 7: 业务线
    print("\n[步骤 7/8] 业务线 / 功能模块")
    biz_lines_raw = ask(
        "请输入业务线或功能模块名称（英文，逗号分隔，例如：order,payment,inventory）"
    )
    biz_lines = [b.strip() for b in biz_lines_raw.split(",") if b.strip()]
    if not biz_lines:
        biz_lines = ["default"]
        print("  未输入，使用默认: default")
    result["business_lines"] = biz_lines

    # 步骤 8: 输出目录与语言
    print("\n[步骤 8/8] 输出与语言")
    default_dir = f"./{project_name}"
    output_dir = ask("请输入生成项目的目标目录", default_dir)
    result["output_dir"] = output_dir

    locale_choice = ask_choice("文档语言：", LANGUAGES, "1")
    locale, _ = LANGUAGES[locale_choice]
    result["language_locale"] = locale

    return result


def confirm_wizard(params: dict[str, Any]) -> bool:
    """显示参数摘要并请求用户确认。"""
    print(f"\n{SEPARATOR}")
    print("  参数确认：")
    print(f"    项目名称：{params['project_name']}")
    print(f"    测试类型：{', '.join(params['test_types'])}")
    print(f"    语言框架：{params['language']} / {params['framework']}")
    print(f"    数据库  ：{params['database']}")
    print(f"    报告工具：{params['report_tool']}")
    print(f"    CI 系统 ：{params['ci_system']}")
    print(f"    业务线  ：{', '.join(params['business_lines'])}")
    print(f"    输出目录：{params['output_dir']}")
    print(f"    文档语言：{params['language_locale']}")
    print(f"{SEPARATOR}")
    return ask_yes_no("确认生成？", default=True)
