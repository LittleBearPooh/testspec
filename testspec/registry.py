"""OptionRegistry — 可注册的选项注册表。

支持运行时动态扩展的选项管理机制，
兼容 dict 接口（items/values/keys/__contains__/__getitem__）。
"""

from __future__ import annotations

from typing import ItemsView, Iterator, KeysView, ValuesView

__all__ = ["OptionRegistry"]


class OptionRegistry:
    """可注册的选项注册表，支持运行时扩展。

    兼容 dict 接口（items/values/keys/__contains__/__getitem__），
    可直接替代原有的硬编码选项字典。

    Usage::

        TEST_TYPES = OptionRegistry("test_types")
        TEST_TYPES.register("1", ("api", "HTTP 接口自动化测试"))
        TEST_TYPES.register("2", ("unit", "单元测试"))

        # 运行时扩展（第三方插件或自定义代码）
        TEST_TYPES.register("5", ("perf", "性能测试"))
    """

    def __init__(self, name: str) -> None:
        self._name = name
        self._items: dict[str, tuple[str, ...]] = {}

    @property
    def name(self) -> str:
        """注册表名称。"""
        return self._name

    def register(self, key: str, value: tuple[str, ...]) -> None:
        """注册一个选项。

        Args:
            key: 选项编号（如 "1", "2"）
            value: 选项元组（第一个元素为标识符，最后一个为描述文本）
        """
        self._items[key] = value

    def unregister(self, key: str) -> None:
        """移除已注册的选项。"""
        self._items.pop(key, None)

    def valid_values(self, index: int = 0) -> frozenset[str]:
        """返回所有选项在指定位置的值的集合。

        Args:
            index: 元组中的位置索引（默认 0，即标识符位置）

        Returns:
            该位置所有值的 frozenset
        """
        return frozenset(v[index] for v in self._items.values())

    # --- dict 兼容接口 ---

    def items(self) -> ItemsView[str, tuple[str, ...]]:
        return self._items.items()

    def values(self) -> ValuesView[tuple[str, ...]]:
        return self._items.values()

    def keys(self) -> KeysView[str]:
        return self._items.keys()

    def get(self, key: str, default: tuple[str, ...] | None = None) -> tuple[str, ...] | None:
        return self._items.get(key, default)

    def __contains__(self, key: object) -> bool:
        return key in self._items

    def __getitem__(self, key: str) -> tuple[str, ...]:
        return self._items[key]

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self) -> Iterator[str]:
        """支持 for 循环遍历已注册键：``for key in registry``。

        迭代顺序与注册顺序一致（Python 3.7+ dict 保持插入顺序）。
        """
        return iter(self._items)

    def __repr__(self) -> str:
        return f"OptionRegistry({self._name!r}, {len(self._items)} options)"
