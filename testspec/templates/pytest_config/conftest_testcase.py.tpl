# -*- coding: utf-8 -*-
"""testcase/ 级 conftest — 提供正式用例目录的共享 fixture。

pytest 会自动发现当前目录及父目录中的 conftest.py。
这里定义的 fixture 可以被 testcase/ 下的测试函数直接声明使用，
例如：def test_x(http_client): ...
"""

from __future__ import annotations

from collections.abc import Generator
from typing import Any

import pytest

{{#IF_HAS_HTTP}}
from utils.http_client import HttpClient


@pytest.fixture(scope="session")
def http_client() -> Generator[HttpClient, None, None]:
    """Session 级通用 HTTP 客户端，复用同一个 requests.Session。

    Yields:
        全局共享的 HttpClient 实例，session 结束时自动关闭连接池。

    Example:
        def test_example(http_client):
            resp = http_client.get("/api/example")
            assert resp.status_code == 200
    """
    client = HttpClient()
    yield client
    client.close()


@pytest.fixture(autouse=True)
def _track_last_response(
    request: pytest.FixtureRequest,
) -> Generator[None, None, None]:
    """每个测试结束后，把 http_client 的最近响应挂到 test item 上。

    懒加载 http_client：只有当测试函数实际声明并使用了 http_client fixture 时，
    才会尝试读取 last_response。这避免了纯单元测试或非 HTTP 测试被迫初始化
    http_client（以及底层的 requests.Session）。

    根级 conftest.py 的 pytest_runtest_makereport 会读取 item._last_response，
    在测试失败时自动把 HTTP 响应 attach 到 Allure 报告。
    """
    yield
    http_client = request.node.funcargs.get("http_client")
    if http_client is not None:
        request.node._last_response = getattr(http_client, "last_response", None)


@pytest.fixture
def cleanup_orders(http_client: HttpClient) -> Generator[list[str], None, None]:
    """自动清理测试创建的订单 — 配合 order_factory 使用。

    在测试函数中将创建的 order_id 追加到此列表，
    fixture 的 teardown 阶段会逐一删除。

    Example:
        def test_create_order(order_factory, cleanup_orders):
            data = order_factory.create()
            cleanup_orders.append(data["order_id"])  # 注册清理
            assert data["status"] == "pending"
    """
    created_ids: list[str] = []
    yield created_ids
    for order_id in created_ids:
        try:
            http_client.delete(
                f"/api/v1/orders/{order_id}",
                assert_status=None,
            )
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning("清理订单失败: %s, 错误: %s", order_id, exc)
{{/IF_HAS_HTTP}}
