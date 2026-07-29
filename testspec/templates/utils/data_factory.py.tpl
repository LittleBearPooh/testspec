# -*- coding: utf-8 -*-
"""测试数据工厂 — 封装复杂的前置数据创建逻辑。

解决的问题:
    - 多个测试需要同一种前置数据（如"已支付的订单"）
    - 数据创建涉及多步操作（创建订单 → 支付 → 确认）
    - 数据需要唯一性保证（并发安全）

用法:
    from utils.data_factory import OrderFactory

    # 创建一个 Pending 状态的订单
    order = OrderFactory.create_pending(http_client)
    # order = {"order_id": "ORD-xxx", "status": "pending", ...}

    # 创建一个已支付的订单（多步操作）
    paid_order = OrderFactory.create_paid(http_client)

    # 清理
    OrderFactory.cancel(http_client, order["order_id"])
"""

from __future__ import annotations

import uuid
from typing import Any

from utils.http_client import HttpClient
from utils.logger import get_logger, safe_copy

logger = get_logger(__name__)


def _unique(prefix: str = "") -> str:
    """生成唯一标识，确保并发安全。"""
    return f"{prefix}{uuid.uuid4().hex[:12]}"


class OrderFactory:
    """订单数据工厂。

    提供常用的订单创建场景，每个方法返回创建结果（dict）。
    调用方负责清理（或配合 cleanup fixture）。
    """

    @staticmethod
    def create_pending(
        client: HttpClient,
        product_id: str = "PROD_TEST_001",
        quantity: int = 1,
        **overrides: Any,
    ) -> dict[str, Any]:
        """创建一个 Pending 状态的订单。

        Args:
            client: HTTP 客户端
            product_id: 商品 ID（需在测试环境存在）
            quantity: 购买数量
            **overrides: 额外参数，覆盖默认值

        Returns:
            创建结果 dict，至少包含 order_id 和 status
        """
        params = {
            "product_id": product_id,
            "quantity": quantity,
            "shipping_address": f"自动化测试地址-{_unique()}",
        }
        params.update(overrides)

        logger.info("OrderFactory: 创建 Pending 订单, params=%s", safe_copy(params))
        resp = client.post("/api/v1/orders", json=params, assert_status=201)
        resp_data = resp.json()
        data = resp_data.get("data", resp_data)

        order_id = data.get("order_id", data.get("id"))
        if order_id is None:
            raise RuntimeError(
                f"订单创建响应中未找到 order_id 或 id 字段，响应体: {data!r}"
            )
        result = {
            "order_id": order_id,
            "status": data.get("status", "pending"),
            "raw": data,
        }
        logger.info("OrderFactory: 订单创建成功, order_id=%s", result["order_id"])
        return result

    @staticmethod
    def create_paid(client: HttpClient, **kwargs: Any) -> dict[str, Any]:
        """创建一个已支付的订单（多步操作：创建 → 支付）。

        Returns:
            dict，包含 order_id, payment_id, status
        """
        order = OrderFactory.create_pending(client, **kwargs)
        order_id = order["order_id"]

        logger.info("OrderFactory: 支付订单 %s", order_id)
        pay_resp = client.post(
            "/api/v1/payments",
            json={
                "order_id": order_id,
                "payment_method": "alipay",
                "amount": order["raw"].get("total_amount", 100),
            },
            assert_status=[200, 201],
        )

        pay_data = pay_resp.json().get("data", {})
        order["payment_id"] = pay_data.get("payment_id")
        order["status"] = pay_data.get("status", "unknown")
        return order

    @staticmethod
    def cancel(client: HttpClient, order_id: str, reason: str = "自动化测试清理") -> None:
        """取消订单（清理用）。"""
        logger.info("OrderFactory: 取消订单 %s", order_id)
        client.put(
            f"/api/v1/orders/{order_id}/cancel",
            json={"reason": reason},
            assert_status=None,
        )


class UserFactory:
    """用户数据工厂。"""

    @staticmethod
    def get_test_token(client: HttpClient, account_name: str = "default") -> str:
        """获取测试用户的 Token。"""
        from config.variable_loader import get_nested as var_get_nested
        account = var_get_nested(f"test_accounts.{account_name}")
        if not account:
            raise ValueError(f"测试账号不存在: test_accounts.{account_name}")

        resp = client.post(
            "/api/v1/auth/login",
            json={
                "username": account.get("username", ""),
                "password": account.get("password", ""),
            },
            assert_status=None,
        )
        token = resp.json().get("data", {}).get("token", "")
        if not token:
            raise RuntimeError(
                f"登录响应中未找到 token，账号: {account_name!r}，"
                f"HTTP {resp.status_code}"
            )
        return token


# =====================================================================
# 在此添加更多工厂类
# =====================================================================
#
# class ProductFactory:
#     @staticmethod
#     def create_test_product(client: HttpClient, **kwargs) -> dict:
#         ...
#
# class InventoryFactory:
#     @staticmethod
#     def set_stock(client: HttpClient, product_id: str, quantity: int) -> None:
#         ...
