"""TestSpec 模板引擎单元测试。"""
from pathlib import Path

import pytest

from testspec.renderer import render_template, render_file


class TestRenderTemplate:
    """render_template 基础测试。"""

    def test_simple_substitution(self):
        result = render_template("Hello {{NAME}}!", {"NAME": "World"})
        assert result == "Hello World!"

    def test_if_block_true(self):
        result = render_template("{{#IF_OK}}yes{{/IF_OK}}", {"OK": True})
        assert result == "yes"

    def test_if_block_false(self):
        result = render_template("{{#IF_OK}}yes{{/IF_OK}}", {"OK": False})
        assert result == ""

    def test_if_not_block(self):
        result = render_template("{{#IF_NOT_OK}}no{{/IF_NOT_OK}}", {"OK": False})
        assert result == "no"

    def test_nested_blocks(self):
        tpl = "{{#IF_A}}outer-{{#IF_B}}inner{{/IF_B}}{{/IF_A}}"
        result = render_template(tpl, {"A": True, "B": True})
        assert result == "outer-inner"

    def test_non_string_scalar_substitution(self):
        result = render_template("count: {{COUNT}}", {"COUNT": 42})
        assert result == "count: 42"

    def test_bool_substitution(self):
        result = render_template("flag: {{FLAG}}", {"FLAG": True})
        assert result == "flag: True"

    def test_list_not_substituted(self):
        with pytest.warns(UserWarning, match="残留未替换占位符"):
            result = render_template("items: {{ITEMS}}", {"ITEMS": [1, 2]})
        assert result == "items: {{ITEMS}}"

    def test_missing_key_unchanged(self):
        with pytest.warns(UserWarning, match="残留未替换占位符"):
            result = render_template("{{MISSING}}", {})
        assert result == "{{MISSING}}"

    def test_source_path_in_error_context(self):
        """source_path 参数不影响正常渲染结果。"""
        result = render_template(
            "Hello {{NAME}}!", {"NAME": "World"}, source_path="test.tpl",
        )
        assert result == "Hello World!"


class TestRenderFile:
    """render_file 文件级测试。"""

    def test_tpl_suffix_stripped(self, tmp_path: Path) -> None:
        """渲染 .tpl 文件时应去除后缀。"""
        src = tmp_path / "test.md.tpl"
        src.write_text("Hello {{NAME}}!", encoding="utf-8")
        dst = tmp_path / "output" / "test.md.tpl"
        actual = render_file(src, dst, {"NAME": "World"})
        assert actual.name == "test.md"
        assert actual.read_text(encoding="utf-8") == "Hello World!"

    def test_non_tpl_copied_as_is(self, tmp_path: Path) -> None:
        """非 .tpl 文件应原样复制。"""
        src = tmp_path / "data.json"
        src.write_text('{"key": "value"}', encoding="utf-8")
        dst = tmp_path / "output" / "data.json"
        actual = render_file(src, dst, {})
        assert actual.name == "data.json"
        assert actual.read_text(encoding="utf-8") == '{"key": "value"}'

    def test_parent_dir_created(self, tmp_path: Path) -> None:
        """目标目录不存在时应自动创建。"""
        src = tmp_path / "test.txt"
        src.write_text("content", encoding="utf-8")
        dst = tmp_path / "deep" / "nested" / "dir" / "test.txt"
        actual = render_file(src, dst, {})
        assert actual.exists()


class TestForLoop:
    """FOR 循环块测试。"""

    def test_basic_for_loop(self) -> None:
        result = render_template(
            "{{#FOR item IN ITEMS}}[{{item}}]{{/FOR}}",
            {"ITEMS": ["a", "b", "c"]},
        )
        assert result == "[a][b][c]"

    def test_for_loop_with_surrounding_text(self) -> None:
        result = render_template(
            "before {{#FOR x IN LIST}}{{x}},{{/FOR}} after",
            {"LIST": ["1", "2"]},
        )
        assert result == "before 1,2, after"

    def test_for_loop_empty_list(self) -> None:
        result = render_template(
            "{{#FOR item IN ITEMS}}{{item}}{{/FOR}}",
            {"ITEMS": []},
        )
        assert result == ""

    def test_for_loop_missing_key(self) -> None:
        result = render_template(
            "{{#FOR item IN MISSING}}{{item}}{{/FOR}}",
            {},
        )
        assert result == ""

    def test_for_loop_non_list_value(self) -> None:
        result = render_template(
            "{{#FOR item IN NOT_A_LIST}}{{item}}{{/FOR}}",
            {"NOT_A_LIST": "hello"},
        )
        assert result == ""

    def test_for_loop_with_tuple(self) -> None:
        result = render_template(
            "{{#FOR item IN TUPLE}}{{item}};{{/FOR}}",
            {"TUPLE": ("x", "y")},
        )
        assert result == "x;y;"

    def test_for_loop_with_if_block(self) -> None:
        """FOR 循环与 IF 条件块组合使用。"""
        tpl = "{{#IF_HAS_ITEMS}}{{#FOR item IN ITEMS}}{{item}} {{/FOR}}{{/IF_HAS_ITEMS}}"
        result = render_template(tpl, {"HAS_ITEMS": True, "ITEMS": ["a", "b"]})
        assert result == "a b "

    def test_for_loop_if_block_false(self) -> None:
        tpl = "{{#IF_HAS_ITEMS}}{{#FOR item IN ITEMS}}{{item}}{{/FOR}}{{/IF_HAS_ITEMS}}"
        result = render_template(tpl, {"HAS_ITEMS": False, "ITEMS": ["a", "b"]})
        assert result == ""

    def test_two_for_loops_in_same_template(self) -> None:
        tpl = "A:{{#FOR a IN LIST_A}}{{a}},{{/FOR}} B:{{#FOR b IN LIST_B}}{{b}};{{/FOR}}"
        result = render_template(tpl, {"LIST_A": ["1", "2"], "LIST_B": ["x", "y"]})
        assert result == "A:1,2, B:x;y;"

    def test_for_loop_numeric_items(self) -> None:
        result = render_template(
            "{{#FOR n IN NUMS}}{{n}} {{/FOR}}",
            {"NUMS": [10, 20, 30]},
        )
        assert result == "10 20 30 "

    def test_if_block_inside_for_loop_true(self) -> None:
        """IF 条件块在 FOR 循环体内部，条件为 True 时保留。"""
        tpl = "{{#FOR item IN ITEMS}}[{{item}}{{#IF_SHOW_TAG}}:tag{{/IF_SHOW_TAG}}]{{/FOR}}"
        result = render_template(tpl, {"ITEMS": ["a", "b"], "SHOW_TAG": True})
        assert result == "[a:tag][b:tag]"

    def test_if_block_inside_for_loop_false(self) -> None:
        """IF 条件块在 FOR 循环体内部，条件为 False 时移除。"""
        tpl = "{{#FOR item IN ITEMS}}[{{item}}{{#IF_SHOW_TAG}}:tag{{/IF_SHOW_TAG}}]{{/FOR}}"
        result = render_template(tpl, {"ITEMS": ["a", "b"], "SHOW_TAG": False})
        assert result == "[a][b]"

    def test_if_not_block_inside_for_loop(self) -> None:
        """IF_NOT 条件块在 FOR 循环体内部。"""
        tpl = "{{#FOR item IN ITEMS}}{{item}}{{#IF_NOT_HAS_PREFIX}}-raw{{/IF_NOT_HAS_PREFIX}};{{/FOR}}"
        result = render_template(tpl, {"ITEMS": ["x", "y"], "HAS_PREFIX": False})
        assert result == "x-raw;y-raw;"

    def test_if_not_block_inside_for_loop_true(self) -> None:
        """IF_NOT 条件块在 FOR 循环体内部，条件为 True 时移除。"""
        tpl = "{{#FOR item IN ITEMS}}{{item}}{{#IF_NOT_HAS_PREFIX}}-raw{{/IF_NOT_HAS_PREFIX}};{{/FOR}}"
        result = render_template(tpl, {"ITEMS": ["x", "y"], "HAS_PREFIX": True})
        assert result == "x;y;"


class TestInclude:
    """{{> partial_name}} include 指令测试。"""

    def _make_partials(self, tmp_path: Path) -> Path:
        d = tmp_path / "_partials"
        d.mkdir(exist_ok=True)
        return d

    def test_basic_include(self, tmp_path: Path) -> None:
        self._make_partials(tmp_path).joinpath("greeting.tpl").write_text(
            "Hello {{NAME}}!", encoding="utf-8",
        )
        result = render_template(
            "{{> greeting}}", {"NAME": "World"}, templates_dir=tmp_path,
        )
        assert result == "Hello World!"

    def test_include_with_conditions(self, tmp_path: Path) -> None:
        self._make_partials(tmp_path).joinpath("block.tpl").write_text(
            "{{#IF_SHOW}}visible{{/IF_SHOW}}", encoding="utf-8",
        )
        result = render_template(
            "{{> block}}", {"SHOW": True}, templates_dir=tmp_path,
        )
        assert result == "visible"

    def test_nested_include(self, tmp_path: Path) -> None:
        d = self._make_partials(tmp_path)
        d.joinpath("inner.tpl").write_text("INNER", encoding="utf-8")
        d.joinpath("outer.tpl").write_text("OUT:{{> inner}}", encoding="utf-8")
        result = render_template("{{> outer}}", {}, templates_dir=tmp_path)
        assert result == "OUT:INNER"

    def test_circular_include_raises(self, tmp_path: Path) -> None:
        d = self._make_partials(tmp_path)
        d.joinpath("a.tpl").write_text("{{> b}}", encoding="utf-8")
        d.joinpath("b.tpl").write_text("{{> a}}", encoding="utf-8")
        from testspec.exceptions import TemplateError
        with pytest.raises(TemplateError, match="循环引用"):
            render_template("{{> a}}", {}, templates_dir=tmp_path)

    def test_missing_partial_raises(self, tmp_path: Path) -> None:
        self._make_partials(tmp_path)
        from testspec.exceptions import TemplateError
        with pytest.raises(TemplateError, match="未找到"):
            render_template("{{> nonexistent}}", {}, templates_dir=tmp_path)

    def test_no_templates_dir_skips_include(self) -> None:
        """无 templates_dir 时 {{> x}} 标签保留原样（向后兼容）。"""
        result = render_template("before {{> partial}} after", {})
        assert result == "before {{> partial}} after"

    def test_include_in_render_file(self, tmp_path: Path) -> None:
        d = tmp_path / "_partials"
        d.mkdir()
        (d / "footer.tpl").write_text("Footer: {{VER}}", encoding="utf-8")
        src = tmp_path / "doc.md.tpl"
        src.write_text("Body\n{{> footer}}", encoding="utf-8")
        dst = tmp_path / "out" / "doc.md.tpl"
        actual = render_file(src, dst, {"VER": "1.0"}, templates_dir=tmp_path)
        assert actual.read_text(encoding="utf-8") == "Body\nFooter: 1.0"

    def test_include_path_traversal_raises(self, tmp_path: Path) -> None:
        """{{> ../secret}} 路径穿越应被拦截并抛出 TemplateError。"""
        d = self._make_partials(tmp_path)
        # 在 _partials/ 之外创建一个文件
        (tmp_path / "secret.txt").write_text("SENSITIVE", encoding="utf-8")
        from testspec.exceptions import TemplateError
        with pytest.raises(TemplateError, match="路径穿越|非法路径段"):
            render_template("{{> ../secret.txt}}", {}, templates_dir=tmp_path)

    def test_include_path_traversal_deep_raises(self, tmp_path: Path) -> None:
        """多层 ../ 路径穿越也应被拦截。"""
        self._make_partials(tmp_path)
        from testspec.exceptions import TemplateError
        with pytest.raises(TemplateError, match="路径穿越|非法路径段"):
            render_template(
                "{{> ../../../../etc/passwd}}", {}, templates_dir=tmp_path,
            )


class TestResidualPlaceholderDetection:
    """模板渲染后残留占位符检测测试。"""

    def test_no_residual_no_warning(self) -> None:
        """所有占位符均被替换时，不产生警告。"""
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            result = render_template("Hello {{NAME}}!", {"NAME": "World"})
        assert result == "Hello World!"

    def test_residual_warns(self) -> None:
        """残留占位符默认发出警告（strict=False）。"""
        with pytest.warns(UserWarning, match="残留未替换占位符"):
            result = render_template("{{KNOWN}} {{UNKNOWN}}", {"KNOWN": "ok"})
        assert result == "ok {{UNKNOWN}}"

    def test_residual_strict_raises(self) -> None:
        """strict=True 时残留占位符抛出 TemplateError。"""
        from testspec.exceptions import TemplateError
        with pytest.raises(TemplateError, match="残留未替换占位符"):
            render_template(
                "{{KNOWN}} {{UNKNOWN}}",
                {"KNOWN": "ok"},
                strict=True,
            )

    def test_residual_strict_all_replaced_ok(self) -> None:
        """strict=True 但所有占位符均被替换时不抛异常。"""
        result = render_template(
            "{{A}} {{B}}",
            {"A": "1", "B": "2"},
            strict=True,
        )
        assert result == "1 2"

    def test_double_underscore_prefix_filtered(self) -> None:
        """双下划线开头的占位符视为内部保留，不触发检测。"""
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            result = render_template("{{__ESCAPED__}}", {})
        assert result == "{{__ESCAPED__}}"

    def test_lowercase_placeholder_filtered(self) -> None:
        """小写占位符视为 Python f-string 变量或文档示例，不触发检测。

        TestSpec 上下文键约定为全大写 UPPER_CASE，小写键名通常是
        模板内嵌的 Python 代码（如 ``f"{{{{param}}}}"``）。
        """
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            result = render_template("{{param}} {{body_lines}}", {})
        assert result == "{{param}} {{body_lines}}"

    def test_residual_source_path_in_message(self) -> None:
        """残留检测警告信息包含 source_path。"""
        with pytest.warns(UserWarning, match="test\\.tpl"):
            render_template(
                "{{MISSING}}",
                {},
                source_path="test.tpl",
            )

    def test_multiple_residual_reported(self) -> None:
        """多个残留占位符全部被报告。"""
        with pytest.warns(UserWarning, match="ALPHA.*BETA"):
            render_template("{{ALPHA}} {{BETA}}", {})

    def test_render_file_strict_raises(self, tmp_path: Path) -> None:
        """render_file 透传 strict 参数。"""
        from testspec.exceptions import TemplateError
        src = tmp_path / "bad.md.tpl"
        src.write_text("{{MISSING_KEY}}", encoding="utf-8")
        dst = tmp_path / "out" / "bad.md.tpl"
        with pytest.raises(TemplateError, match="残留未替换占位符"):
            render_file(src, dst, {}, strict=True)

    def test_residual_strict_includes_line_number(self) -> None:
        """strict=True 抛出的 TemplateError 应包含行号。"""
        from testspec.exceptions import TemplateError
        tpl = "line1\nline2\n{{MISSING_KEY}}"
        with pytest.raises(TemplateError) as exc_info:
            render_template(tpl, {}, strict=True)
        assert exc_info.value.line_number == 3

    def test_residual_warning_includes_line_info(self) -> None:
        """警告消息应包含行号信息。"""
        tpl = "ok\n{{UNKNOWN}}"
        with pytest.warns(UserWarning, match=r"line \d"):
            render_template(tpl, {})

    def test_multiline_template_correct_line(self) -> None:
        """多行模板中残留占位符应报告正确行号。"""
        from testspec.exceptions import TemplateError
        tpl = "header\n{{OK}}\n{{BAD_KEY}}\nfooter"
        with pytest.raises(TemplateError) as exc_info:
            render_template(tpl, {"OK": "replaced"}, strict=True)
        assert exc_info.value.line_number == 3


class TestElseBlock:
    """{{#IF_KEY}}...{{#ELSE}}...{{/IF_KEY}} ELSE 分支测试。"""

    def test_else_when_true(self) -> None:
        """条件为 True 时返回 then-body。"""
        tpl = "{{#IF_OK}}yes{{#ELSE}}no{{/IF_OK}}"
        assert render_template(tpl, {"OK": True}) == "yes"

    def test_else_when_false(self) -> None:
        """条件为 False 时返回 else-body。"""
        tpl = "{{#IF_OK}}yes{{#ELSE}}no{{/IF_OK}}"
        assert render_template(tpl, {"OK": False}) == "no"

    def test_else_key_missing(self) -> None:
        """键缺失时返回 else body。"""
        tpl = "{{#IF_OK}}yes{{#ELSE}}no{{/IF_OK}}"
        assert render_template(tpl, {}) == "no"

    def test_no_else_unchanged(self) -> None:
        """普通 IF 块（无 ELSE）仍然正常工作。"""
        tpl = "{{#IF_OK}}yes{{/IF_OK}}"
        assert render_template(tpl, {"OK": True}) == "yes"
        assert render_template(tpl, {"OK": False}) == ""

    def test_nested_else_outer_true_inner_true(self) -> None:
        """嵌套 ELSE：外层 True，内层 True。"""
        tpl = (
            "{{#IF_A}}"
            "A:{{#IF_B}}B-yes{{#ELSE}}B-no{{/IF_B}}"
            "{{#ELSE}}no-A{{/IF_A}}"
        )
        assert render_template(tpl, {"A": True, "B": True}) == "A:B-yes"

    def test_nested_else_outer_true_inner_false(self) -> None:
        """嵌套 ELSE：外层 True，内层 False。"""
        tpl = (
            "{{#IF_A}}"
            "A:{{#IF_B}}B-yes{{#ELSE}}B-no{{/IF_B}}"
            "{{#ELSE}}no-A{{/IF_A}}"
        )
        assert render_template(tpl, {"A": True, "B": False}) == "A:B-no"

    def test_nested_else_outer_false(self) -> None:
        """嵌套 ELSE：外层 False。"""
        tpl = (
            "{{#IF_A}}"
            "A:{{#IF_B}}B-yes{{#ELSE}}B-no{{/IF_B}}"
            "{{#ELSE}}no-A{{/IF_A}}"
        )
        assert render_template(tpl, {"A": False, "B": True}) == "no-A"

    def test_else_with_substitution(self) -> None:
        """ELSE body 中包含占位符替换。"""
        tpl = "{{#IF_OK}}correct{{#ELSE}}error: {{MSG}}{{/IF_OK}}"
        result = render_template(tpl, {"OK": False, "MSG": "not found"})
        assert result == "error: not found"

    def test_else_multiline(self) -> None:
        """ELSE 块跨多行。"""
        tpl = (
            "{{#IF_ENABLED}}\n"
            "feature on\n"
            "{{#ELSE}}\n"
            "feature off\n"
            "{{/IF_ENABLED}}"
        )
        assert render_template(tpl, {"ENABLED": True}) == "\nfeature on\n"
        assert render_template(tpl, {"ENABLED": False}) == "\nfeature off\n"

    def test_else_with_for_loop(self) -> None:
        """ELSE 块与 FOR 循环组合。"""
        tpl = (
            "{{#IF_HAS_ITEMS}}"
            "{{#FOR x IN ITEMS}}[{{x}}]{{/FOR}}"
            "{{#ELSE}}empty{{/IF_HAS_ITEMS}}"
        )
        result = render_template(
            tpl, {"HAS_ITEMS": True, "ITEMS": ["a", "b"]},
        )
        assert result == "[a][b]"
        result_empty = render_template(
            tpl, {"HAS_ITEMS": False, "ITEMS": []},
        )
        assert result_empty == "empty"


# ---------------------------------------------------------------------------
# 模板转义语法测试 (v1.2.0)
# ---------------------------------------------------------------------------


class TestTemplateEscape:
    """\\{{KEY}} 转义语法测试。"""

    def test_basic_escape_prevents_substitution(self):
        """\\{{KEY}} 应输出字面量 {{KEY}}，不被替换。"""
        result = render_template(r'\{{KEY}}', {"KEY": "value"})
        assert result == "{{KEY}}"

    def test_escape_with_no_context_key(self):
        """转义后的 {{KEY}} 不触发残留占位符检测。"""
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            result = render_template(r'\{{MISSING_KEY}}', {})
        assert result == "{{MISSING_KEY}}"

    def test_escape_inside_if_true_block(self):
        """转义在 IF 块内也生效。"""
        result = render_template(
            r'{{#IF_OK}}\{{KEY}}{{/IF_OK}}',
            {"OK": True, "KEY": "replaced"},
        )
        assert result == "{{KEY}}"

    def test_escape_inside_for_loop(self):
        """转义在 FOR 循环内也生效。"""
        result = render_template(
            r'{{#FOR x IN LIST}}\{{x}}{{/FOR}}',
            {"LIST": ["a", "b"]},
        )
        assert result == "{{x}}{{x}}"

    def test_multiple_escapes_in_template(self):
        """多个转义同时存在。"""
        result = render_template(r'\{{A}} literal, \{{B}} literal', {})
        assert result == "{{A}} literal, {{B}} literal"

    def test_mixed_escaped_and_real_placeholders(self):
        """转义占位符与正常占位符共存。"""
        result = render_template(r'\{{LITERAL}} and {{REAL}}', {"REAL": "value"})
        assert result == "{{LITERAL}} and value"

    def test_escape_in_partial(self, tmp_path: Path):
        """partial 中的 \\{{ 也应被转义。"""
        d = tmp_path / "_partials"
        d.mkdir()
        (d / "partial.tpl").write_text(r"example: \{{KEY}}", encoding="utf-8")
        result = render_template("{{> partial}}", {}, templates_dir=tmp_path)
        assert result == "example: {{KEY}}"


# ---------------------------------------------------------------------------
# FOR 循环局部作用域测试 (v1.2.0)
# ---------------------------------------------------------------------------


class TestForLoopLocalScope:
    """FOR 循环局部作用域（v1.2.0 新增功能）。"""

    def test_if_condition_on_loop_variable_truthy(self):
        """循环变量为非空时，{{#IF_var}} 块显示。"""
        tpl = "{{#FOR item IN ITEMS}}{{#IF_item}}[{{item}}]{{/IF_item}}{{/FOR}}"
        result = render_template(tpl, {"ITEMS": ["hello", "world"]})
        assert result == "[hello][world]"

    def test_if_condition_on_loop_variable_empty_string(self):
        """循环变量为空字符串时，{{#IF_var}} 块隐藏。"""
        tpl = "{{#FOR item IN ITEMS}}{{#IF_item}}[{{item}}]{{/IF_item}}{{/FOR}}"
        result = render_template(tpl, {"ITEMS": ["a", "", "b"]})
        assert result == "[a][b]"

    def test_if_not_condition_on_loop_variable(self):
        """{{#IF_NOT_var}} 对空循环变量显示。"""
        tpl = "{{#FOR x IN LIST}}{{#IF_NOT_x}}(empty){{/IF_NOT_x}}{{/FOR}}"
        result = render_template(tpl, {"LIST": ["val", "", "v2"]})
        assert result == "(empty)"

    def test_loop_variable_does_not_pollute_outer_scope(self):
        """循环变量不影响外层 ctx。"""
        import warnings
        tpl = "{{#FOR item IN LIST}}{{item}} {{/FOR}}|outer={{ITEM_FROM_OUTER}}"
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            result = render_template(
                tpl,
                {"LIST": ["x"], "ITEM_FROM_OUTER": "global"},
            )
        assert result == "x |outer=global"

    def test_nested_for_different_loop_variables(self):
        """不同变量名的嵌套 FOR 循环各自独立。"""
        tpl = (
            "{{#FOR outer IN OUTER}}"
            "{{#FOR inner IN INNER}}"
            "{{outer}}-{{inner}} "
            "{{/FOR}}"
            "{{/FOR}}"
        )
        result = render_template(
            tpl,
            {"OUTER": ["A", "B"], "INNER": ["1", "2"]},
        )
        assert result == "A-1 A-2 B-1 B-2 "

    def test_loop_variable_shadows_global_key(self):
        """循环变量名与全局 ctx 键同名时，局部值优先。"""
        tpl = "{{#FOR LANG IN LANGS}}{{#IF_LANG}}[{{LANG}}]{{/IF_LANG}}{{/FOR}}"
        result = render_template(
            tpl,
            {"LANGS": ["python", ""], "LANG": "global_override"},
        )
        assert result == "[python]"


# ---------------------------------------------------------------------------
# 同名嵌套块错误检测测试
# ---------------------------------------------------------------------------


class TestSameNameNestingDetection:
    """同名嵌套 IF 块的明确错误检测。"""

    def test_same_name_nesting_raises_specific_error(self) -> None:
        """同名嵌套块应产生包含 '同名嵌套' 的清晰错误，而非通用收敛错误。"""
        from testspec.exceptions import TemplateError
        tpl = "{{#IF_FOO}}outer{{#IF_FOO}}inner{{/IF_FOO}}{{/IF_FOO}}"
        with pytest.raises(TemplateError, match="同名嵌套"):
            render_template(tpl, {"FOO": True})

    def test_same_name_nesting_error_includes_key_name(self) -> None:
        """错误信息应包含出问题的 key 名称。"""
        from testspec.exceptions import TemplateError
        tpl = "{{#IF_MY_KEY}}outer{{#IF_MY_KEY}}inner{{/IF_MY_KEY}}{{/IF_MY_KEY}}"
        with pytest.raises(TemplateError, match="MY_KEY"):
            render_template(tpl, {"MY_KEY": True})

    def test_different_key_nesting_is_unaffected(self) -> None:
        """不同 key 的多层嵌套应正常工作，不触发同名检测。"""
        tpl = "{{#IF_A}}outer-{{#IF_B}}inner{{/IF_B}}{{/IF_A}}"
        result = render_template(tpl, {"A": True, "B": True})
        assert result == "outer-inner"

    def test_find_same_name_nesting_detects_multiple_keys(self) -> None:
        """_find_same_name_nesting 应检测多个同名嵌套 key。"""
        from testspec.renderer import _find_same_name_nesting
        content = (
            "{{#IF_X}}a{{#IF_X}}b{{/IF_X}}{{/IF_X}}"
            "{{#IF_Y}}c{{#IF_Y}}d{{/IF_Y}}{{/IF_Y}}"
        )
        result = _find_same_name_nesting(content)
        assert "X" in result
        assert "Y" in result

    def test_find_same_name_nesting_returns_empty_for_valid(self) -> None:
        """正常的非同名嵌套应返回空列表。"""
        from testspec.renderer import _find_same_name_nesting
        content = "{{#IF_A}}{{#IF_B}}{{/IF_B}}{{/IF_A}}"
        assert _find_same_name_nesting(content) == []
