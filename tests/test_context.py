"""TestSpec 上下文构建测试。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from testspec.context import build_context_from_config, build_context_from_wizard
from testspec.exceptions import ConfigError


# ---------------------------------------------------------------------------
# build_context_from_wizard 测试
# ---------------------------------------------------------------------------

class TestBuildContextFromWizard:
    """build_context_from_wizard 基础测试。"""

    def test_basic_context(self, base_ctx: dict[str, Any]) -> None:
        assert base_ctx["PROJECT_NAME"] == "order-service"
        assert base_ctx["PROJECT_NAME_SNAKE"] == "order_service"
        assert base_ctx["IS_API"] is True
        assert base_ctx["IS_E2E"] is True
        assert base_ctx["HAS_DB"] is True
        assert base_ctx["DB_SQLSERVER"] is True
        assert base_ctx["DB_MYSQL"] is False
        assert base_ctx["HAS_ALLURE"] is True
        assert base_ctx["HAS_HTTP"] is True
        assert base_ctx["CI_GITHUB"] is True
        assert base_ctx["DB_DEFAULT_PORT"] == "1433"

    def test_no_db(self) -> None:
        ctx = build_context_from_wizard(
            project_name="api-only",
            test_types=["api"],
            language="python",
            framework="pytest",
            database="none",
            report_tool="html",
            business_lines=["default"],
            output_dir="./api-only",
        )
        assert ctx["HAS_DB"] is False
        assert ctx["DB_DEFAULT_PORT"] == ""
        assert ctx["DB_SQLSERVER"] is False

    def test_business_lines_list_is_set_literal(self) -> None:
        ctx = build_context_from_wizard(
            project_name="test-proj",
            test_types=["api"],
            language="python",
            framework="pytest",
            database="none",
            report_tool="allure",
            business_lines=["order", "payment"],
            output_dir="./test",
        )
        bl = ctx["BUSINESS_LINES_LIST"]
        assert bl.startswith("{")
        assert bl.endswith("}")
        assert "'order'" in bl
        assert "'payment'" in bl

    def test_invalid_test_type_raises(self, base_wizard_params: dict[str, Any]) -> None:
        with pytest.raises(ValueError, match="无效的测试类型"):
            build_context_from_wizard(**{**base_wizard_params, "test_types": ["invalid"]})

    def test_invalid_database_raises(self, base_wizard_params: dict[str, Any]) -> None:
        with pytest.raises(ValueError, match="无效的数据库类型"):
            build_context_from_wizard(**{**base_wizard_params, "database": "oracle"})

    def test_name_variants(self, base_ctx: dict[str, Any]) -> None:
        assert base_ctx["PROJECT_NAME_PASCAL"] == "OrderService"
        assert base_ctx["PROJECT_NAME_TITLE"] == "Order Service"
        assert base_ctx["PROJECT_DISPLAY_NAME"] == "Order Service"

    def test_derived_values(self, base_ctx: dict[str, Any]) -> None:
        assert base_ctx["CONFIG_CLASS_NAME"] == "OrderServiceConfig"
        assert base_ctx["API_CLASS_NAME"] == "OrderServiceApi"
        assert base_ctx["RUN_SCRIPT_NAME"] == "run_order_service_tests"
        assert base_ctx["AUTH_MODULE_PATH"] == "order_service/client/auth_store.py"


# ---------------------------------------------------------------------------
# build_context_from_config 测试
# ---------------------------------------------------------------------------

class TestBuildContextFromConfig:
    """build_context_from_config 测试。"""

    def test_valid_config(
        self, tmp_path: Path, base_wizard_params: dict[str, Any],
    ) -> None:
        config = tmp_path / "config.json"
        config.write_text(json.dumps(base_wizard_params), encoding="utf-8")
        ctx = build_context_from_config(str(config))
        assert ctx["PROJECT_NAME"] == "order-service"
        assert ctx["IS_API"] is True
        assert ctx["HAS_DB"] is True

    def test_valid_config_with_path_object(
        self, tmp_path: Path, base_wizard_params: dict[str, Any],
    ) -> None:
        config = tmp_path / "config.json"
        config.write_text(json.dumps(base_wizard_params), encoding="utf-8")
        ctx = build_context_from_config(config)
        assert ctx["PROJECT_NAME"] == "order-service"

    def test_invalid_test_type_raises(self, tmp_path: Path) -> None:
        config = tmp_path / "config.json"
        config.write_text(json.dumps({
            "project_name": "x",
            "test_types": ["invalid"],
        }), encoding="utf-8")
        with pytest.raises(ValueError, match="无效的测试类型"):
            build_context_from_config(config)

    def test_invalid_database_raises(self, tmp_path: Path) -> None:
        config = tmp_path / "config.json"
        config.write_text(json.dumps({
            "project_name": "x",
            "test_types": ["api"],
            "database": "oracle",
        }), encoding="utf-8")
        with pytest.raises(ValueError, match="无效的数据库类型"):
            build_context_from_config(config)

    def test_missing_file_raises(self) -> None:
        with pytest.raises(ValueError, match="配置文件不存在"):
            build_context_from_config("/nonexistent/path.json")

    def test_defaults_applied(self, tmp_path: Path) -> None:
        config = tmp_path / "config.json"
        config.write_text(json.dumps({}), encoding="utf-8")
        ctx = build_context_from_config(config)
        assert ctx["PROJECT_NAME"] == "my-project"
        assert ctx["TEST_TYPES"] == ["api"]

    def test_malformed_json_raises(self, tmp_path: Path) -> None:
        config = tmp_path / "config.json"
        config.write_text("{invalid json", encoding="utf-8")
        with pytest.raises(ValueError, match="JSON 格式错误"):
            build_context_from_config(config)

    def test_invalid_project_name_raises(self, tmp_path: Path) -> None:
        config = tmp_path / "config.json"
        config.write_text(json.dumps({
            "project_name": "Invalid_Name!",
        }), encoding="utf-8")
        with pytest.raises(ValueError, match="项目名称格式无效"):
            build_context_from_config(config)

    def test_unknown_keys_warns(self, tmp_path: Path) -> None:
        config = tmp_path / "config.json"
        config.write_text(json.dumps({
            "projcet_name": "typo-test",  # 拼写错误
        }), encoding="utf-8")
        with pytest.warns(UserWarning, match="未知键"):
            build_context_from_config(config)

    def test_json_array_root_raises(self, tmp_path: Path) -> None:
        """JSON 根元素为数组时应抛出 ConfigError。"""
        config = tmp_path / "config.json"
        config.write_text("[1, 2, 3]", encoding="utf-8")
        with pytest.raises(ValueError, match="根元素必须是 JSON 对象"):
            build_context_from_config(config)

    def test_json_string_root_raises(self, tmp_path: Path) -> None:
        """JSON 根元素为字符串时应抛出 ConfigError。"""
        config = tmp_path / "config.json"
        config.write_text('"just a string"', encoding="utf-8")
        with pytest.raises(ValueError, match="根元素必须是 JSON 对象"):
            build_context_from_config(config)


class TestProjectNameValidation:
    """项目名称格式校验测试。"""

    def test_valid_names(self) -> None:
        ctx = build_context_from_wizard(
            project_name="my-api-tests",
            test_types=["api"],
            language="python",
            framework="pytest",
            database="none",
            report_tool="allure",
            business_lines=["default"],
            output_dir="./out",
        )
        assert ctx["PROJECT_NAME"] == "my-api-tests"

    def test_uppercase_name_raises(self) -> None:
        with pytest.raises(ValueError, match="项目名称格式无效"):
            build_context_from_wizard(
                project_name="MyProject",
                test_types=["api"],
                language="python",
                framework="pytest",
                database="none",
                report_tool="allure",
                business_lines=["default"],
                output_dir="./out",
            )

    def test_underscore_name_raises(self) -> None:
        with pytest.raises(ValueError, match="项目名称格式无效"):
            build_context_from_wizard(
                project_name="my_project",
                test_types=["api"],
                language="python",
                framework="pytest",
                database="none",
                report_tool="allure",
                business_lines=["default"],
                output_dir="./out",
            )


class TestBusinessLineValidation:
    """业务线名称校验测试。"""

    def test_invalid_business_line_raises_config_error(self) -> None:
        """无效业务线名称应抛出 ConfigError（而非原始 ValueError）。"""
        with pytest.raises(ConfigError, match="无效的业务线名称"):
            build_context_from_wizard(
                project_name="test-proj",
                test_types=["api"],
                language="python",
                framework="pytest",
                database="none",
                report_tool="allure",
                business_lines=["Invalid_Name"],
                output_dir="./out",
            )

    def test_invalid_business_line_still_caught_by_value_error(self) -> None:
        """ConfigError 继承 ValueError，旧代码 except ValueError 仍可捕获。"""
        with pytest.raises(ValueError, match="无效的业务线名称"):
            build_context_from_wizard(
                project_name="test-proj",
                test_types=["api"],
                language="python",
                framework="pytest",
                database="none",
                report_tool="allure",
                business_lines=["Bad!Name"],
                output_dir="./out",
            )


class TestMissingProjectNameWarning:
    """配置文件缺少 project_name 时应发出警告。"""

    def test_missing_project_name_warns(self, tmp_path: Path) -> None:
        config = tmp_path / "config.json"
        config.write_text(json.dumps({
            "test_types": ["api"],
        }), encoding="utf-8")
        with pytest.warns(UserWarning, match="project_name"):
            build_context_from_config(config)

    def test_present_project_name_no_warning(self, tmp_path: Path) -> None:
        config = tmp_path / "config.json"
        config.write_text(json.dumps({
            "project_name": "my-test",
            "test_types": ["api"],
        }), encoding="utf-8")
        import warnings as _warnings
        with _warnings.catch_warnings():
            _warnings.simplefilter("error")
            ctx = build_context_from_config(config)
        assert ctx["PROJECT_NAME"] == "my-test"


class TestValidateInputsAllDimensions:
    """_validate_inputs 中各维度无效参数的 raise 分支测试。"""

    _BASE = dict(
        test_types=["api"], database="none", project_name="test-proj",
    )

    def test_invalid_language_raises(self) -> None:
        with pytest.raises(ConfigError, match="无效的编程语言"):
            from testspec.context import build_context_from_wizard
            build_context_from_wizard(
                language="ruby", framework="pytest",
                report_tool="allure", ci_system="none", language_locale="zh",
                business_lines=["default"], output_dir="./out",
                **self._BASE,
            )

    def test_invalid_framework_raises(self) -> None:
        with pytest.raises(ConfigError, match="无效的测试框架"):
            from testspec.context import build_context_from_wizard
            build_context_from_wizard(
                language="python", framework="mocha",
                report_tool="allure", ci_system="none", language_locale="zh",
                business_lines=["default"], output_dir="./out",
                **self._BASE,
            )

    def test_invalid_report_tool_raises(self) -> None:
        with pytest.raises(ConfigError, match="无效的报告工具"):
            from testspec.context import build_context_from_wizard
            build_context_from_wizard(
                language="python", framework="pytest",
                report_tool="grafana", ci_system="none", language_locale="zh",
                business_lines=["default"], output_dir="./out",
                **self._BASE,
            )

    def test_invalid_ci_system_raises(self) -> None:
        with pytest.raises(ConfigError, match="无效的 CI 系统"):
            from testspec.context import build_context_from_wizard
            build_context_from_wizard(
                language="python", framework="pytest",
                report_tool="allure", ci_system="jenkins", language_locale="zh",
                business_lines=["default"], output_dir="./out",
                **self._BASE,
            )

    def test_invalid_language_locale_raises(self) -> None:
        with pytest.raises(ConfigError, match="无效的文档语言"):
            from testspec.context import build_context_from_wizard
            build_context_from_wizard(
                language="python", framework="pytest",
                report_tool="allure", ci_system="none", language_locale="fr",
                business_lines=["default"], output_dir="./out",
                **self._BASE,
            )

    def test_empty_business_lines_fallback(self) -> None:
        """空业务线列表应回退为 ['default']。"""
        ctx = build_context_from_wizard(
            project_name="test-proj",
            test_types=["api"],
            language="python",
            framework="pytest",
            database="none",
            report_tool="allure",
            business_lines=[],
            output_dir="./out",
        )
        assert ctx["BUSINESS_LINES_RAW"] == ["default"]


# ---------------------------------------------------------------------------
# 上下文键一致性元测试
# ---------------------------------------------------------------------------


class TestContextConsistency:
    """上下文键一致性元测试 — 防止 TypedDict、dataclass、子构建函数之间的键漂移。"""

    def test_typeddict_keys_match_dataclass_fields(self) -> None:
        """TypedDict ProjectContext 的键集合必须与 _ProjectContextModel 的字段集合完全一致。"""
        import dataclasses
        from testspec.context import ProjectContext, _ProjectContextModel

        typeddict_keys = set(ProjectContext.__annotations__.keys())
        dataclass_keys = {f.name for f in dataclasses.fields(_ProjectContextModel)}

        assert typeddict_keys == dataclass_keys, (
            f"TypedDict 与 dataclass 键集合不一致:\n"
            f"  仅在 TypedDict: {sorted(typeddict_keys - dataclass_keys)}\n"
            f"  仅在 dataclass:  {sorted(dataclass_keys - typeddict_keys)}"
        )

    def test_key_groups_union_equals_typeddict_keys(self) -> None:
        """9 个 _*_KEYS 常量的并集必须恰好等于 TypedDict 的键集合（无多余，无遗漏）。"""
        from testspec.context import (
            ProjectContext,
            _PROJECT_NAME_KEYS,
            _TEST_TYPE_KEYS,
            _LANGUAGE_KEYS,
            _DATABASE_KEYS,
            _REPORT_KEYS,
            _CI_KEYS,
            _LOCALE_KEYS,
            _BUSINESS_KEYS,
            _DERIVED_KEYS,
        )

        all_group_keys = (
            _PROJECT_NAME_KEYS | _TEST_TYPE_KEYS | _LANGUAGE_KEYS
            | _DATABASE_KEYS | _REPORT_KEYS | _CI_KEYS
            | _LOCALE_KEYS | _BUSINESS_KEYS | _DERIVED_KEYS
        )
        typeddict_keys = set(ProjectContext.__annotations__.keys())

        assert all_group_keys == typeddict_keys, (
            f"键分组并集与 TypedDict 不一致:\n"
            f"  仅在分组中:    {sorted(all_group_keys - typeddict_keys)}\n"
            f"  仅在 TypedDict: {sorted(typeddict_keys - all_group_keys)}"
        )

    def test_build_ctx_output_keys_match_typeddict(
        self, base_wizard_params,
    ) -> None:
        """build_context_from_wizard 实际输出的键集合必须与 TypedDict 定义完全一致。"""
        from testspec.context import ProjectContext, build_context_from_wizard

        ctx = build_context_from_wizard(**base_wizard_params)
        built_keys = set(ctx.keys())
        typeddict_keys = set(ProjectContext.__annotations__.keys())

        assert built_keys == typeddict_keys, (
            f"_build_ctx() 输出与 TypedDict 不一致:\n"
            f"  仅在输出:       {sorted(built_keys - typeddict_keys)}\n"
            f"  仅在 TypedDict: {sorted(typeddict_keys - built_keys)}"
        )

    def test_no_silently_empty_string_keys(
        self, base_wizard_params,
    ) -> None:
        """在完整参数下，所有 string 类型的上下文键应有非空值。

        已知例外: SKILL_PREFIX 设计上始终为空（占位符，未来实现）。
        """
        import dataclasses
        from testspec.context import _ProjectContextModel, build_context_from_wizard

        _INTENTIONALLY_EMPTY: frozenset[str] = frozenset({"SKILL_PREFIX"})

        ctx = build_context_from_wizard(**base_wizard_params)
        model = _ProjectContextModel(**ctx)

        silently_empty = [
            f.name
            for f in dataclasses.fields(model)
            if isinstance(getattr(model, f.name), str)
            and not getattr(model, f.name)
            and f.name not in _INTENTIONALLY_EMPTY
        ]

        assert not silently_empty, (
            f"以下字符串字段在完整参数下意外为空: {silently_empty}\n"
            f"（这些字段可能在 _build_ctx() 中未被赋值）"
        )

    def test_projectcontext_total_is_true(self) -> None:
        """ProjectContext 必须使用 total=True，以便静态分析工具强制要求所有字段存在。"""
        from testspec.context import ProjectContext
        assert ProjectContext.__total__ is True


# ---------------------------------------------------------------------------
# JSON 配置字段类型校验测试
# ---------------------------------------------------------------------------


class TestConfigTypeValidation:
    """build_context_from_config JSON 字段类型校验测试。"""

    def test_test_types_string_raises(self, tmp_path: Path) -> None:
        """test_types: 'api'（字符串而非列表）应抛出 ConfigError。"""
        config = tmp_path / "c.json"
        config.write_text(
            json.dumps({"project_name": "p", "test_types": "api"}),
            encoding="utf-8",
        )
        with pytest.raises(ConfigError, match="test_types"):
            build_context_from_config(config)

    def test_business_lines_string_raises(self, tmp_path: Path) -> None:
        """business_lines: 'order'（字符串而非列表）应抛出 ConfigError。"""
        config = tmp_path / "c.json"
        config.write_text(
            json.dumps({"project_name": "p", "business_lines": "order"}),
            encoding="utf-8",
        )
        with pytest.raises(ConfigError, match="business_lines"):
            build_context_from_config(config)

    def test_project_name_int_raises(self, tmp_path: Path) -> None:
        """project_name: 123（整数）应抛出 ConfigError。"""
        config = tmp_path / "c.json"
        config.write_text(json.dumps({"project_name": 123}), encoding="utf-8")
        with pytest.raises(ConfigError, match="project_name"):
            build_context_from_config(config)

    def test_test_types_list_of_ints_raises(self, tmp_path: Path) -> None:
        """test_types: [1, 2]（整数列表）应在列表元素类型校验时抛出 ConfigError。"""
        config = tmp_path / "c.json"
        config.write_text(
            json.dumps({"project_name": "p", "test_types": [1, 2]}),
            encoding="utf-8",
        )
        with pytest.raises(ConfigError, match=r"test_types\[0\]"):
            build_context_from_config(config)

    def test_language_wrong_type_raises(self, tmp_path: Path) -> None:
        """language: 3（整数）应抛出 ConfigError。"""
        config = tmp_path / "c.json"
        config.write_text(
            json.dumps({"project_name": "p", "language": 3}),
            encoding="utf-8",
        )
        with pytest.raises(ConfigError, match="language"):
            build_context_from_config(config)

    def test_correct_types_do_not_raise(self, tmp_path: Path) -> None:
        """正确类型的配置应正常构建上下文，不抛出异常。"""
        config = tmp_path / "c.json"
        config.write_text(json.dumps({
            "project_name": "my-proj",
            "test_types": ["api"],
            "language": "python",
            "business_lines": ["default"],
        }), encoding="utf-8")
        ctx = build_context_from_config(config)
        assert ctx["PROJECT_NAME"] == "my-proj"
