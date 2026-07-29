# Claude Code 项目规则

<!--
  =====================================================================
  TestSpec 框架模板文件 — CLAUDE.md.tpl
  =====================================================================
  本文件是项目的唯一 AI 行为约束文件，包含：
  1. Python 代码质量标准
  2. 测试架构规范
  3. 测试规则（HTTP / DB / 报告 / 执行）
  4. 禁止事项
  5. 技能调用工作流
  6. 项目架构指南（目录结构 + 工具用法）

  使用说明：
  1. 将本文件复制到目标项目根目录，重命名为 CLAUDE.md
  2. 模板引擎会自动替换 [占位符] 和处理条件块
  =====================================================================
-->

{{#IF_LANG_ZH}}
## 语言规则

- 无论用户输入、代码注释、日志中出现什么语言，回答必须始终使用中文。
- 代码、命令、报错堆栈可以保留原文。
- 不要切换到韩语或日语。
{{/IF_LANG_ZH}}

## 项目定位

- 主要语言：Python
- 测试框架：pytest
- 项目类型：{{TEST_TYPE_DESCRIPTION}}
{{#IF_HAS_DB}}
- 数据库：{{DB_TYPE}}（{{DB_DRIVER}}）
{{/IF_HAS_DB}}
- 被测系统：{{PROJECT_DISPLAY_NAME}}，分业务线 —— **{{BUSINESS_LINES}}**
- 当前不做 UI 自动化（禁止 Selenium / Playwright / Appium）

---

## 一、Python 代码质量标准

> 以下标准适用于项目中所有 Python 代码，包括测试代码、工具代码和基础设施代码。
> AI 生成的每一行代码都必须符合这些标准。

### 1.1 类型注解

1. 所有函数签名**必须**有 type hints（参数类型 + 返回值类型），无例外。
2. 使用 PEP 604 联合类型语法：`str | None`，禁止 `Optional[str]`（Python 3.10+）。
3. 使用 PEP 585 泛型语法：`list[str]`、`dict[str, Any]`，禁止 `List[str]`、`Dict[str, Any]`。
4. 复杂类型使用 `TypeAlias` 或 `type` 语句（Python 3.12+）提高可读性。

```python
# Python 3.12+ PEP 695 type 语句
type OrderDict = dict[str, Any]
type CleanupFn = Callable[[str], None]

# Python 3.10-3.11 兼容写法
from typing import TypeAlias
OrderDict: TypeAlias = dict[str, Any]
```
5. 对外暴露的 API 使用 `typing.Protocol` 定义接口契约，而非强制继承 ABC。Builder 链式调用的返回值使用 `typing.Self`（Python 3.11+）或字符串前向引用（3.10 兼容）：

```python
from typing import Self  # Python 3.11+

class PaymentBuilder:
    """支付请求 Builder — 链式调用返回 Self。"""

    def with_amount(self, amount: float) -> Self:
        """设置金额，返回自身以支持链式调用。"""
        self._data["amount"] = amount
        return self

    def with_method(self, method: str) -> Self:
        self._data["payment_method"] = method
        return self
```

```python
# ✓ 正确
def query_order(order_id: str, *, timeout: float = 10.0) -> dict[str, Any] | None:
    ...

# ✗ 错误
def query_order(order_id, timeout=10.0):
    ...
```

### 1.2 Docstring 规范

6. 所有 public 函数/类**必须**有 Google 风格 docstring，包含：
   - 一行摘要
   - `Args:` 参数说明（含类型和默认值）
   - `Returns:` 返回值说明
   - `Raises:` 异常说明（如有）
   - `Example:` 使用示例（对外 API 函数）
7. 私有函数（`_` 前缀）至少有一行摘要 docstring。
8. 模块级 docstring 说明模块职责和使用方式。

```python
def poll_until(
    query_fn: Callable[[], T | None],
    timeout: float = 10.0,
    interval: float = 0.2,
    backoff: float = 1.5,
    max_interval: float = 2.0,
) -> T:
    """轮询直到查询函数返回非 None 结果（指数退避）。

    Args:
        query_fn: 无参查询函数，返回 None 表示数据未就绪。
        timeout: 最大等待时间（秒）。
        interval: 初始轮询间隔（秒），后续按 backoff 指数增长。
        backoff: 退避因子（默认 1.5）。
        max_interval: 最大轮询间隔（秒）。

    Returns:
        查询函数的首次非 None 返回值。

    Raises:
        TimeoutError: 超过 timeout 仍未获取到结果。

    Example:
        >>> order = poll_until(lambda: db.query_one("SELECT ...", (oid,)))
    """
```

### 1.3 命名与格式

9. 变量/函数 `snake_case`，类 `PascalCase`，常量 `UPPER_SNAKE_CASE`，私有成员 `_` 前缀。
10. 字符串格式化统一使用 f-string，禁止 `.format()` 和 `%` 格式化。
11. 文件路径操作统一使用 `pathlib.Path`，禁止 `os.path`。
12. import 顺序：标准库 → 第三方库 → 本项目模块，各组之间空一行，组内按字母排序。
13. 函数长度：单个函数不超过 50 行（不含 docstring 和注释）；超过时提取 helper。
14. 禁止魔法数字：所有非 0/1 的数值常量必须命名（`MAX_RETRY = 3`、`DEFAULT_TIMEOUT = 30`）。

### 1.4 错误处理

15. 使用自定义异常类（继承自项目基类 `TestInfraError`），禁止裸 `except Exception:`。
16. 所有 `except` 块必须指定具体异常类型，或附带 `logger.exception()` 记录完整堆栈。
17. 资源清理使用 `try/finally` 或上下文管理器（`with` 语句），禁止依赖 GC。
18. 断言失败时**必须**携带完整上下文（期望值 + 实际值 + 关键参数）：

```python
# ✓ 正确 — 上下文完整
assert order["Status"] == expected_status, (
    f"订单状态不符: order_id={order_id}, "
    f"期望={expected_status}, 实际={order['Status']}"
)

# ✗ 错误 — 无上下文
assert order["Status"] == expected_status
```

19. 多资源并行清理时使用 `ExceptionGroup`（Python 3.11+）收集所有失败：

```python
def cleanup_all(resource_ids: list[str], client: HttpClient) -> None:
    """并行清理多个资源，收集所有失败。"""
    errors: list[Exception] = []
    for rid in resource_ids:
        try:
            client.delete(f"/api/resources/{rid}", assert_status=None)
        except Exception as exc:
            errors.append(exc)
            logger.warning("清理资源 %s 失败: %s", rid, exc)
    if errors:
        raise ExceptionGroup("部分资源清理失败", errors)
```

### 1.5 数据结构

20. 结构化数据优先使用 `dataclasses.dataclass`，而非裸 dict：

```python
from dataclasses import dataclass, field

@dataclass(frozen=True)
class OrderPayload:
    """创建订单请求体 — frozen 确保不可变。"""
    product_id: str
    quantity: int = 1
    shipping_address: str = ""
    remark: str = field(default_factory=lambda: f"auto-{uuid4().hex[:8]}")

    def to_dict(self) -> dict[str, Any]:
        """转换为 API 请求 dict。"""
        return asdict(self)
```

21. API 响应的结构化解析使用 `TypedDict`（运行时不强制，但 IDE 和 mypy 受益）：

```python
from typing import TypedDict

class OrderResponse(TypedDict):
    """创建订单响应 data 字段结构。"""
    order_id: str
    status: str
    total_amount: float
    created_at: str
```

22. 有限集合的常量使用 `enum.Enum`（`str` mixin 确保与模板引擎兼容）：

```python
from enum import Enum

class OrderStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    SHIPPED = "shipped"
    CANCELLED = "cancelled"

# 用法
assert data["status"] == OrderStatus.PENDING  # 可读性优于 "pending"
```

23. 简单不可变记录使用 `NamedTuple`：

```python
from typing import NamedTuple

class DbConfig(NamedTuple):
    host: str
    port: int
    user: str
    name: str
```

**数据结构选型决策**：

| 场景 | 推荐方式 | 理由 |
|------|---------|------|
| API 请求体（需要 to_dict） | `@dataclass` | 可变、支持默认值、`asdict()` 转换 |
| API 请求体（不可变） | `@dataclass(frozen=True)` | 线程安全、hashable |
| API 请求体（大量实例化） | `@dataclass(frozen=True, slots=True)` | Python 3.10+，内存优化 |
| API 响应结构（只做类型标注） | `TypedDict` | 运行时零开销、IDE 补全 |
| 响应结构 + 运行时校验 | Pydantic `BaseModel` | 自动类型转换和约束校验 |
| 有限枚举值 | `Enum(str, Enum)` | 可读性、IDE 补全、防拼写错误 |
| 简单不可变记录（无方法） | `NamedTuple` | 轻量、可解包、可索引 |
| 配置项（多层嵌套） | `dict` + `TypedDict` 标注 | 灵活、配合 variable_loader |

### 1.6 上下文管理器与资源管理

24. 需要 setup/teardown 的资源使用 `contextlib.contextmanager` 或自定义 `__enter__`/`__exit__`：

```python
from contextlib import contextmanager

@contextmanager
def temp_order(client: HttpClient, **kwargs: Any):
    """创建临时订单，退出 with 块时自动取消。"""
    data = client.post("/api/v1/orders", json=kwargs, assert_status=201).json()["data"]
    order_id = data["order_id"]
    try:
        yield data
    finally:
        client.put(f"/api/v1/orders/{order_id}/cancel",
                   json={"reason": "测试清理"}, assert_status=None)
        logger.info("已清理订单: %s", order_id)

# 用法
with temp_order(client, product_id="PROD_001") as order:
    resp = client.get(f"/api/v1/orders/{order['order_id']}")
    assert resp.json()["data"]["status"] == "pending"
# 退出 with 块时自动取消
```

25. 禁止在 `__del__` 中做资源清理——Python GC 时机不可预测。

### 1.7 functools 工具函数

26. 计算开销大的纯函数使用 `@functools.lru_cache` 或 `@functools.cached_property`：

```python
from functools import lru_cache, cached_property

class TestConfig:
    @cached_property
    def base_url(self) -> str:
        """首次访问时从配置加载，后续直接返回缓存值。"""
        return var_get("base_url", "http://localhost")

@lru_cache(maxsize=32)
def get_auth_token(account: str) -> str:
    """缓存 token，避免重复登录。"""
    ...
```

27. 需要固定部分参数的回调使用 `functools.partial`：

```python
from functools import partial

# 创建预配置的 factory
create_vip_order = partial(order_factory.create, quantity=10, remark="VIP")
```

### 1.8 日志最佳实践

28. 日志使用延迟求值（lazy formatting），避免不必要的字符串格式化：

```python
# ✓ 正确 — 延迟求值，日志级别被过滤时不会执行格式化
logger.debug("订单详情: order_id=%s, status=%s", order_id, status)

# ✗ 错误 — 立即求值，即使 debug 被禁用也会执行 f-string
logger.debug(f"订单详情: order_id={order_id}, status={status}")
```

29. 异常日志使用 `logger.exception()` 自动附带堆栈：

```python
try:
    resp = client.post("/api/orders", json=payload)
except requests.RequestException:
    logger.exception("创建订单失败: payload=%s", payload)
    raise
```

30. 敏感信息脱敏 — 使用项目 logger 的自动脱敏功能：

```python
# logger.py 已配置脱敏过滤器，以下字段自动替换为 ***
logger.info("用户登录: username=%s, password=%s", username, password)
# 输出: 用户登录: username=admin, password=***
```

### 1.9 高级 Python 模式

> 以下模式适用于需要类型安全复用、精确多态标注或复杂基础设施封装的场景。
> AI 应在合适的场景中主动使用这些模式，而非默认用最简单的实现。

31. **泛型 Factory**：当 Factory 需要服务多种实体类型时，使用 `Generic[T]`：

```python
from typing import Generic, TypeVar, Any

T = TypeVar("T")

class BaseFactory(Generic[T]):
    """泛型数据工厂基类 — 子类指定具体实体类型。"""

    _defaults: dict[str, Any]
    _endpoint: str

    def build(self, **overrides: Any) -> dict[str, Any]:
        """构建请求体，overrides 覆盖默认值。"""
        return {**self._defaults, **overrides}

    def create(self, **overrides: Any) -> dict[str, Any]:
        """构建并发送创建请求，返回响应 data。"""
        resp = self._client.post(self._endpoint, json=self.build(**overrides), assert_status=201)
        return resp.json()["data"]


class OrderFactory(BaseFactory["OrderResponse"]):
    """订单工厂 — 泛型实例化。"""
    _endpoint = "/api/v1/orders"
    _defaults = {"product_id": "PROD_TEST_001", "quantity": 1}
```

32. **`typing.overload` 精确标注多态返回值**：HttpClient 的 `assert_status` 参数有不同行为时，用 overload 标注：

```python
from typing import overload
import requests

class HttpClient:
    @overload
    def get(self, path: str, *, assert_status: None = ...) -> requests.Response: ...
    @overload
    def get(self, path: str, *, assert_status: int | list[int] = 200) -> requests.Response: ...

    def get(self, path: str, *, assert_status: int | list[int] | None = 200) -> requests.Response:
        """发送 GET 请求。assert_status=None 关闭自动断言。"""
        ...
```

33. **装饰器工厂模式**：自定义 retry、timing 装饰器用于测试基础设施：

```python
import functools
import time
from collections.abc import Callable
from typing import Any

def retry(max_attempts: int = 3, delay: float = 1.0) -> Callable:
    """重试装饰器 — 适用于不稳定操作的自动重试。

    Args:
        max_attempts: 最大重试次数。
        delay: 重试间隔（秒）。

    Returns:
        装饰后的函数，失败时自动重试。
    """
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            for attempt in range(1, max_attempts + 1):
                try:
                    return fn(*args, **kwargs)
                except Exception as exc:
                    if attempt == max_attempts:
                        raise
                    logger.warning("第 %d 次尝试失败: %s, %.1fs 后重试", attempt, exc, delay)
                    time.sleep(delay)
        return wrapper
    return decorator

# 用法
@retry(max_attempts=3, delay=2.0)
def flaky_api_call() -> dict[str, Any]:
    """不稳定接口 — 自动重试最多 3 次。"""
    return client.get("/api/unstable").json()
```

34. **`dataclass` 高级用法** — `__post_init__` 校验 + `kw_only` 强制关键字参数：

```python
from dataclasses import dataclass, field

@dataclass(kw_only=True)
class PaginationParams:
    """分页查询参数 — kw_only 强制关键字调用，防止参数顺序混淆。"""

    page: int = 1
    page_size: int = 20
    sort_by: str = "created_at"
    sort_order: str = "desc"

    def __post_init__(self) -> None:
        """初始化后自动校验参数约束。"""
        if self.page < 1:
            raise ValueError(f"page 必须 >= 1, 收到 {self.page}")
        if not 1 <= self.page_size <= 100:
            raise ValueError(f"page_size 必须在 1-100 之间, 收到 {self.page_size}")

# 用法 — 必须使用关键字参数
params = PaginationParams(page=2, page_size=50)
# PaginationParams(2, 50)  ← TypeError，强制关键字
```

35. **`Protocol` 接口契约**：测试基础设施中的可替换组件使用 Protocol 定义接口：

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class DataCleaner(Protocol):
    """数据清理器接口 — 任何实现 clean 方法的类均可替代。"""

    def clean(self, resource_id: str) -> None: ...


class OrderCleaner:
    """通过 API 清理订单。"""

    def __init__(self, client: HttpClient) -> None:
        self._client = client

    def clean(self, resource_id: str) -> None:
        self._client.delete(f"/api/v1/orders/{resource_id}", assert_status=None)


class DatabaseCleaner:
    """通过数据库直接清理。"""

    def clean(self, resource_id: str) -> None:
        db.execute("DELETE FROM Orders WHERE Id = %s", (resource_id,))

# 两种 cleaner 均满足 DataCleaner Protocol，可互换使用
def register_cleanup(cleaner: DataCleaner, resource_id: str) -> None:
    cleaner.clean(resource_id)
```

36. **`TypedDict` + `Required/NotRequired` 精确标注 API 响应**：

```python
from typing import TypedDict
from typing_extensions import Required, NotRequired  # Python 3.11+ 可直接从 typing 导入

class PaginatedResponse(TypedDict):
    """分页响应结构 — Required 标记必填字段，NotRequired 标记可选字段。"""

    total: Required[int]
    items: Required[list[dict[str, Any]]]
    next_cursor: NotRequired[str | None]
    prev_cursor: NotRequired[str | None]


class OrderDetail(TypedDict):
    """订单详情响应 data 字段。"""

    order_id: Required[str]
    status: Required[str]
    total_amount: Required[float]
    remark: NotRequired[str]
    cancelled_at: NotRequired[str | None]
```

---

## 二、测试架构规范

> 以下规范定义测试代码的组织方式和设计模式，确保测试代码可维护、可扩展。

### 2.1 AAA 模式

37. 每个测试函数**严格**遵循 Arrange-Act-Assert 三段式，用空行 + 注释分隔：

```python
def test_create_order_returns_201(http_client, order_factory):
    # --- Arrange ---
    payload = order_factory.build(quantity=2)

    # --- Act ---
    resp = http_client.post("/api/v1/orders", json=payload, assert_status=201)
    data = resp.json()["data"]

    # --- Assert ---
    assert data["order_id"] is not None
    assert data["status"] == "pending"
```

38. 当使用 `allure.step` 时，step 块天然充当 AAA 分段标记，无需额外注释。

### 2.2 Fixture 层级与 Scope

39. conftest.py 层级：
    - `conftest.py`（根级）：Allure 环境信息、失败自动 attach
    - `testcase/conftest.py`：`http_client`（session 级）、`cleanup_orders`（function 级）
    - `testcase/<业务线>/conftest.py`：业务线特有 fixture（前置数据、特殊 client）

40. Fixture scope 决策：

    | 资源类型 | 推荐 scope | 理由 |
    |---------|-----------|------|
    | HTTP client、DB 连接 | `session` | 无状态，复用连接池 |
    | 测试数据（创建/清理） | `function` | 有副作用，必须隔离 |
    | 只读配置（base_url） | `session` | 全局不变 |
    | 业务线前置数据 | `module` 或 `function` | 视数据是否跨用例共享 |

41. 有状态 fixture 禁止使用 `session` scope，否则并发执行时会数据污染。

### 2.3 设计模式

42. **Factory Fixture + Builder Pattern**：测试数据通过 factory fixture 生成，复杂请求体使用 Builder 类（链式调用）构建，不在测试函数内硬编码大段 dict：

```python
@pytest.fixture
def order_factory(http_client: HttpClient) -> OrderFactory:
    """订单数据工厂 — 每个测试获取独立实例。"""
    return OrderFactory(http_client)

class OrderFactory:
    """订单 Builder — 链式调用构建请求体。"""

    def __init__(self, client: HttpClient) -> None:
        self._client = client
        self._defaults: dict[str, Any] = {
            "product_id": "PROD_TEST_001",
            "quantity": 1,
            "shipping_address": f"自动化地址-{uuid4().hex[:8]}",
        }

    def build(self, **overrides: Any) -> dict[str, Any]:
        """构建请求体，overrides 覆盖默认值。"""
        return {**self._defaults, **overrides}

    def create(self, **overrides: Any) -> dict[str, Any]:
        """构建并发送创建请求，返回响应 data。"""
        resp = self._client.post(
            "/api/v1/orders", json=self.build(**overrides), assert_status=201,
        )
        return resp.json()["data"]
```

43. **Service Object**：业务操作封装到 `{{PROJECT_NAME_SNAKE}}/client/` 下的 Service 类，测试函数不直接拼 URL 和参数。

44. **Strategy Pattern**：当同一个接口有多种断言策略时（如按角色、按环境），用策略类而非 if/else 分支：

```python
class AssertionStrategy(Protocol):
    def verify(self, response: dict[str, Any]) -> None: ...

class AdminAssertion:
    def verify(self, response: dict[str, Any]) -> None:
        assert response["data"]["admin_only_field"] is not None

class UserAssertion:
    def verify(self, response: dict[str, Any]) -> None:
        assert "admin_only_field" not in response["data"]
```

### 2.4 数据生命周期

45. 每个测试函数必须实现"准备 → 执行 → 验证 → 清理"完整生命周期。
46. 清理注册**必须在断言之前**（确保断言失败时也能清理）。
47. 使用唯一标识（UUID / 时间戳）确保测试数据不冲突。
48. 优先使用 fixture 的 `yield` 模式做清理，避免手动 `try/finally`：

```python
@pytest.fixture
def created_order(order_factory: OrderFactory, cleanup_orders: list[str]):
    """创建测试订单并在测试后自动清理。"""
    data = order_factory.create()
    cleanup_orders.append(data["order_id"])  # 注册清理（在断言之前！）
    yield data
```

### 2.5 pytest-xdist 并发安全

49. 使用 `pytest-xdist` 并行执行时，测试数据和资源必须 worker-safe：
    - 测试数据使用 `uuid4()` 确保唯一性，禁止硬编码固定 ID
    - 共享文件写入使用 `filelock` 避免竞态条件
    - `session` scope fixture 在每个 xdist worker 中独立初始化，不跨 worker 共享
    - 数据库测试数据使用唯一前缀（如 `worker_id = os.environ.get("PYTEST_XDIST_WORKER", "gw0")`）

```python
import os
from uuid import uuid4

@pytest.fixture(scope="session")
def worker_id() -> str:
    """当前 xdist worker 标识，单进程时返回 'main'。"""
    return os.environ.get("PYTEST_XDIST_WORKER", "main")

@pytest.fixture
def unique_name(worker_id: str) -> str:
    """生成 worker-safe 的唯一名称。"""
    return f"test-{worker_id}-{uuid4().hex[:8]}"
```

---

## 三、测试规则

### 3.1 目录与文件规范

50. 测试用例按业务线放在 `testcase/<业务线>/` 子目录；各业务线目录名与被测模块保持一致。
51. 测试函数命名使用动宾结构 `test_<动作>_<期望结果>`，例如 `test_CreateOrder_ReturnsOrderNumber`；e2e 用例可用大驼峰描述场景，contract/smoke 用例优先 `test_should_xxx_when_yyy`。
{{#IF_HAS_HTTP}}
52. 登录、token、base_url、headers 放到 fixture 或 api_client，不在测试函数里硬编码。
53. 接口封装清单：核心业务 → `{{PROJECT_NAME_SNAKE}}/client/`；通用 HTTP → `utils/http_client.py`；数据库 → `utils/db_client.py`。
{{/IF_HAS_HTTP}}
{{#IF_HAS_DB}}
54. 数据库操作封装优先放在 `utils/db_client.py`。
{{/IF_HAS_DB}}
55. 公共断言写在测试模块内部或 `utils/` 下合适的辅助文件；不要主动创建 `utils/assertions.py` 除非确有需要。
56. 测试数据放在 `data/` 目录（yaml/json/excel 子目录）。

### 3.2 通用测试约束

57. 禁止依赖测试执行顺序。
58. 禁止无条件 `time.sleep`（固定等待）；异步结果必须使用带超时的轮询循环（`while time.monotonic() <= deadline`），轮询循环内的间隔 sleep 是允许的。
59. 测试数据必须唯一，避免并发执行冲突。
60. 测试完成后必须有清理策略。
61. E2E 用例默认直接执行，无需环境变量开关；不得在 E2E 用例上添加 `skipif` 环境变量门控。
62. 日志统一使用 `from utils.logger import get_logger`（不存在任何旧版兼容入口）。
63. 新增测试文件后，必须同步更新 `{{RUN_SCRIPT_NAME}}.ps1` / `{{RUN_SCRIPT_NAME}}.sh`：smoke/contract 用例追加到分组 1 参数列表，e2e 用例新增独立分组块（直接调用 Invoke-PytestGroup），分组编号顺序递增。
64. 新增 `pytest.mark` 标记前，先在 `pytest.ini` 的 `markers` 节中声明；`--strict-markers` 会在运行时拒绝未注册的标记。
65. 参数化测试**必须**提供 `ids` 参数，让测试报告可读：

```python
# ✓ 正确 — 有 ids
@pytest.mark.parametrize("case", read_yaml("yaml/cases.yaml"), ids=lambda c: c["id"])

# ✗ 错误 — 无 ids，报告显示 test[0], test[1], ...
@pytest.mark.parametrize("case", read_yaml("yaml/cases.yaml"))
```

{{#IF_HAS_HTTP}}
### 3.3 HTTP 接口规则

66. 接口测试必须包含有效断言，不能只判断 status_code。
67. 外部第三方接口默认 mock。
{{/IF_HAS_HTTP}}

{{#IF_HAS_DB}}
### 3.4 数据库测试规则

68. 写接口必须考虑数据库校验。
69. 失败场景必须校验不应落库。
70. 查询接口必须校验分页、筛选、排序。
71. 更新接口必须校验变更字段和未变更字段。
72. 删除接口必须区分软删除和物理删除。
{{/IF_HAS_DB}}

{{#IF_HAS_ALLURE}}
### 3.5 Allure 报告规则

73. 每个 `with allure.step(...)` 块内**必须**用 `allure.attach(...)` 输出该步骤的关键请求参数和响应结果（不限于失败时）：下单/前置步骤 attach 关键 ID；发请求步骤 attach 请求参数（脱敏）；校验步骤 attach 响应关键字段或响应 dict。
74. `@allure.title` 必须是每个测试函数的**第一个装饰器**。
{{/IF_HAS_ALLURE}}
{{#IF_NOT_HAS_ALLURE}}
### 3.5 报告规则（pytest-html）

- 测试报告可使用 `pytest-html` 生成 HTML 报告：`pytest --html=reports/report.html --self-contained-html`
- 使用描述性的测试函数名和 docstring 替代 `@allure.title`。
{{/IF_NOT_HAS_ALLURE}}

---

## 四、数据库校验规则

{{#IF_HAS_DB}}
1. SQL 必须参数化，禁止字符串拼接 SQL。
2. 数据库连接信息从环境变量或配置文件读取。
3. 不在代码中写真实账号、密码、host、token。
4. 新增接口校验新增记录和关键字段。
5. 更新接口校验修改字段和未修改字段。
6. 删除接口校验删除状态。
7. 查询接口校验响应结果和数据库一致。
8. 失败接口校验数据库无脏数据。
9. 数据清理优先按唯一测试标识清理。
10. 并行执行时数据不能互相影响。
{{/IF_HAS_DB}}
{{#IF_NOT_HAS_DB}}
> 本项目未配置数据库校验，此节不适用。
{{/IF_NOT_HAS_DB}}

---

## 五、禁止事项

- 禁止生成 Selenium、Playwright、Appium 相关 UI 自动化代码。
- 禁止访问真实第三方支付、短信、邮件服务。
- 禁止把生产环境数据或生产环境凭据作为测试依赖。
- 禁止把真实密钥、token、密码写入**测试代码**（.py 文件）；配置文件 variables.yaml 允许存储测试环境凭据，但**禁止**存储生产环境凭据（见下方敏感配置维护规则）。
- 禁止假装已经运行过测试。
- 禁止使用裸 `except:` 或 `except Exception:` 而不记录日志。
- 禁止在测试函数中使用 `print()`，统一使用 `logger`。
- 禁止在测试代码中使用 `os.path`，统一使用 `pathlib.Path`。

---

## 六、技能使用规范

新建测试用例时，按以下顺序调用技能（标注"必须"的不可跳过）：

| 阶段 | 命令 | 必须/推荐 | 说明 |
|---|---|---|---|
| 0. 规格对齐 | `/case-design` 内含步骤 0 | **必须** | 先读 `specs/<业务线>/` 需求文档，建立追溯表 |
| 1. 用例设计 | `/case-design` | **必须** | 先出用例清单，确认覆盖维度，再写代码 |
| 2. 测试数据 | `/test-data` | 推荐 | 数据驱动用例或需要 YAML 组织数据时使用 |
| 3. 编写代码 | `/write-tests` | **必须** | 生成 pytest 代码框架，含 fixture/helper |
| 4. 断言设计 | `/assertion-design` | 推荐 | 断言策略不明确或接口字段复杂时使用 |
| 5. 数据验证 | `/data-verify` | **必须**（写/改/删接口） | 新增/更新/删除接口必须有数据验证 |
{{#IF_HAS_ALLURE}}
| 6. 报告装饰 | `/report-decorate` | **必须** | 每个测试文件完成后补全 allure 注解 |
{{/IF_HAS_ALLURE}}
| 7. 合规自检 | `/compliance-check` | **必须** | 收尾门禁：扫描写操作用例是否缺 DB 校验 |

Phase 2 扩展技能：
| `/spec-review` | 审查 Spec 文档质量 |
| `/mock-setup` | 为外部依赖配置 Mock 服务 |
| `/contract-test` | 生成 JSON Schema 契约测试 |
| `/analyze-ci-failures` | 分析 CI 失败结果，输出改进建议 |

失败排查时：
- `/debug-failure` — 用例失败、报错、数据异常时调用，定位根因后再修代码

使用技能时的注意事项：
1. 调用 `/write-tests` 时，在 `$ARGUMENTS` 中说明"token 从 `{{AUTH_MODULE_PATH}}` 获取"（项目无通用 `login_token` fixture）。
{{#IF_HAS_ALLURE}}
2. 调用 `/report-decorate` 时，生成的 `allure.severity` 和 `allure.step` 注解可直接补入现有文件，不影响存量测试。
{{/IF_HAS_ALLURE}}

---

## 七、敏感配置维护规则

1. 敏感值（密码、DB host/user/password、API secret_key 等）优先写入 `variables_override.yaml`（gitignored）；执行机无法读取 override 文件时，允许将测试环境凭据直接写入 `variables.yaml` 并提交。
2. 每当 `variables_override.yaml` 新增或删除一个敏感键，**必须同步**更新 `variables_override.yaml.template`（对应位置用 `<FILL_IN>` 占位），两个文件的结构必须保持一致。
3. 代码重构或项目结构优化后，核查 `variables_override.yaml.template` 是否遗漏新引入的敏感配置节。
4. `variables.yaml` 允许写入测试环境的真实凭据；**禁止写入生产环境凭据**。

---

## 八、项目架构指南

> 以下内容描述项目的目录结构、工具用法和常见模式，供 AI 和新成员快速理解代码。

### 目录结构

```
{{PROJECT_NAME}}/
├── CLAUDE.md                      # 本文件（AI 行为约束 + 架构指南）
├── config/
│   └── variable_loader.py         # 变量加载器（三层合并：default → env → override）
├── utils/
{{#IF_HAS_HTTP}}
│   ├── http_client.py             # 通用 HTTP 客户端（retry + auth token + 自动状态码断言）
{{/IF_HAS_HTTP}}
{{#IF_HAS_DB}}
│   ├── db_client.py               # {{DB_TYPE}} 客户端（{{DB_DRIVER}} + DBUtils 连接池）
{{/IF_HAS_DB}}
│   ├── logger.py                  # 日志工厂（只写文件 + 敏感字段脱敏）
│   ├── data_reader.py             # YAML/JSON/Excel 数据读取
│   ├── data_factory.py            # 测试数据工厂（faker + UUID 唯一性）
│   ├── contract_checker.py        # JSON Schema 契约校验
│   ├── mock_server.py             # Mock 服务（responses 库）
│   ├── assertions.py              # SoftAssertions 软断言工具
│   └── poll_helper.py             # 异步落库轮询等待工具
├── {{PROJECT_NAME_SNAKE}}/
│   └── client/                    # 业务 API 封装（需项目自行实现）
├── testcase/                      # 唯一正式用例目录（pytest.ini: testpaths = testcase）
│   ├── conftest.py                # http_client fixture（session 级）
│   └── <业务线>/                  # 按业务线分目录
├── specs/                         # 规格文档目录
│   ├── registry.yaml              # 机器可读 spec 索引（v2.1）
│   └── <业务线>/                  # 各业务线需求文档
├── schemas/                       # JSON Schema 文件（契约测试用）
├── data/{yaml,json,excel}/        # 数据驱动用例的测试数据
├── scripts/                       # 工具链脚本
│   ├── validate_specs.py          # spec 注册表校验
│   ├── check_coverage.py          # spec→test 覆盖率
│   ├── generate_skeletons.py      # 测试骨架生成（含 --append）
│   ├── generate_clients.py        # API Client 桩生成
│   ├── import_openapi.py          # OpenAPI/Swagger 导入
│   ├── check_compliance.py        # 合规自检
│   ├── spec_diff.py               # spec 变更影响分析
│   ├── detect_flaky.py            # Flaky Test 检测
│   ├── generate_metrics.py        # 质量度量
│   └── mcp_server.py              # MCP Server（AI 工具链）
├── .claude/commands/              # AI 技能命令（13 个）
├── logs/ reports/                 # 运行产物（gitignored）
├── conftest.py                    # 根级：Allure 环境信息 + 失败自动 attach
├── pytest.ini                     # testpaths = testcase；strict-markers
├── {{RUN_SCRIPT_NAME}}.ps1/.sh    # 分组执行脚本
├── variables.yaml                 # 非敏感默认变量（提交 git）
├── variables.{env}.yaml           # 环境层变量（如 staging/prod，可选）
├── variables_override.yaml        # 敏感值（gitignored）
└── docker-compose.test.yml        # 测试数据库容器（可选）
```

### 变量系统

三层合并优先级（低 → 高）：
1. `variables.yaml` — 非敏感默认值（提交 Git）
2. `variables.{env}.yaml` — 环境层（通过 `ENV` 环境变量选择，如 `ENV=staging`）
3. `variables_override.yaml` — 敏感覆盖（gitignored）

```python
from config.variable_loader import get as var_get, get_nested, current_env

base_url = var_get("base_url", "http://localhost")
db_cfg = get_nested("db.default")          # 点号路径访问嵌套 key
env_name = current_env()                    # 当前环境名
```

{{#IF_HAS_HTTP}}
### HTTP 客户端

```python
# 通用 HTTP 客户端（自动重试 503/超时，支持 auth token 管理）
from utils.http_client import HttpClient

client = HttpClient()                              # base_url 从 variables.yaml 读取
client.set_auth_token("Bearer eyJ...")             # 后续请求自动带 Authorization
client.login("username", "password")               # 登录并自动设置 token
client.get("/api/users")                           # 默认断言 200
client.post("/api/items", json={...}, assert_status=201)
client.delete("/api/items/1", assert_status=[200, 204])
resp = client.get("/api/maybe-404", assert_status=None)  # 关闭断言
```
{{/IF_HAS_HTTP}}

{{#IF_HAS_DB}}
### 数据库客户端

```python
from utils.db_client import get_db

db = get_db("default")
rows = db.query("SELECT * FROM Orders WHERE Id = %s", (order_id,))
row  = db.query_one("SELECT * FROM Orders WHERE Id = %s", (order_id,))
n    = db.execute("UPDATE Orders SET Status = %s WHERE Id = %s", (status, order_id))
```
{{/IF_HAS_DB}}

### 常用命令

```bash
# 工具链
python scripts/validate_specs.py        # 校验 spec 注册表
python scripts/check_coverage.py        # spec→test 覆盖率
python scripts/generate_skeletons.py    # 生成测试骨架
python scripts/generate_skeletons.py --append  # 追加缺失测试函数
python scripts/generate_clients.py      # 生成 API Client 桩
python scripts/import_openapi.py swagger.yaml  # 导入 OpenAPI 接口
python scripts/check_compliance.py      # 合规自检
python scripts/mcp_server.py            # 启动 MCP Server

# 测试执行
pytest testcase/ -m smoke -v            # 只跑 smoke
pytest testcase/ -v                     # 全量
{{#IF_HAS_ALLURE}}
pytest testcase/ --alluredir=reports/allure-results  # 生成 Allure 结果
{{/IF_HAS_ALLURE}}
```
