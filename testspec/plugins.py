"""TestSpec 插件发现机制。

通过 importlib.metadata entry_points 加载第三方 SectionRenderer 插件。
Python 3.9+ 的 entry_points(group=...) API 用于插件发现。

Entry point 格式（在插件包的 pyproject.toml 中声明）::

    [project.entry-points."testspec.sections"]
    my_section = "my_package.module:MySectionClass"
"""

from __future__ import annotations

import logging
from importlib.metadata import entry_points
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .sections import BaseSectionRenderer

__all__ = ["discover_plugins", "load_plugin_renderers"]

_logger = logging.getLogger(__name__)


def discover_plugins(group: str = "testspec.sections") -> list[type]:
    """发现并返回注册在指定 entry_points 组下的 Section Renderer 类。

    加载失败的插件被记录为 WARNING 后跳过，不影响其他插件的加载。

    Args:
        group: entry_points 分组名称（默认 ``"testspec.sections"``）

    Returns:
        成功加载的类列表（可能为空）
    """
    discovered: list[type] = []
    eps = entry_points(group=group)
    # 延迟导入放在循环外：Python 会缓存已导入模块，但放在循环内影响可读性
    from .sections import BaseSectionRenderer
    for ep in eps:
        try:
            cls = ep.load()
            # 验证加载的对象是 BaseSectionRenderer 的子类
            if not (isinstance(cls, type) and issubclass(cls, BaseSectionRenderer)):
                _logger.warning(
                    "插件 entry_point %r 加载的 %r 不是 BaseSectionRenderer 子类，已跳过",
                    ep.name, getattr(cls, "__name__", cls),
                )
                continue
            discovered.append(cls)
            _logger.debug("已加载插件 Section: %s (%s)", ep.name, ep.value)
        except Exception as exc:
            _logger.warning(
                "加载插件 entry_point %r 失败: %s: %s",
                ep.name, type(exc).__name__, exc,
            )
    return discovered


def load_plugin_renderers(group: str = "testspec.sections") -> list[BaseSectionRenderer]:
    """发现插件并返回实例化的 SectionRenderer 列表。

    每个发现的类会被无参实例化。实例化失败的插件被记录为 WARNING 后跳过。

    Args:
        group: entry_points 分组名称

    Returns:
        实例化的 BaseSectionRenderer 列表（可能为空）
    """
    renderers: list[BaseSectionRenderer] = []
    for cls in discover_plugins(group=group):
        try:
            renderers.append(cls())
        except Exception as exc:
            _logger.warning(
                "实例化插件 Section %r 失败: %s: %s",
                cls.__name__, type(exc).__name__, exc,
            )
    return renderers
