"""TestSpec 自定义异常层次测试。"""
from __future__ import annotations

import pytest

from testspec.exceptions import (
    TestSpecError,
    ConfigError,
    TemplateError,
    GenerationError,
)


class TestExceptionHierarchy:
    """验证异常继承关系正确性。"""

    def test_config_error_is_testspec_error(self) -> None:
        assert issubclass(ConfigError, TestSpecError)

    def test_config_error_is_value_error(self) -> None:
        """向后兼容：ConfigError 必须也是 ValueError。"""
        assert issubclass(ConfigError, ValueError)

    def test_generation_error_is_testspec_error(self) -> None:
        assert issubclass(GenerationError, TestSpecError)

    def test_generation_error_is_runtime_error(self) -> None:
        """向后兼容：GenerationError 必须也是 RuntimeError。"""
        assert issubclass(GenerationError, RuntimeError)

    def test_template_error_is_testspec_error(self) -> None:
        assert issubclass(TemplateError, TestSpecError)

    def test_config_error_caught_by_value_error(self) -> None:
        """现有 except ValueError 代码能捕获 ConfigError。"""
        with pytest.raises(ValueError):
            raise ConfigError("test")

    def test_generation_error_caught_by_runtime_error(self) -> None:
        """现有 except RuntimeError 代码能捕获 GenerationError。"""
        with pytest.raises(RuntimeError):
            raise GenerationError("test")


class TestTemplateError:
    """TemplateError 格式化输出测试。"""

    def test_basic_message(self) -> None:
        err = TemplateError("something broke")
        assert "something broke" in str(err)

    def test_with_source_path(self) -> None:
        err = TemplateError("bad syntax", source_path="skills/01.md.tpl")
        assert "skills/01.md.tpl" in str(err)

    def test_with_context_key(self) -> None:
        err = TemplateError("missing value", context_key="HAS_DB")
        assert "HAS_DB" in str(err)

    def test_with_both_source_and_key(self) -> None:
        err = TemplateError(
            "broken", source_path="test.tpl", context_key="MY_KEY",
        )
        msg = str(err)
        assert "test.tpl" in msg
        assert "MY_KEY" in msg

    def test_attributes_stored(self) -> None:
        err = TemplateError("msg", source_path="/a/b.tpl", context_key="K")
        assert err.source_path == "/a/b.tpl"
        assert err.context_key == "K"

    def test_no_source_path(self) -> None:
        err = TemplateError("msg")
        assert err.source_path is None
        assert err.context_key is None

    def test_with_line_number(self) -> None:
        err = TemplateError(
            "bad placeholder", source_path="skills/01.md.tpl", line_number=42,
        )
        assert err.line_number == 42
        msg = str(err)
        assert "line 42" in msg
        assert "skills/01.md.tpl" in msg

    def test_line_number_defaults_to_none(self) -> None:
        err = TemplateError("msg")
        assert err.line_number is None

    def test_all_three_attributes(self) -> None:
        err = TemplateError(
            "broken",
            source_path="test.tpl",
            context_key="MY_KEY",
            line_number=7,
        )
        msg = str(err)
        assert "test.tpl" in msg
        assert "MY_KEY" in msg
        assert "line 7" in msg
        assert err.source_path == "test.tpl"
        assert err.context_key == "MY_KEY"
        assert err.line_number == 7
