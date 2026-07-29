"""testspec.yaml_emitter 模块的单元测试。

覆盖 yaml_dump 的标量、dict、list、多行字符串、QuotedStr、
特殊字符处理和 header_comment 等功能。
"""
from __future__ import annotations

import pytest

from testspec.yaml_emitter import yaml_dump, QuotedStr


class TestYamlDumpScalars:
    """标量值序列化。"""

    def test_none_value(self) -> None:
        assert yaml_dump({"key": None}) == "key:\n"

    def test_bool_true(self) -> None:
        assert yaml_dump({"key": True}) == "key: true\n"

    def test_bool_false(self) -> None:
        assert yaml_dump({"key": False}) == "key: false\n"

    def test_integer(self) -> None:
        assert yaml_dump({"key": 42}) == "key: 42\n"

    def test_float(self) -> None:
        assert yaml_dump({"key": 3.14}) == "key: 3.14\n"

    def test_empty_string(self) -> None:
        assert yaml_dump({"key": ""}) == 'key: ""\n'

    def test_simple_string(self) -> None:
        assert yaml_dump({"key": "hello"}) == "key: hello\n"


class TestYamlDumpQuotedStr:
    """QuotedStr 强制引号。"""

    def test_quoted_str_produces_double_quoted(self) -> None:
        result = yaml_dump({"version": QuotedStr("3.11")})
        assert '"3.11"' in result

    def test_quoted_str_escapes_backslash(self) -> None:
        result = yaml_dump({"key": QuotedStr("a\\b")})
        assert '"a\\\\b"' in result

    def test_quoted_str_escapes_doublequote(self) -> None:
        result = yaml_dump({"key": QuotedStr('a"b')})
        assert '"a\\"b"' in result


class TestYamlDumpDict:
    """字典序列化。"""

    def test_simple_flat_dict(self) -> None:
        result = yaml_dump({"name": "test", "version": 1})
        assert "name: test" in result
        assert "version: 1" in result

    def test_nested_dict(self) -> None:
        result = yaml_dump({"parent": {"child": "value"}})
        assert "parent:" in result
        assert "  child: value" in result

    def test_empty_dict(self) -> None:
        result = yaml_dump({"key": {}})
        assert "key: {}" in result

    def test_dict_with_none_value(self) -> None:
        result = yaml_dump({"key": None})
        assert "key:" in result

    def test_header_comment(self) -> None:
        result = yaml_dump({"key": "val"}, header_comment="Auto-generated")
        assert result.startswith("# Auto-generated\n")


class TestYamlDumpList:
    """列表序列化。"""

    def test_list_of_scalars_inline(self) -> None:
        """≤3 个短标量应内联为 [a, b, c]。"""
        result = yaml_dump({"items": ["a", "b", "c"]})
        assert "[a, b, c]" in result

    def test_list_of_scalars_block(self) -> None:
        """>3 个标量应逐行输出。"""
        result = yaml_dump({"items": ["a", "b", "c", "d"]})
        assert "  - a" in result
        assert "  - d" in result

    def test_list_of_dicts(self) -> None:
        result = yaml_dump({"steps": [{"name": "s1", "run": "echo hi"}]})
        assert "- name: s1" in result
        assert "  run: echo hi" in result

    def test_empty_list(self) -> None:
        result = yaml_dump({"items": []})
        assert "items: []" in result

    def test_list_of_integers(self) -> None:
        result = yaml_dump({"ports": [80, 443]})
        assert "[80, 443]" in result


class TestYamlDumpMultiline:
    """多行字符串（块标量 ``|``）。"""

    def test_multiline_value_in_dict(self) -> None:
        result = yaml_dump({"script": "line1\nline2\n"})
        assert "script: |" in result
        assert "  line1" in result
        assert "  line2" in result

    def test_multiline_value_as_first_list_item_key(self) -> None:
        """H1 回归测试：多行字符串作为列表项首键时 body 行不能以 '- ' 开头。"""
        data = {"steps": [{"run": "echo hello\necho world\n", "name": "test"}]}
        result = yaml_dump(data)
        lines = result.split("\n")
        # 找到 block scalar 标记行
        block_scalar_line = None
        for i, line in enumerate(lines):
            if "run: |" in line:
                block_scalar_line = i
                break
        assert block_scalar_line is not None, "应包含 block scalar 标记"
        # body 行不能以 "- " 开头（排除列表标记行）
        body_line = lines[block_scalar_line + 1]
        assert not body_line.lstrip().startswith("- "), (
            f"body 行不应以 '- ' 开头: {body_line!r}"
        )
        # body 行应该包含实际内容
        assert "echo hello" in body_line

    def test_multiline_value_as_second_list_item_key(self) -> None:
        """非首键的多行字符串也应正确缩进。"""
        data = {"steps": [{"name": "test", "run": "echo hello\necho world\n"}]}
        result = yaml_dump(data)
        assert "run: |" in result
        assert "echo hello" in result
        assert "echo world" in result

    def test_multiline_body_indentation(self) -> None:
        """body 行的缩进应与键名对齐，而非与列表标记对齐。"""
        data = {"steps": [{"run": "cmd1\ncmd2\n"}]}
        result = yaml_dump(data)
        lines = result.split("\n")
        for line in lines:
            if "cmd1" in line or "cmd2" in line:
                # body 行不应以 "- " 开头
                stripped = line.lstrip()
                assert not stripped.startswith("- "), (
                    f"body 行错误地以 '- ' 开头: {line!r}"
                )


class TestSpecialCharacters:
    """特殊字符和保留字的引号处理。"""

    def test_reserved_word_true(self) -> None:
        result = yaml_dump({"key": "true"})
        assert '"true"' in result

    def test_reserved_word_null(self) -> None:
        result = yaml_dump({"key": "null"})
        assert '"null"' in result

    def test_reserved_word_yes(self) -> None:
        result = yaml_dump({"key": "yes"})
        assert '"yes"' in result

    def test_colon_space_in_value(self) -> None:
        result = yaml_dump({"key": "a: b"})
        assert '"a: b"' in result

    def test_leading_dash(self) -> None:
        result = yaml_dump({"key": "-item"})
        assert '"-item"' in result

    def test_key_with_special_chars(self) -> None:
        result = yaml_dump({"a:b": "value"})
        assert '"a:b"' in result

    def test_numeric_string_not_quoted(self) -> None:
        """纯数字字符串不需要引号（除非是 QuotedStr）。"""
        result = yaml_dump({"port": "8080"})
        # "8080" 可以被解析为数字，但 _needs_quoting 对纯数字返回 False
        assert "port: 8080" in result

    def test_hash_in_value(self) -> None:
        result = yaml_dump({"key": "value # comment"})
        assert '"value # comment"' in result
