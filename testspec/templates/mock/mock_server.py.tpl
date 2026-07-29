# -*- coding: utf-8 -*-
"""Mock 服务配置生成器。

为外部依赖（支付网关、短信服务、物流系统等）提供 Mock 配置和 fixture。

用法:
    # 方式 1：使用 responses 库（轻量级，推荐简单场景）
    from utils.mock_server import mock_response

    @mock_response(
        url="https://pay.example.com/api/charge",
        method="POST",
        status=200,
        json={"code": 0, "transaction_id": "TXN-001"},
    )
    def test_payment_with_mock(http_client):
        ...

    # 方式 2：使用 responses 文件（适用于大量 Mock 场景）
    # 在 mock_responses/ 目录下创建 JSON 文件
    from utils.mock_server import load_mock_responses

    responses = load_mock_responses("payment")
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from functools import wraps

from utils.logger import get_logger

logger = get_logger(__name__)

_MOCK_DIR = Path(__file__).resolve().parent.parent / "mock_responses"


# =====================================================================
# 方式 1：装饰器模式（轻量级 Mock）
# =====================================================================

def mock_response(
    url: str,
    method: str = "GET",
    status: int = 200,
    json_body: Any = None,
    body: str = "",
    headers: dict | None = None,
):
    """Mock 单个 HTTP 响应的装饰器。

    使用 responses 库拦截 HTTP 请求，返回预设响应。

    Args:
        url: 要 Mock 的 URL（支持通配符）
        method: HTTP 方法
        status: 响应状态码
        json_body: 响应 JSON 体
        body: 响应文本体
        headers: 响应头

    示例:
        @mock_response(
            url="https://pay.example.com/api/charge",
            method="POST",
            status=200,
            json_body={"code": 0, "transaction_id": "TXN-001"},
        )
        def test_payment(http_client):
            resp = http_client.post("/api/v1/payments", json={...})
            assert resp.status_code == 200
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                import responses
            except ImportError:
                raise ImportError(
                    "mock_response 需要安装 responses 库: pip install responses"
                )

            with responses.RequestsMock() as rsps:
                rsps.add(
                    method=getattr(responses, method.upper()),
                    url=url,
                    status=status,
                    json=json_body,
                    body=body,
                    headers=headers or {},
                )
                logger.info("Mock 已激活: %s %s → %d", method.upper(), url, status)
                return func(*args, **kwargs)
        return wrapper
    return decorator


# =====================================================================
# 方式 2：文件模式（批量 Mock）
# =====================================================================

def load_mock_responses(name: str) -> list[dict]:
    """从 mock_responses/ 目录加载 Mock 配置。

    Args:
        name: Mock 配置文件名（不含扩展名）
              例如 "payment" → mock_responses/payment.json

    Returns:
        Mock 配置列表，每个条目包含 url/method/status/json
    """
    mock_file = _MOCK_DIR / f"{name}.json"
    if not mock_file.exists():
        raise FileNotFoundError(f"Mock 配置文件不存在: {mock_file}")

    with mock_file.open(encoding="utf-8") as f:
        configs = json.load(f)

    logger.info("加载 Mock 配置: %s (%d 条)", name, len(configs))
    return configs


def apply_mock_responses(configs: list[dict]) -> Any:
    """将 Mock 配置应用到 responses 库。

    Args:
        configs: load_mock_responses() 返回的配置列表

    Returns:
        responses.RequestsMock 实例（需配合 with 使用）

    示例:
        configs = load_mock_responses("payment")
        with apply_mock_responses(configs):
            # 所有 Mock 在此块内生效
            test_something()
    """
    try:
        import responses as resp_lib
    except ImportError:
        raise ImportError("需要安装 responses 库: pip install responses")

    rsps = resp_lib.RequestsMock()
    for cfg in configs:
        method_name = cfg.get("method", "GET").upper()
        method_attr = getattr(resp_lib, method_name, None)
        if method_attr is None:
            raise ValueError(f"不支持的 HTTP 方法: {method_name}")
        rsps.add(
            method=method_attr,
            url=cfg["url"],
            status=cfg.get("status", 200),
            json=cfg.get("json"),
            body=cfg.get("body", ""),
            headers=cfg.get("headers", {}),
        )
    return rsps
