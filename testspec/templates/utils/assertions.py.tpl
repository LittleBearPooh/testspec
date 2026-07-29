# -*- coding: utf-8 -*-
"""Soft Assertion 工具 — 收集所有断言失败后统一报告。

使用方式：
    from utils.assertions import SoftAssertions

    def test_example():
        with SoftAssertions() as soft:
            soft.assert_equal(actual, expected, "field_name")
            soft.assert_true(condition, "description")
        # 退出 with 块时自动报告所有失败
"""
from __future__ import annotations

from typing import Any


class SoftAssertions:
    """收集所有断言失败，退出 with 块时自动报告 — 防止忘记调用 verify()。

    Example:
        >>> with SoftAssertions() as soft:
        ...     soft.assert_equal(data["status"], "pending", "status")
        ...     soft.assert_true(data["amount"] > 0, "amount 应 > 0")
    """

    def __init__(self) -> None:
        self._failures: list[str] = []

    def assert_equal(self, actual: Any, expected: Any, label: str = "") -> None:
        """断言两个值相等。"""
        if actual != expected:
            self._failures.append(
                f"[{label}] 期望={expected!r}, 实际={actual!r}"
            )

    def assert_true(self, condition: bool, message: str) -> None:
        """断言条件为真。"""
        if not condition:
            self._failures.append(message)

    def assert_in(self, member: Any, container: Any, label: str = "") -> None:
        """断言成员在容器中。"""
        if member not in container:
            self._failures.append(f"[{label}] {member!r} 不在 {container!r} 中")

    def assert_approx_equal(
        self, actual: float, expected: float, label: str = "", *, rel: float = 1e-6,
    ) -> None:
        """浮点数近似比较 — 使用容差避免精度问题。"""
        if abs(actual - expected) > max(abs(expected) * rel, 1e-9):
            self._failures.append(
                f"[{label}] 期望≈{expected!r}, 实际={actual!r} (容差 rel={rel})"
            )

    def assert_not_none(self, value: Any, label: str = "") -> None:
        """断言值不为 None。"""
        if value is None:
            self._failures.append(f"[{label}] 值为 None，期望非空")

    def verify(self) -> None:
        """手动报告所有收集的断言失败（也可通过 with 块自动触发）。"""
        if self._failures:
            failures_text = "\n".join(f"  - {f}" for f in self._failures)
            raise AssertionError(
                f"共 {len(self._failures)} 项断言失败:\n{failures_text}"
            )

    def __enter__(self) -> SoftAssertions:
        return self

    def __exit__(self, exc_type: type | None, *_: Any) -> None:
        # 只有在 with 块内没有抛出其他异常时才自动 verify
        if self._failures and exc_type is None:
            self.verify()
