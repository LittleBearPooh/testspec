"""TestSpec 交互式向导单元测试。"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from testspec.wizard import (
    ask,
    ask_choice,
    ask_yes_no,
    ask_multi,
    run_wizard,
    confirm_wizard,
)
from testspec.constants import PROJECT_NAME_PATTERN


# ---------------------------------------------------------------------------
# 项目名称正则测试
# ---------------------------------------------------------------------------

class TestProjectNameRegex:
    """PROJECT_NAME_PATTERN 格式校验。"""

    @pytest.mark.parametrize("name", [
        "order-service",
        "api-tests-v2",
        "my-project",
        "a",
        "test123",
    ])
    def test_valid_names(self, name: str) -> None:
        assert PROJECT_NAME_PATTERN.match(name)

    @pytest.mark.parametrize("name", [
        "Order-Service",     # 大写
        "123-tests",         # 数字开头
        "order_service",     # 下划线
        "-leading-dash",     # 连字符开头
        "has space",         # 空格
        "special!char",      # 特殊字符
        "",                  # 空字符串
    ])
    def test_invalid_names(self, name: str) -> None:
        assert not PROJECT_NAME_PATTERN.match(name)


# ---------------------------------------------------------------------------
# ask_yes_no 测试
# ---------------------------------------------------------------------------

class TestAskYesNo:
    """ask_yes_no 交互测试。"""

    @patch("builtins.input", return_value="y")
    def test_yes_input(self, _mock: object) -> None:
        assert ask_yes_no("确认？") is True

    @patch("builtins.input", return_value="n")
    def test_no_input(self, _mock: object) -> None:
        assert ask_yes_no("确认？") is False

    @patch("builtins.input", return_value="")
    def test_default_true(self, _mock: object) -> None:
        assert ask_yes_no("确认？", default=True) is True

    @patch("builtins.input", return_value="")
    def test_default_false(self, _mock: object) -> None:
        assert ask_yes_no("确认？", default=False) is False

    @patch("builtins.input", return_value="yes")
    def test_yes_full(self, _mock: object) -> None:
        assert ask_yes_no("确认？") is True

    @patch("builtins.input", return_value="是")
    def test_chinese_yes(self, _mock: object) -> None:
        assert ask_yes_no("确认？") is True


# ---------------------------------------------------------------------------
# ask 测试
# ---------------------------------------------------------------------------

class TestAsk:
    """ask 交互测试。"""

    @patch("builtins.input", return_value="hello")
    def test_user_input(self, _mock: object) -> None:
        assert ask("请输入") == "hello"

    @patch("builtins.input", return_value="")
    def test_default_value(self, _mock: object) -> None:
        assert ask("请输入", default="world") == "world"

    @patch("builtins.input", return_value="  spaced  ")
    def test_strips_whitespace(self, _mock: object) -> None:
        assert ask("请输入") == "spaced"


# ---------------------------------------------------------------------------
# ask_choice 测试
# ---------------------------------------------------------------------------

class TestAskChoice:
    """ask_choice 交互测试。"""

    OPTIONS = {
        "1": ("api", "API 测试"),
        "2": ("unit", "单元测试"),
    }

    @patch("builtins.input", return_value="2")
    def test_select_second(self, _mock: object) -> None:
        assert ask_choice("选择类型", self.OPTIONS) == "2"

    @patch("builtins.input", return_value="")
    def test_default_selection(self, _mock: object) -> None:
        assert ask_choice("选择类型", self.OPTIONS, default="1") == "1"


# ---------------------------------------------------------------------------
# ask_multi 测试
# ---------------------------------------------------------------------------

class TestAskMulti:
    """ask_multi 交互测试。"""

    OPTIONS = {
        "1": ("api", "API 测试"),
        "2": ("unit", "单元测试"),
        "3": ("e2e", "端到端测试"),
    }

    @patch("builtins.input", return_value="1,3")
    def test_multi_select(self, _mock: object) -> None:
        result = ask_multi("选择", self.OPTIONS)
        assert result == ["api", "e2e"]

    @patch("builtins.input", return_value="2")
    def test_single_select(self, _mock: object) -> None:
        result = ask_multi("选择", self.OPTIONS)
        assert result == ["unit"]

    @patch("builtins.input", return_value="")
    def test_empty_input(self, _mock: object) -> None:
        result = ask_multi("选择", self.OPTIONS)
        assert result == []

    @patch("builtins.input", return_value="1, 2, 99")
    def test_invalid_option_ignored(self, _mock: object) -> None:
        result = ask_multi("选择", self.OPTIONS)
        assert result == ["api", "unit"]


# ---------------------------------------------------------------------------
# run_wizard 完整流程测试
# ---------------------------------------------------------------------------

class TestRunWizard:
    """run_wizard 完整 8 步交互流程测试。"""

    @patch("builtins.input", side_effect=[
        "order-service",     # 步骤 1: 项目名称
        "1",                 # 步骤 2: 测试类型 (api)
        "1",                 # 步骤 3: 语言框架 (python/pytest)
        "y",                 # 步骤 4: 是否使用数据库
        "1",                 # 步骤 4: 数据库类型 (sqlserver)
        "1",                 # 步骤 5: 报告工具 (allure)
        "1",                 # 步骤 6: CI 系统 (github)
        "order,payment",     # 步骤 7: 业务线
        "",                  # 步骤 8: 输出目录 (默认)
        "1",                 # 步骤 8: 文档语言 (zh)
    ])
    def test_full_wizard_flow(self, _mock: object) -> None:
        """完整 8 步向导应返回正确的参数字典。"""
        result = run_wizard()
        assert result["project_name"] == "order-service"
        assert result["test_types"] == ["api"]
        assert result["language"] == "python"
        assert result["framework"] == "pytest"
        assert result["database"] == "sqlserver"
        assert result["report_tool"] == "allure"
        assert result["ci_system"] == "github"
        assert result["business_lines"] == ["order", "payment"]
        assert result["output_dir"] == "./order-service"
        assert result["language_locale"] == "zh"

    @patch("builtins.input", side_effect=[
        "my-api",            # 步骤 1: 项目名称
        "1,3",               # 步骤 2: 测试类型 (api, e2e)
        "1",                 # 步骤 3: 语言框架 (python/pytest)
        "n",                 # 步骤 4: 不使用数据库
        "2",                 # 步骤 5: 报告工具 (html)
        "3",                 # 步骤 6: CI 系统 (none)
        "",                  # 步骤 7: 业务线 (空 → default)
        "./my-output",       # 步骤 8: 输出目录
        "2",                 # 步骤 8: 文档语言 (en)
    ])
    def test_wizard_no_db(self, _mock: object) -> None:
        """不使用数据库时的向导流程。"""
        result = run_wizard()
        assert result["database"] == "none"
        assert result["business_lines"] == ["default"]
        assert result["output_dir"] == "./my-output"
        assert result["language_locale"] == "en"

    @patch("builtins.input", side_effect=EOFError)
    def test_wizard_eof_exits(self, _mock: object) -> None:
        """输入流结束时优雅退出。"""
        with pytest.raises(SystemExit) as exc_info:
            run_wizard()
        assert exc_info.value.code == 0

    @patch("builtins.input", side_effect=KeyboardInterrupt)
    def test_wizard_ctrl_c_exits(self, _mock: object) -> None:
        """Ctrl+C 时优雅退出。"""
        with pytest.raises(SystemExit) as exc_info:
            run_wizard()
        assert exc_info.value.code == 0

    @patch("builtins.input", side_effect=[
        "INVALID",           # 第一次输入无效名称
        "valid-name",        # 第二次输入有效名称
        "1",                 # 步骤 2-8 继续...
        "1",
        "n",
        "1",
        "1",
        "default",
        "",
        "1",
    ])
    def test_wizard_retry_invalid_name(self, _mock: object) -> None:
        """无效项目名称应提示重新输入。"""
        result = run_wizard()
        assert result["project_name"] == "valid-name"


# ---------------------------------------------------------------------------
# confirm_wizard 测试
# ---------------------------------------------------------------------------

class TestConfirmWizard:
    """confirm_wizard 确认交互测试。"""

    _PARAMS = {
        "project_name": "test-proj",
        "test_types": ["api", "e2e"],
        "language": "python",
        "framework": "pytest",
        "database": "sqlserver",
        "report_tool": "allure",
        "ci_system": "github",
        "business_lines": ["order"],
        "output_dir": "./test-proj",
        "language_locale": "zh",
    }

    @patch("builtins.input", return_value="y")
    def test_confirm_yes(self, _mock: object) -> None:
        assert confirm_wizard(self._PARAMS) is True

    @patch("builtins.input", return_value="n")
    def test_confirm_no(self, _mock: object) -> None:
        assert confirm_wizard(self._PARAMS) is False

    @patch("builtins.input", return_value="")
    def test_confirm_default_true(self, _mock: object) -> None:
        """确认提示默认为 True（按回车即确认）。"""
        assert confirm_wizard(self._PARAMS) is True
