# -*- coding: utf-8 -*-
"""通用 HTTP 客户端封装。

特性：
- 基于 requests.Session，整个测试会话复用同一个 Session（Cookie 自动保持）
- base_url 和 timeout 自动从 variables.yaml 读取
- 默认自动断言响应状态码为 200，支持自定义或关闭
- 自动重试：503 / 超时 / 连接错误自动重试 3 次（指数退避）
- Auth Token 管理：set_auth_token() 自动注入 Authorization 头

assert_status 用法：
    client.get("/api/users")                          # 默认断言 200
    client.post("/api/items", json={...}, assert_status=201)
    client.delete("/api/items/1", assert_status=[200, 204])
    resp = client.get("/api/maybe-404", assert_status=None)  # 关闭断言

Auth 用法：
    client.set_auth_token("Bearer eyJ...")            # 后续请求自动带 Authorization
    client.clear_auth()                               # 清除认证头
"""

from __future__ import annotations

import threading
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config.variable_loader import get as var_get
from utils.logger import get_logger

logger = get_logger(__name__)

# _SENTINEL 是哨兵对象，用于区分"调用方没传 assert_status"和"调用方传了 None"：
#   - 没传 assert_status  → 使用 _SENTINEL → 自动断言 200
#   - assert_status=None  → 显式关闭断言，用例自行处理
#   - assert_status=201   → 断言指定状态码
#   - assert_status=[200,204] → 断言多个可接受状态码之一
_SENTINEL = object()


class HttpClient:
    """通用 JSON HTTP 客户端。

    path 以 / 开头时自动拼接 base_url，否则视为完整 URL 直接使用。
    """

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float | None = None,
    ) -> None:
        # 调用方显式传入 base_url/timeout 时优先使用调用方的值；
        # 不传时从 variables.yaml 读取，保证测试用例无需重复写环境配置。
        # rstrip("/") 统一去掉末尾斜杠，后续拼接 `/api/...` 时不会出现双斜杠。
        self._base_url = (base_url or var_get("base_url", "http://localhost")).rstrip("/")
        self._timeout = timeout if timeout is not None else float(var_get("timeout", 30))

        # Session 会复用 TCP 连接与 Cookie；对登录后再访问接口的测试尤其重要。
        self.session = requests.Session()

        # 自动重试配置：503 / 超时 / 连接错误自动重试 3 次（指数退避 0.5s, 1s, 2s）
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[502, 503, 504],
            allowed_methods=["GET", "HEAD", "OPTIONS", "PUT", "DELETE"],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # 记录最近一次响应，供 conftest 在失败时 attach 到 Allure（线程安全）。
        self._local = threading.local()

    # -------------------------------------------------------------------
    # 线程安全的 last_response 属性
    # -------------------------------------------------------------------

    @property
    def last_response(self) -> requests.Response | None:
        """最近一次 HTTP 响应（线程安全）。"""
        return getattr(self._local, "response", None)

    @last_response.setter
    def last_response(self, val: requests.Response | None) -> None:
        self._local.response = val

    # -------------------------------------------------------------------
    # Auth Token 管理
    # -------------------------------------------------------------------

    def set_auth_token(self, token: str) -> None:
        """设置 Bearer Token，后续所有请求自动注入 Authorization 头。

        Args:
            token: 完整的 token 值，如 "Bearer eyJ..." 或纯 token "eyJ..."
        """
        if not token.lower().startswith("bearer "):
            token = f"Bearer {token}"
        self.session.headers["Authorization"] = token
        logger.debug("Auth token 已设置")

    def set_api_key(self, key: str, header_name: str = "X-API-Key") -> None:
        """设置 API Key 认证。"""
        self.session.headers[header_name] = key
        logger.debug("API Key 已设置 (header: %s)", header_name)

    def clear_auth(self) -> None:
        """清除所有认证头。"""
        self.session.headers.pop("Authorization", None)
        self.session.headers.pop("X-API-Key", None)
        logger.debug("认证头已清除")

    def login(self, username: str, password: str, login_path: str = "/api/v1/auth/login") -> str:
        """通过登录接口获取 token 并自动设置。

        Args:
            username: 用户名
            password: 密码
            login_path: 登录接口路径

        Returns:
            获取到的 token 字符串
        """
        resp = self.post(
            login_path,
            json={"username": username, "password": password},
            assert_status=None,
        )
        if resp.status_code == 200:
            data = resp.json()
            inner = data.get("data")
            token = data.get("token") or data.get("access_token")
            if not token and isinstance(inner, dict):
                token = inner.get("token") or inner.get("access_token")
            if token:
                self.set_auth_token(token)
                return token
        raise RuntimeError(
            f"登录失败: 未获取到 token, HTTP {resp.status_code}, body: {resp.text[:200]}"
        )

    def _build_url(self, path: str) -> str:
        """把调用方传入的 path 转换成最终 URL。"""
        # 以 / 开头表示"相对项目 base_url 的接口路径"。
        if path.startswith("/"):
            return f"{self._base_url}{path}"
        # 否则认为调用方已经传了完整 URL，例如第三方回调地址。
        return path

    def _assert_status(self, resp: requests.Response, assert_status: Any, method: str, path: str) -> None:
        """统一做响应状态码断言。"""
        # assert_status=None 是显式关闭自动断言，留给用例自己判断。
        if assert_status is None:
            return

        # 支持传单个状态码 200，也支持传 [200, 204] 这种多个可接受状态码。
        expected = assert_status if isinstance(assert_status, (list, tuple)) else [assert_status]
        if resp.status_code not in expected:
            body_preview = (resp.text or "")[:500]
            raise AssertionError(
                f"{method.upper()} {path} — 期望状态码 {expected}，实际 {resp.status_code}。"
                f"\n响应体：{body_preview}"
            )

    def request(self, method: str, path: str, assert_status: Any = _SENTINEL, **kwargs: Any) -> requests.Response:
        """统一请求入口。"""
        url = self._build_url(path)

        # _SENTINEL 用于区分"调用方没传 assert_status"和"调用方传了 None"。
        # 没传 => 默认断言 200；传 None => 不断言。
        effective_status = 200 if assert_status is _SENTINEL else assert_status
        logger.info("HTTP %s 开始：url=%s", method.upper(), url)
        try:
            resp = self.session.request(method, url, timeout=self._timeout, **kwargs)
        except Exception:
            logger.exception("HTTP %s 请求异常：url=%s", method.upper(), url)
            raise
        logger.info("HTTP %s 响应：url=%s status=%s", method.upper(), url, resp.status_code)

        # 请求成功拿到响应后再断言状态码，这样失败信息里能带上响应体预览。
        self.last_response = resp
        self._assert_status(resp, effective_status, method, path)
        return resp

    def close(self) -> None:
        """关闭底层 Session，释放连接池资源。"""
        self.session.close()

    def __enter__(self) -> "HttpClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def get(self, path: str, assert_status: Any = _SENTINEL, **kwargs: Any) -> requests.Response:
        return self.request("GET", path, assert_status, **kwargs)

    def post(self, path: str, assert_status: Any = _SENTINEL, **kwargs: Any) -> requests.Response:
        return self.request("POST", path, assert_status, **kwargs)

    def put(self, path: str, assert_status: Any = _SENTINEL, **kwargs: Any) -> requests.Response:
        return self.request("PUT", path, assert_status, **kwargs)

    def patch(self, path: str, assert_status: Any = _SENTINEL, **kwargs: Any) -> requests.Response:
        return self.request("PATCH", path, assert_status, **kwargs)

    def delete(self, path: str, assert_status: Any = _SENTINEL, **kwargs: Any) -> requests.Response:
        return self.request("DELETE", path, assert_status, **kwargs)
