"""TestSpec 常量与 OptionRegistry 测试。"""
from __future__ import annotations

import pytest

from testspec.constants import (
    OptionRegistry,
    TEST_TYPES,
    LANG_FRAMEWORKS,
    DB_TYPES,
    REPORT_TOOLS,
    CI_SYSTEMS,
    LANGUAGES,
    VALID_TEST_TYPES,
    VALID_DATABASES,
)


class TestOptionRegistry:
    """OptionRegistry 注册表测试。"""

    def test_register_and_access(self) -> None:
        reg = OptionRegistry("test")
        reg.register("1", ("api", "API 测试"))
        assert reg["1"] == ("api", "API 测试")
        assert "1" in reg
        assert len(reg) == 1

    def test_valid_values(self) -> None:
        reg = OptionRegistry("test")
        reg.register("1", ("api", "API 测试"))
        reg.register("2", ("unit", "单元测试"))
        assert reg.valid_values() == frozenset({"api", "unit"})

    def test_unregister(self) -> None:
        reg = OptionRegistry("test")
        reg.register("1", ("api", "API 测试"))
        reg.register("2", ("unit", "单元测试"))
        reg.unregister("2")
        assert len(reg) == 1
        assert "2" not in reg

    def test_unregister_nonexistent(self) -> None:
        reg = OptionRegistry("test")
        reg.unregister("nonexistent")  # 不应抛异常

    def test_dict_like_interface(self) -> None:
        reg = OptionRegistry("test")
        reg.register("1", ("api", "API 测试"))
        reg.register("2", ("unit", "单元测试"))

        # items()
        items = dict(reg.items())
        assert items == {"1": ("api", "API 测试"), "2": ("unit", "单元测试")}

        # values()
        vals = list(reg.values())
        assert ("api", "API 测试") in vals

        # keys()
        assert set(reg.keys()) == {"1", "2"}

        # get()
        assert reg.get("1") == ("api", "API 测试")
        assert reg.get("99") is None
        assert reg.get("99", "default") == "default"

    def test_repr(self) -> None:
        reg = OptionRegistry("my_registry")
        reg.register("1", ("a", "desc"))
        assert "my_registry" in repr(reg)
        assert "1 options" in repr(reg)

    def test_runtime_extension(self) -> None:
        """运行时注册新选项后，valid_values() 应包含新值。"""
        reg = OptionRegistry("test")
        reg.register("1", ("api", "API 测试"))
        assert "perf" not in reg.valid_values()

        reg.register("5", ("perf", "性能测试"))
        assert "perf" in reg.valid_values()
        assert len(reg) == 2

    def test_iter_over_registry(self) -> None:
        """for key in registry 应按注册顺序遍历所有键。"""
        reg = OptionRegistry("test")
        reg.register("1", ("api", "API 测试"))
        reg.register("2", ("unit", "单元测试"))
        assert list(reg) == ["1", "2"]

    def test_iter_empty_registry(self) -> None:
        """空注册表 iter 应返回空迭代器，不抛异常。"""
        reg = OptionRegistry("empty")
        assert list(reg) == []

    def test_iter_compatible_with_builtin_constructors(self) -> None:
        """注册表可以直接传入 set()、tuple() 等内置构造函数。"""
        reg = OptionRegistry("test")
        reg.register("1", ("api", "API 测试"))
        reg.register("3", ("e2e", "E2E 测试"))
        assert set(reg) == {"1", "3"}
        assert tuple(reg) == ("1", "3")


class TestBuiltinRegistries:
    """内置注册表内容验证。"""

    def test_test_types_has_api(self) -> None:
        assert "api" in VALID_TEST_TYPES

    def test_test_types_has_all_four(self) -> None:
        assert VALID_TEST_TYPES == frozenset({"api", "unit", "integ", "e2e"})

    def test_valid_databases_includes_none(self) -> None:
        assert "none" in VALID_DATABASES

    def test_lang_frameworks_python_pytest(self) -> None:
        lang, fw, _ = LANG_FRAMEWORKS["1"]
        assert lang == "python"
        assert fw == "pytest"

    def test_all_registries_non_empty(self) -> None:
        for reg in (TEST_TYPES, LANG_FRAMEWORKS, DB_TYPES, REPORT_TOOLS, CI_SYSTEMS, LANGUAGES):
            assert len(reg) > 0, f"{reg.name} 不应为空"


class TestCatalogsConsistency:
    """catalogs.py 数据映射表的跨字典一致性验证。"""

    def test_db_port_and_driver_keys_match(self) -> None:
        """DB_PORT_MAP 和 DB_DRIVER_MAP 的键必须完全一致。"""
        from testspec.catalogs import DB_PORT_MAP, DB_DRIVER_MAP
        assert set(DB_PORT_MAP.keys()) == set(DB_DRIVER_MAP.keys())

    def test_db_deps_keys_are_subset_of_port_map(self) -> None:
        """DB_DEPS 的键必须是 DB_PORT_MAP 键的子集（只有需要额外驱动的数据库才在 DB_DEPS 中）。"""
        from testspec.catalogs import DB_PORT_MAP, DB_DEPS
        assert set(DB_DEPS.keys()).issubset(set(DB_PORT_MAP.keys()))

    def test_db_deps_excludes_sqlite_and_none(self) -> None:
        """sqlite 和 none 不需要额外驱动，不应出现在 DB_DEPS 中。"""
        from testspec.catalogs import DB_DEPS
        assert "sqlite" not in DB_DEPS
        assert "none" not in DB_DEPS

    def test_type_desc_map_covers_all_test_types(self) -> None:
        """TYPE_DESC_MAP 应覆盖所有已注册的测试类型。"""
        from testspec.catalogs import TYPE_DESC_MAP
        assert set(TYPE_DESC_MAP.keys()) == VALID_TEST_TYPES
