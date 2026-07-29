# -*- coding: utf-8 -*-
"""轮询等待工具 — 异步落库/异步处理的超时轮询。

使用方式：
    from utils.poll_helper import poll_until

    row = poll_until(
        lambda: db.query_one("SELECT * FROM Orders WHERE Id = %s", (order_id,)),
        description=f"订单 {order_id} 落库",
    )
"""
from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")

POLL_TIMEOUT: float = 10.0   # 默认超时 10 秒
POLL_INTERVAL: float = 0.5   # 默认轮询间隔 0.5 秒


def poll_until(
    query_fn: Callable[[], T | None],
    timeout: float = POLL_TIMEOUT,
    interval: float = POLL_INTERVAL,
    backoff: float = 1.5,
    max_interval: float = 2.0,
    description: str = "数据",
) -> T:
    """轮询直到查询函数返回非 None 结果（指数退避）。

    Args:
        query_fn: 无参查询函数，返回 None 表示数据未就绪。
        timeout: 最大等待时间（秒）。
        interval: 初始轮询间隔（秒），后续按 backoff 指数增长。
        backoff: 退避因子，每次轮询间隔乘以此值（默认 1.5）。
        max_interval: 最大轮询间隔（秒），防止间隔过大。
        description: 描述文本，用于超时错误信息。

    Returns:
        查询函数的首次非 None 返回值。

    Raises:
        TimeoutError: 超过 timeout 仍未获取到结果。

    Example:
        >>> row = poll_until(lambda: db.query_one("SELECT ...", (oid,)))
    """
    deadline = time.monotonic() + timeout
    current_interval = interval
    while time.monotonic() <= deadline:
        result = query_fn()
        if result is not None:
            return result
        time.sleep(current_interval)
        current_interval = min(current_interval * backoff, max_interval)
    raise TimeoutError(f"{description}在 {timeout}s 内未就绪")
