"""TestSpec 生命周期 Hook 注册表。

为 ProjectGenerator 提供可扩展的生命周期事件机制。
支持在生成的关键节点注册自定义回调函数。

独立模块，零项目内依赖。
"""

from __future__ import annotations

import logging
from typing import Any, Callable

__all__ = ["HookRegistry", "VALID_EVENTS"]

_logger = logging.getLogger(__name__)

# 已知的合法事件名称
VALID_EVENTS: frozenset[str] = frozenset({
    "pre_generate",
    "post_section",
    "pre_atomic_move",
    "post_generate",
})


class HookRegistry:
    """生命周期 Hook 注册表。

    为 :class:`~testspec.generator.ProjectGenerator` 提供可扩展的事件机制。
    支持在生成的关键节点注册自定义回调函数。

    已支持的事件:
        - ``pre_generate``: 生成开始前触发。kwargs: ``ctx``
        - ``post_section``: 每个 section 渲染完成后触发。kwargs: ``section``, ``ctx``
        - ``pre_atomic_move``: 原子移动前触发（仅非 dry-run）。kwargs: ``ctx``
        - ``post_generate``: 生成完成后触发（含 dry-run）。kwargs: ``ctx``, ``generated``

    Note:
        HookRegistry 不是线程安全的。如果需要在多线程环境中使用，
        请自行添加外部同步机制（如 ``threading.Lock``）。

    Usage::

        hooks = HookRegistry()
        hooks.register("post_generate", lambda ctx, generated: print(f"生成了 {len(generated)} 个文件"))

        gen = ProjectGenerator(ctx, templates_dir, hook_registry=hooks)
        gen.generate()
    """

    def __init__(self) -> None:
        self._hooks: dict[str, list[Callable[..., None]]] = {}

    def register(self, event: str, callback: Callable[..., None]) -> None:
        """注册一个事件回调。

        Args:
            event: 事件名称（见 :data:`VALID_EVENTS`）
            callback: 回调函数，接受 ``**kwargs`` 参数

        Note:
            不校验 event 名称是否在 VALID_EVENTS 中，允许第三方扩展自定义事件。
        """
        self._hooks.setdefault(event, []).append(callback)

    def unregister(self, event: str, callback: Callable[..., None]) -> None:
        """移除一个事件回调。

        Args:
            event: 事件名称
            callback: 之前注册的回调函数
        """
        hooks = self._hooks.get(event, [])
        try:
            hooks.remove(callback)
        except ValueError:
            pass

    def fire(self, event: str, *, safe: bool = False, **kwargs: Any) -> None:
        """触发事件，按注册顺序调用所有回调。

        Args:
            event: 事件名称
            safe: 若为 True，每个回调的异常被捕获并记录，不中断后续回调。
                  默认 False 保持原有行为（异常向上传播）。
            **kwargs: 传递给回调的关键字参数
        """
        for callback in list(self._hooks.get(event, [])):
            if safe:
                try:
                    callback(**kwargs)
                except Exception as exc:
                    _logger.warning(
                        "Hook callback %r for event %r raised %s: %s",
                        callback, event, type(exc).__name__, exc,
                    )
            else:
                callback(**kwargs)

    def safe_fire(self, event: str, **kwargs: Any) -> None:
        """触发事件，单个回调失败时记录日志并继续（非关键事件使用）。

        等同于 ``fire(event, safe=True, **kwargs)``。
        适用于 ``post_section`` 和 ``post_generate`` 等非关键生命周期事件。

        Args:
            event: 事件名称
            **kwargs: 传递给回调的关键字参数
        """
        self.fire(event, safe=True, **kwargs)

    def has_hooks(self, event: str) -> bool:
        """检查指定事件是否已注册回调。"""
        return bool(self._hooks.get(event))

    def clear(self, event: str | None = None) -> None:
        """清理事件回调。

        Args:
            event: 指定事件名称。为 None 时清空所有事件。
        """
        if event is None:
            self._hooks.clear()
        else:
            self._hooks.pop(event, None)

    def __repr__(self) -> str:
        total = sum(len(v) for v in self._hooks.values())
        return f"HookRegistry({total} hooks, {len(self._hooks)} events)"
