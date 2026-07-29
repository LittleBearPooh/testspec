"""TestSpec YAML 序列化器。

纯 stdlib 实现的最小化 YAML 发射器，用于生成 CI/CD 配置文件。
支持 dict、list、str（含多行 ``|`` 块标量）、int、float、bool、None。

零外部依赖，不引入 PyYAML / ruamel.yaml。
"""

from __future__ import annotations

from typing import Any, Union

__all__ = ["yaml_dump", "QuotedStr"]

# ---------------------------------------------------------------------------
# QuotedStr — 显式标记需要引号的字符串
# ---------------------------------------------------------------------------

class QuotedStr(str):
    """标记一个字符串在 YAML 输出时必须带引号。

    用于版本号（如 '3.11'）等看起来像数字但必须是字符串的值。

    Usage::

        data = {"python-version": QuotedStr("3.11")}
        yaml_dump(data)  # → python-version: "3.11"
    """
    pass

# YAML 值中首字符需引号的特殊字符
_YAML_VALUE_START_SPECIAL = frozenset("'\"{}[]&*!|>%@`#")

# YAML 键名特殊字符（更宽松：键名允许 - _ .）
_YAML_KEY_SPECIAL = frozenset(":{}[]&*?|>!%@`#")

# YAML 保留字（不可作为裸值）
_YAML_RESERVED = frozenset({
    "true", "false", "yes", "no", "on", "off",
    "null", "~",
    "True", "False", "Yes", "No", "On", "Off",
    "TRUE", "FALSE", "YES", "NO", "ON", "OFF",
})


def yaml_dump(
    data: Union[dict, list],
    *,
    indent: int = 2,
    header_comment: str = "",
) -> str:
    """将 Python dict/list 序列化为 YAML 格式字符串。

    Args:
        data: 要序列化的数据（dict 或 list）。
        indent: 缩进空格数（默认 2）。
        header_comment: 可选的头部注释（不含 ``#`` 前缀）。

    Returns:
        YAML 格式字符串，末尾带换行符。
    """
    lines: list[str] = []

    if header_comment:
        for line in header_comment.splitlines():
            lines.append(f"# {line}" if line else "#")
        lines.append("")

    _emit(data, lines, level=0, indent=indent)

    result = "\n".join(lines)
    if not result.endswith("\n"):
        result += "\n"
    return result


# ---------------------------------------------------------------------------
# 内部实现
# ---------------------------------------------------------------------------

_YamlValue = Union[dict, list, str, int, float, bool, None]


def _emit(
    data: _YamlValue,
    lines: list[str],
    level: int,
    indent: int,
) -> None:
    """递归发射 YAML 行。"""
    prefix = " " * (level * indent)

    if isinstance(data, dict):
        if not data:
            lines.append(f"{prefix}{{}}")
            return
        for key, value in data.items():
            key_str = _format_key(key, level, indent)
            if isinstance(value, dict) and value:
                lines.append(f"{prefix}{key_str}:")
                _emit(value, lines, level + 1, indent)
            elif isinstance(value, list) and value:
                # 检查列表元素是否都是简单标量
                if all(_is_scalar(v) for v in value):
                    # 简单标量列表：内联或逐行
                    if len(value) <= 3 and all(
                        _inline_safe(v) for v in value
                    ):
                        items = ", ".join(_format_scalar(v) for v in value)
                        lines.append(f"{prefix}{key_str}: [{items}]")
                    else:
                        lines.append(f"{prefix}{key_str}:")
                        for item in value:
                            lines.append(
                                f"{prefix}{' ' * indent}- {_format_scalar(item)}"
                            )
                else:
                    lines.append(f"{prefix}{key_str}:")
                    _emit_list(value, lines, level + 1, indent)
            elif value is None:
                lines.append(f"{prefix}{key_str}:")
            else:
                formatted = _format_scalar(value)
                if isinstance(value, str) and "\n" in value:
                    lines.append(f"{prefix}{key_str}: |")
                    for line in value.rstrip("\n").splitlines():
                        lines.append(f"{prefix}{' ' * indent}{line}")
                else:
                    lines.append(f"{prefix}{key_str}: {formatted}")

    elif isinstance(data, list):
        if not data:
            lines.append(f"{prefix}[]")
            return
        _emit_list(data, lines, level, indent)

    else:
        lines.append(f"{prefix}{_format_scalar(data)}")


def _emit_list(
    data: list,
    lines: list[str],
    level: int,
    indent: int,
) -> None:
    """发射 YAML 列表。

    列表项中的 dict 使用 ``- key:`` 语法（首个键与列表标记同行），
    后续键与首个键对齐。内部辅助 ``_emit_kv`` 通过闭包捕获
    ``level + 2`` 确保嵌套 dict/list 的缩进层级正确，
    消除首键与后续键之间约 30 行的重复代码。
    """
    prefix = " " * (level * indent)
    # 列表项内嵌套 dict/list 值统一使用 level + 2（而非 level + 1），
    # 因为列表标记 ``- `` 额外占据一层缩进。
    nested_level = level + 2

    def _emit_kv(key_str: str, value: _YamlValue, line_prefix: str, body_extra: int) -> None:
        """发射列表项内的单个 key: value 对。

        Args:
            key_str: 已格式化的键名
            value: 值
            line_prefix: 键行前缀（首键 ``prefix + "- "``，后续 ``prefix + indent``）
            body_extra: 多行字符串体相对于 line_prefix 的额外缩进空格数
        """
        if isinstance(value, dict) and value:
            lines.append(f"{line_prefix}{key_str}:")
            _emit(value, lines, nested_level, indent)
        elif isinstance(value, list) and value:
            lines.append(f"{line_prefix}{key_str}:")
            _emit_list(value, lines, nested_level, indent)
        elif value is None:
            lines.append(f"{line_prefix}{key_str}:")
        elif isinstance(value, str) and "\n" in value:
            lines.append(f"{line_prefix}{key_str}: |")
            body_pad = " " * body_extra
            for line in value.rstrip("\n").splitlines():
                lines.append(f"{rest_prefix}{body_pad}{line}")
        else:
            lines.append(f"{line_prefix}{key_str}: {_format_scalar(value)}")

    first_prefix = f"{prefix}- "
    rest_prefix = f"{prefix}{' ' * indent}"

    for item in data:
        if isinstance(item, dict) and item:
            first_key = True
            for key, value in item.items():
                key_str = _format_key(key, level, indent)
                if first_key:
                    # 首键: 前缀为 ``- ``，多行体使用 rest_prefix 对齐键名后方
                    _emit_kv(key_str, value, first_prefix, indent)
                    first_key = False
                else:
                    # 后续键: 前缀为缩进空格，多行体需 indent 对齐键名后方
                    _emit_kv(key_str, value, rest_prefix, indent)
        elif isinstance(item, list):
            lines.append(f"{prefix}-")
            _emit_list(item, lines, level + 1, indent)
        else:
            lines.append(f"{prefix}- {_format_scalar(item)}")


def _format_key(key: Any, level: int, indent: int) -> str:
    """格式化 YAML 键名。"""
    s = str(key)
    if _needs_key_quoting(s):
        return f'"{s}"'
    return s


def _format_scalar(value: _YamlValue) -> str:
    """格式化 YAML 标量值。"""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, QuotedStr):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        if not value:
            return '""'
        if _needs_quoting(value):
            escaped = value.replace("\\", "\\\\").replace('"', '\\"')
            return f'"{escaped}"'
        return value
    return str(value)


def _needs_quoting(s: str) -> bool:
    """判断字符串值是否需要引号包裹。"""
    if not s:
        return True
    # 保留字
    if s in _YAML_RESERVED:
        return True
    # 以特殊字符开头（- 开头可能被误解为列表项）
    if s[0] in _YAML_VALUE_START_SPECIAL or s[0] == "-":
        return True
    # 以数字/符号开头但非纯数字
    if s[0].isdigit() or s[0] in "+-.":
        try:
            float(s)
            return False
        except ValueError:
            return True
    # 包含特定位置的 problematic 字符（: 后跟空格、# 等）
    if ": " in s or " #" in s or s.endswith(":"):
        return True
    # 尾部空格
    if s != s.strip():
        return True
    # 包含换行符（由调用者单独处理为块标量）
    if "\n" in s:
        return False  # 多行字符串使用 | 语法，不需要引号
    return False


def _needs_key_quoting(s: str) -> bool:
    """判断 YAML 键名是否需要引号包裹。

    键名比值的规则更宽松：允许 - _ . 和数字。
    不检查保留字（YAML 1.2 中 on/off/yes/no 作为键名是合法的）。
    """
    if not s:
        return True
    if s[0].isdigit():
        return True
    for ch in s:
        if ch in _YAML_KEY_SPECIAL:
            return True
    return False


def _is_scalar(value: Any) -> bool:
    """判断值是否为简单标量（非 dict/list）。"""
    return isinstance(value, (str, int, float, bool)) or value is None


def _inline_safe(value: Any) -> bool:
    """判断值是否适合内联在 [...] 中。"""
    if not isinstance(value, (str, int, float, bool)):
        return False
    s = str(value)
    return len(s) < 40 and not _needs_quoting(s)
