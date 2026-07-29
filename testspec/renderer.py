"""TestSpec 模板引擎。

简易模板渲染：
  - {{> partial_name}} 包含指令（从 _partials/ 目录加载片段）
  - {{KEY}} 占位符替换
  - {{#IF_KEY}}...{{#ELSE}}...{{/IF_KEY}} 条件块（含可选 ELSE 分支）
  - {{#IF_KEY}}...{{/IF_KEY}} 条件包含块
  - {{#IF_NOT_KEY}}...{{/IF_NOT_KEY}} 条件排除块
  - {{#FOR var IN LIST_KEY}}...{{/FOR}} 循环块

支持不同 key 的多层嵌套条件块（相同 key 的嵌套不支持）。
引擎会迭代处理直到所有条件块展开完毕。
"""

from __future__ import annotations

import re
import shutil
import warnings
from pathlib import Path
from typing import Any

from .exceptions import TemplateError

__all__ = [
    "render_template",
    "render_file",
]

# 最大嵌套处理迭代次数，防止无限循环
_MAX_ITERATIONS = 10

# Include 最大递归深度
_MAX_INCLUDE_DEPTH = 5

# 预编译条件块正则（避免每次调用 re.sub 重新编译）
_IF_NOT_RE = re.compile(r"\{\{#IF_NOT_(\w+)\}\}(.*?)\{\{/IF_NOT_\1\}\}", re.DOTALL)

# IF-ELSE 正则：then-body 使用负向前瞻禁止包含嵌套 IF/IF_NOT 标签，
# 确保优先匹配最内层 ELSE 块，避免跨层泄漏。
_IF_ELSE_RE = re.compile(
    r"\{\{#IF_(\w+)\}\}"
    r"((?:(?!\{\{#(?:IF_|IF_NOT_)).)*?)"
    r"\{\{#ELSE\}\}"
    r"(.*?)"
    r"\{\{/IF_\1\}\}",
    re.DOTALL,
)

# 普通 IF 块（无 ELSE）
_IF_RE = re.compile(r"\{\{#IF_(\w+)\}\}(.*?)\{\{/IF_\1\}\}", re.DOTALL)

# 预编译 FOR 循环正则：{{#FOR var IN list_key}}body{{/FOR}}
_FOR_RE = re.compile(
    r"\{\{#FOR\s+(\w+)\s+IN\s+(\w+)\}\}(.*?)\{\{/FOR\}\}", re.DOTALL,
)

# 预编译 FOR 循环开始标签（_process_for_blocks 使用）
_FOR_OPEN_RE = re.compile(r"\{\{#FOR\s+(\w+)\s+IN\s+(\w+)\}\}")

# 预编译占位符扫描正则（用于只替换模板中实际出现的键）
_PLACEHOLDER_RE = re.compile(r"\{\{(\w+)\}\}")

# 预编译 include 指令正则：{{> partial_name}}
_INCLUDE_RE = re.compile(r"\{\{>\s*(\S+)\s*\}\}")

# 转义语法哨兵：\{{ 和 \}} 在处理前被替换为哨兵，处理后还原为字面量
# 使用 \x00 包裹确保不会与正常模板内容冲突（模板为 UTF-8 文本，不含空字节）
_ESCAPE_LBRACE_SENTINEL = "\x00TESTSPEC_LBRACE\x00"
_ESCAPE_RBRACE_SENTINEL = "\x00TESTSPEC_RBRACE\x00"

# 预编译同名嵌套检测正则：匹配 {{#IF_XXX}} 开标签
_IF_OPEN_RE = re.compile(r"\{\{#IF_(\w+)\}\}")


def _find_same_name_nesting(content: str) -> list[str]:
    """扫描模板内容，检测同名嵌套 IF 块。

    检测形如 ``{{#IF_FOO}}...{{#IF_FOO}}...{{/IF_FOO}}...{{/IF_FOO}}`` 的模式，
    其中内层开标签在外层闭标签之前出现（真正的嵌套，而非顺序排列）。

    顺序排列的同名块（``{{#IF_FOO}}...{{/IF_FOO}}...{{#IF_FOO}}...{{/IF_FOO}}``）
    是合法的，不会被标记。

    Returns:
        存在同名嵌套的 key 名称列表（可能为空）。
    """
    problematic: list[str] = []
    checked: set[str] = set()

    for m in _IF_OPEN_RE.finditer(content):
        key = m.group(1)
        if key in checked:
            continue
        checked.add(key)

        open_tag = f"{{{{#IF_{key}}}}}"
        close_tag = f"{{{{/IF_{key}}}}}"

        # 从第一个开标签之后开始扫描，跟踪嵌套深度
        depth = 1
        pos = m.end()
        while depth > 0 and pos < len(content):
            next_open = content.find(open_tag, pos)
            next_close = content.find(close_tag, pos)

            if next_close == -1:
                break  # 未找到闭标签，退出

            if next_open != -1 and next_open < next_close:
                # 在找到闭标签之前遇到了新的开标签 → 同名嵌套！
                depth += 1
                if depth == 2:
                    problematic.append(key)
                    break
                pos = next_open + len(open_tag)
            else:
                depth -= 1
                pos = next_close + len(close_tag)

    return problematic


def render_template(
    content: str,
    ctx: dict[str, Any],
    *,
    source_path: str | Path | None = None,
    templates_dir: Path | None = None,
    strict: bool = False,
) -> str:
    """渲染模板内容，替换占位符和条件块。

    处理顺序：
    0. 包含指令 {{> partial_name}}（需传入 templates_dir）
    0.5 转义预处理：``\\{{`` → 哨兵（防止后续步骤替换）
    1. 迭代处理条件块（支持不同 key 的多层嵌套）
       - 否定条件块 {{#IF_NOT_KEY}}...{{/IF_NOT_KEY}}
       - 正向条件块 {{#IF_KEY}}...{{/IF_KEY}}
       - FOR 循环块 {{#FOR var IN LIST_KEY}}...{{/FOR}}
    2. 占位符 {{KEY}} → ctx[KEY]
    3. 残留占位符检测（strict=True 时抛异常，否则 warn）
    4. 转义还原：哨兵 → ``{{``

    Args:
        content: 模板原始内容
        ctx: 上下文变量字典
        source_path: 模板文件路径（用于错误报告定位）
        templates_dir: 模板根目录（启用 ``{{> partial}}`` 包含指令）
        strict: 若为 True，渲染后存在未替换占位符时抛出 TemplateError；
                若为 False（默认），仅发出警告。
    """
    _loc = f" in {source_path}" if source_path else ""

    # Step 0: 处理 include 指令（必须在条件块之前，以便 partial 中包含条件块）
    if templates_dir is not None:
        try:
            content = _process_includes(content, templates_dir)
        except OSError as e:
            raise TemplateError(
                str(e),
                source_path=str(source_path) if source_path else None,
            ) from e

    # Step 0.5: 转义预处理 — \{{ 和 \}} 替换为哨兵，使后续正则全部忽略
    content = content.replace("\\{{", _ESCAPE_LBRACE_SENTINEL)
    content = content.replace("\\}}", _ESCAPE_RBRACE_SENTINEL)

    # 迭代处理嵌套条件块（含 FOR 循环）
    # 注意：FOR 必须先于 IF 处理。FOR 展开时内部已调用 _process_condition_blocks
    # 并使用局部上下文（含循环变量），确保 {{#IF_loopvar}} 能正确判断。
    # 外层 _process_condition_blocks 处理剩余的顶层 IF 块。

    # 预检：同名嵌套块检测（在迭代前主动扫描，防止静默产出错误结果）
    nested_keys = _find_same_name_nesting(content)
    if nested_keys:
        keys_str = ", ".join(nested_keys)
        raise TemplateError(
            f"模板中存在同名嵌套条件块（key: {keys_str}），这不被支持。"
            f"请将内层 {{{{#IF_{nested_keys[0]}}}}} 重命名为不同的 key，"
            f"或拆分到独立的 partial 文件中{_loc}。",
            source_path=str(source_path) if source_path else None,
        )

    for _ in range(_MAX_ITERATIONS):
        try:
            new_content = _process_for_blocks(content, ctx)
            new_content = _process_condition_blocks(new_content, ctx)
        except re.error as e:
            raise TemplateError(
                str(e),
                source_path=str(source_path) if source_path else None,
            ) from e
        if new_content == content:
            break
        content = new_content
    else:
        # 尝试识别同名嵌套块，给出更明确的错误信息
        _loc = f" in {source_path}" if source_path else ""
        nested_keys = _find_same_name_nesting(content)
        if nested_keys:
            keys_str = ", ".join(nested_keys)
            raise TemplateError(
                f"模板中存在同名嵌套条件块（key: {keys_str}），这不被支持。"
                f"请将内层 {{{{#IF_{nested_keys[0]}}}}} 重命名为不同的 key，"
                f"或拆分到独立的 partial 文件中{_loc}。",
                source_path=str(source_path) if source_path else None,
            )
        raise TemplateError(
            f"模板条件块在 {_MAX_ITERATIONS} 次迭代后未收敛{_loc}，"
            f"可能存在嵌套同名块（如 {{{{#IF_FOO}}}} 内再次出现 {{{{#IF_FOO}}}}）",
            source_path=str(source_path) if source_path else None,
        )

    # 替换占位符（只替换模板中实际出现的键，避免对 47 个键逐一 replace）
    used_keys = set(_PLACEHOLDER_RE.findall(content))
    for key in used_keys:
        value = ctx.get(key)
        if value is not None and not isinstance(value, (dict, list, set)):
            content = content.replace(f"{{{{{key}}}}}", str(value))

    # 残留占位符检测：逐行扫描以追踪行号
    key_to_lines: dict[str, list[int]] = {}
    for lineno, line in enumerate(content.split("\n"), start=1):
        for k in _PLACEHOLDER_RE.findall(line):
            if not k.startswith("__") and k == k.upper():
                key_to_lines.setdefault(k, []).append(lineno)

    if key_to_lines:
        sorted_residual = sorted(key_to_lines)
        detail = "; ".join(
            f"{k} (line {key_to_lines[k][0]})" for k in sorted_residual
        )
        msg = (
            f"模板渲染后残留未替换占位符{_loc}: {detail}。"
            f"请检查上下文中是否缺少对应键。"
        )
        first_line = key_to_lines[sorted_residual[0]][0]
        if strict:
            raise TemplateError(
                msg,
                source_path=str(source_path) if source_path else None,
                line_number=first_line,
            )
        warnings.warn(msg, stacklevel=2)

    # Step Final: 转义还原 — 哨兵还原为字面量 {{ 和 }}
    content = content.replace(_ESCAPE_LBRACE_SENTINEL, "{{")
    content = content.replace(_ESCAPE_RBRACE_SENTINEL, "}}")

    return content


def _process_condition_blocks(content: str, ctx: dict[str, Any]) -> str:
    """处理一轮 IF_NOT、IF-ELSE 和 IF 条件块替换。

    处理顺序：
    1. 否定条件块 {{#IF_NOT_KEY}}...{{/IF_NOT_KEY}}
    2. 含 ELSE 的条件块 {{#IF_KEY}}...{{#ELSE}}...{{/IF_KEY}}
       （必须在普通 IF 之前处理，避免 ELSE 标签泄漏到输出）
    3. 普通正向条件块 {{#IF_KEY}}...{{/IF_KEY}}

    设计为被 render_template 迭代调用，直到内容不再变化（收敛）为止。
    """
    # 处理否定条件块
    def _replace_not_block(m: re.Match) -> str:
        key = m.group(1)
        body = m.group(2)
        if not ctx.get(key):
            return body
        return ""

    content = _IF_NOT_RE.sub(
        _replace_not_block,
        content,
    )

    # 处理含 ELSE 的条件块（必须在普通 IF 之前）
    # 内层循环：IF-ELSE 需多轮处理以解决嵌套场景
    # （外层 IF-ELSE 的 then-body 包含内层 IF 标签时，
    #  负向前瞻导致外层不匹配；内层解析后外层才可匹配）
    def _replace_else_block(m: re.Match) -> str:
        key = m.group(1)
        then_body = m.group(2)
        else_body = m.group(3)
        return then_body if ctx.get(key) else else_body

    for _ in range(_MAX_ITERATIONS):
        new_content = _IF_ELSE_RE.sub(_replace_else_block, content)
        if new_content == content:
            break
        content = new_content

    # 处理普通正向条件块
    def _replace_block(m: re.Match) -> str:
        key = m.group(1)
        body = m.group(2)
        if ctx.get(key):
            return body
        return ""

    content = _IF_RE.sub(
        _replace_block,
        content,
    )

    return content


def _process_for_blocks(content: str, ctx: dict[str, Any]) -> str:
    """处理一轮 FOR 循环块替换。

    语法: ``{{#FOR item IN LIST_KEY}}...{{item}}...{{/FOR}}``

    对 ``LIST_KEY`` 中的每个元素，复制循环体并将其中的 ``{{item}}`` 替换为
    该元素的字符串值。列表键缺失或为空时，整个块被移除。

    v1.2.0: 循环变量注入局部上下文，支持 ``{{#IF_item}}`` / ``{{#IF_NOT_item}}``
    条件判断（基于当前迭代值的真值性）。局部变量不污染外层 ctx。

    循环体内部的 ``{{#IF_...}}`` / ``{{#IF_NOT_...}}`` 条件块会在变量替换后
    立即展开，确保每次迭代中的条件判断基于当前迭代上下文。

    设计为被 :func:`render_template` 迭代调用，以支持多层嵌套 FOR 块
    （不同变量名）。

    v1.2.0: 使用手动平衡解析替代正则 sub，正确处理嵌套 FOR 块
    （多个 ``{{#FOR}}`` 共享 ``{{/FOR}}`` 标签时，通过深度计数找到匹配对）。
    """
    # 使用手动解析替代 _FOR_RE.sub，以正确处理嵌套 FOR 块
    _FOR_CLOSE = "{{/FOR}}"

    result_parts: list[str] = []
    pos = 0

    while pos < len(content):
        m = _FOR_OPEN_RE.search(content, pos)
        if m is None:
            result_parts.append(content[pos:])
            break

        # 添加 FOR 标签之前的文本
        result_parts.append(content[pos:m.start()])

        var_name = m.group(1)
        list_key = m.group(2)
        body_start = m.end()

        # 通过深度计数找到匹配的 {{/FOR}} 标签
        depth = 1
        scan = body_start
        while depth > 0:
            next_open = _FOR_OPEN_RE.search(content, scan)
            next_close_idx = content.find(_FOR_CLOSE, scan)

            if next_close_idx == -1:
                # 未找到匹配的关闭标签，将剩余内容作为文本
                result_parts.append(content[m.start():])
                return "".join(result_parts)

            if next_open and next_open.start() < next_close_idx:
                depth += 1
                scan = next_open.end()
            else:
                depth -= 1
                if depth == 0:
                    body = content[body_start:next_close_idx]
                    pos = next_close_idx + len(_FOR_CLOSE)
                else:
                    scan = next_close_idx + len(_FOR_CLOSE)

        # 展开 FOR 循环
        items = ctx.get(list_key)
        if not isinstance(items, (list, tuple)):
            continue  # 列表缺失或非列表类型，整个块被移除

        for item in items:
            # 构建局部上下文（循环变量覆盖同名全局键，不污染外层 ctx）
            local_ctx = {**ctx, var_name: item}
            # 先替换循环变量
            expanded = body.replace(f"{{{{{var_name}}}}}", str(item))
            # 再处理循环体内的条件块（使用局部上下文，支持 {{#IF_var}} 判断）
            expanded = _process_condition_blocks(expanded, local_ctx)
            result_parts.append(expanded)

    return "".join(result_parts)


def _process_includes(
    content: str,
    templates_dir: Path,
    *,
    _depth: int = 0,
    _seen: frozenset[str] | None = None,
) -> str:
    """处理 ``{{> partial_name}}`` 包含指令。

    从 ``templates_dir/_partials/`` 加载 partial 文件并内联替换。
    支持嵌套 include（最大深度 :data:`_MAX_INCLUDE_DEPTH`）。
    检测循环引用并抛出 :class:`TemplateError`。

    Args:
        content: 含 ``{{> ...}}`` 标签的模板内容
        templates_dir: 模板根目录，``_partials/`` 在其下
        _depth: 当前递归深度（内部使用）
        _seen: 当前调用栈中已处理的文件路径集合（防循环）
    """
    if not _INCLUDE_RE.search(content):
        return content  # 快速路径：无 include 标签

    if _depth > _MAX_INCLUDE_DEPTH:
        warnings.warn(
            f"Include 嵌套超过 {_MAX_INCLUDE_DEPTH} 层，可能存在循环引用",
            stacklevel=2,
        )
        return content

    if _seen is None:
        _seen = frozenset()

    def _replace_include(m: re.Match) -> str:
        partial_name = m.group(1)
        partials_dir = templates_dir / "_partials"

        # 路径穿越防护：在 resolve 前拒绝包含 .. 的路径
        if ".." in partial_name.replace("\\", "/").split("/"):
            raise TemplateError(
                f"Partial '{partial_name}' 包含非法路径段 '..'，不允许访问 _partials/ 之外的文件",
                context_key=partial_name,
            )

        # 查找 partial 文件：先查原名，再查 .tpl 后缀
        candidate = partials_dir / partial_name
        if not candidate.exists():
            candidate = partials_dir / (partial_name + ".tpl")
        if not candidate.exists():
            raise TemplateError(
                f"Partial '{partial_name}' 未找到（搜索路径: {partials_dir}）",
                context_key=partial_name,
            )

        # 二次防护：resolve 后验证仍在 _partials/ 内
        resolved = candidate.resolve()
        try:
            resolved.relative_to(partials_dir.resolve())
        except ValueError:
            raise TemplateError(
                f"Partial '{partial_name}' 路径穿越：不允许访问 _partials/ 之外的文件",
                context_key=partial_name,
            )

        path_key = str(resolved)
        if path_key in _seen:
            raise TemplateError(
                f"循环引用检测: '{partial_name}' 已在处理栈中",
                context_key=partial_name,
            )

        partial_content = candidate.read_text(encoding="utf-8")
        return _process_includes(
            partial_content, templates_dir,
            _depth=_depth + 1, _seen=_seen | {path_key},
        )

    return _INCLUDE_RE.sub(_replace_include, content)


def render_file(
    src: Path,
    dst: Path,
    ctx: dict[str, Any],
    *,
    templates_dir: Path | None = None,
    strict: bool = False,
) -> Path:
    """读取模板文件，渲染后写入目标路径。

    如果目标路径以 ``.tpl`` 结尾，会自动去除该后缀；
    否则直接使用目标路径（适用于 generator.py 已指定正确输出名的场景）。

    Args:
        src: 模板源文件路径
        dst: 目标写入路径
        ctx: 上下文变量字典
        templates_dir: 模板根目录（启用 ``{{> partial}}`` 包含指令）
        strict: 若为 True，渲染后存在未替换占位符时抛出 TemplateError

    Returns:
        实际写入的文件路径。
    """
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.suffix == ".tpl":
        content = src.read_text(encoding="utf-8")
        rendered = render_template(
            content, ctx, source_path=src, templates_dir=templates_dir,
            strict=strict,
        )
        # 只有 dst 自身以 .tpl 结尾时才剥离，否则保留 generator 指定的文件名
        actual_dst = dst.with_suffix("") if dst.suffix == ".tpl" else dst
        actual_dst.write_text(rendered, encoding="utf-8")
        return actual_dst
    else:
        shutil.copy2(src, dst)
        return dst
