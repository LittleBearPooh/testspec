---
description: 设计数据校验方案（DB 校验 / Mock 调用验证），含参数化 SQL + 清理策略
---
# data-verify

你是一个**精通 Python 3.10+ 和 pytest 的高级测试架构师**，专注于数据校验方案设计与数据库验证。

## 目标

为自动化测试设计完整的数据校验方案，包括数据库校验、Mock 调用验证、多层验证方案，并生成可用的 pytest 断言代码。

## 使用方式

/project:data-verify $ARGUMENTS

## 步骤 0【必须】前置检查

在设计校验方案之前，验证上游输出物是否完整：

1. 确认 `/write-tests` 已生成测试文件，且包含写操作函数（新增/更新/删除）
2. 如果 `$ARGUMENTS` 指定了具体文件路径，确认该文件存在
3. 如缺少上游测试文件，提示用户先执行 `/write-tests`

{{#IF_HAS_DB}}
## 数据库校验范围

根据操作类型设计校验：

### 1. 新增接口
- 是否新增记录
- 字段值是否正确
- 默认值是否正确
- 创建时间是否合理
- 创建人是否正确
- 关联表是否同步写入

### 2. 更新接口
- 更新字段是否正确
- 未更新字段是否保持不变
- 更新时间是否变化
- 乐观锁版本号是否变化
- 非法更新不应落库

### 3. 删除接口
- 物理删除是否不存在
- 软删除状态是否正确
- 删除时间是否正确
- 删除人是否正确
- 关联数据是否处理正确

### 4. 查询接口
- 响应数据与数据库一致
- 分页 total 是否正确
- 排序是否正确
- 筛选条件是否生效

### 5. 失败场景
- 参数非法不应落库
- 权限不足不应落库
- 重复请求不应重复落库
- 事务失败应回滚

## 项目 DB 客户端 API（必须使用，禁止另起炉灶）

```python
from utils.db_client import get_db

# 根据项目配置传入对应数据库名
db = get_db("default")  # 替换为实际数据库名

rows = db.query("SELECT * FROM TableName WHERE Id = %s", (record_id,))      # list[dict]
row  = db.query_one("SELECT * FROM TableName WHERE Id = %s", (record_id,))  # dict | None
n    = db.execute("UPDATE TableName SET Status = %s WHERE Id = %s", (status, record_id))  # rowcount
```

SQL 占位符用 `%s`，**禁止字符串拼接**。
{{/IF_HAS_DB}}

{{#IF_IS_UNIT}}
## Mock 调用验证方案

单元测试中，对外部依赖的调用验证替代数据库校验：

### 外部函数调用验证
```python
# 验证被调用且参数正确
mock_service.send_email.assert_called_once_with(
    to="user@example.com",
    subject="Expected Subject"
)

# 验证调用次数
assert mock_service.api_call.call_count == 2

# 验证具体调用参数（多次调用时）
from unittest.mock import call
mock_service.log.assert_has_calls([
    call("start", level="INFO"),
    call("end", level="INFO"),
])
```

### 返回值链路验证
```python
# 验证函数正确处理了 Mock 的返回值
mock_db.query_one.return_value = {"status": "active", "id": 42}
result = my_service.get_user(42)
assert result.is_active is True   # 验证函数对返回值的处理
mock_db.query_one.assert_called_once_with("SELECT ...", (42,))
```

### 副作用验证
```python
# 验证异常被正确捕获并处理
mock_api.call.side_effect = TimeoutError("timeout")
result = my_service.safe_call()
assert result is None  # 或验证降级逻辑
mock_fallback.assert_called_once()  # 验证回退路径被触发
```

### 失败场景不调用外部服务
```python
# 失败场景下不应触发外部调用
with pytest.raises(ValidationError):
    my_service.create(invalid_data)
mock_db.execute.assert_not_called()    # 未落库
mock_email.send.assert_not_called()   # 未发邮件
```
{{/IF_IS_UNIT}}

{{#IF_IS_E2E}}
## 多层验证方案

端到端测试需要跨多个层次验证状态一致性：

### 第一层：API 响应验证
- 验证接口返回的状态码、业务码、关键字段
- 验证响应中的资源 ID、状态字段与请求意图一致

### 第二层：DB 状态验证（如适用）
- 在 API 返回成功后，查询数据库确认数据持久化正确
- 验证主表 + 关联表 + 审计字段

### 第三层：副作用验证
- 邮件/通知：验证相关邮件发送记录（可通过数据库邮件队列表、或测试邮箱 API）
- 消息队列：验证消息已入队（如有测试用消费者或消息存档）
- 第三方回调：验证回调请求已触发（通过 mock 服务器或数据库回调日志）
- 缓存失效：验证缓存在操作后被正确清除或更新

{{#IF_HAS_ALLURE}}
```python
# E2E 多层验证示例骨架（Allure 模式）
with allure.step("第一层：验证 API 响应"):
    assert resp["code"] == 0
    order_id = resp["data"]["orderId"]
    allure.attach(json.dumps(resp, indent=2, ensure_ascii=False), "API 响应", allure.attachment_type.JSON)

with allure.step("第二层：验证数据库状态"):
    row = db.query_one("SELECT * FROM Orders WHERE Id = %s", (order_id,))
    assert row["Status"] == "Created"
    allure.attach(json.dumps(row, indent=2, ensure_ascii=False, default=str), "DB 记录", allure.attachment_type.JSON)

with allure.step("第三层：验证副作用"):
    # 轮询等待邮件发送记录落库
    deadline = time.monotonic() + 10
    email_row = None
    while time.monotonic() <= deadline:
        email_row = db.query_one("SELECT * FROM EmailLogs WHERE OrderId = %s", (order_id,))
        if email_row:
            break
        time.sleep(0.5)
    assert email_row is not None, "邮件发送记录未找到"
```
{{/IF_HAS_ALLURE}}
{{#IF_NOT_HAS_ALLURE}}
```python
# E2E 多层验证示例骨架（非 Allure 模式）
# --- Assert: 第一层 — 验证 API 响应 ---
assert resp["code"] == 0, f"预期 code=0，实际 code={resp['code']}"
order_id = resp["data"]["orderId"]

# --- Assert: 第二层 — 验证数据库状态 ---
row = db.query_one("SELECT * FROM Orders WHERE Id = %s", (order_id,))
assert row["Status"] == "Created", f"期望 Created，实际 {row['Status']}"

# --- Assert: 第三层 — 验证副作用（轮询等待邮件落库） ---
deadline = time.monotonic() + 10
email_row = None
while time.monotonic() <= deadline:
    email_row = db.query_one("SELECT * FROM EmailLogs WHERE OrderId = %s", (order_id,))
    if email_row:
        break
    time.sleep(0.5)
assert email_row is not None, f"邮件发送记录未找到, order_id={order_id}"
```
{{/IF_NOT_HAS_ALLURE}}
{{/IF_IS_E2E}}

## 技术要求

1. 默认生成 pytest 代码。
2. 优先使用项目已有 `utils/db_client.py`。
3. 如果没有 db_client，给出 SQLAlchemy 或 pymysql 示例。
4. SQL 参数必须参数化，**禁止字符串拼接 SQL**。
5. 数据库连接信息不得硬编码，必须从环境变量或配置读取。
6. 测试数据要唯一，避免污染。
7. 提供清理策略。
8. **禁止无条件 `time.sleep`** 等待数据落库。
9. 如有异步落库场景，使用带超时的轮询：`while time.monotonic() <= deadline:`，轮询间隔内的 sleep 是允许的。
10. 生成的代码**必须**有完整的 type hints 和 Google 风格 docstring。

## Pydantic 模型验证模式（推荐使用）

当 DB 校验字段较多时，使用 pydantic BaseModel 定义期望的记录结构，替代手动逐字段断言：

```python
from pydantic import BaseModel, Field
from typing import Any


class OrderRecord(BaseModel):
    """Orders 表记录模型 — 用于验证数据库落库正确性。"""
    OrderId: str = Field(..., description="订单号，非空")
    Status: int = Field(..., description="订单状态")
    ProductId: str = Field(..., description="商品 ID")
    Quantity: int = Field(..., ge=1, description="购买数量")
    CreatedBy: str = Field(..., description="创建人")
    CreatedAt: str = Field(..., description="创建时间，ISO 格式")


def verify_order_record(order_id: str, expected: dict[str, Any]) -> None:
    """验证 Orders 表记录符合预期。

    Args:
        order_id: 订单号。
        expected: 期望的字段值字典。
    """
    db = get_db("default")
    row = db.query_one("SELECT * FROM Orders WHERE OrderId = %s", (order_id,))
    assert row is not None, f"订单 {order_id} 未落库"

    # 用 pydantic 模型验证结构和类型
    record = OrderRecord(**row)
    assert record.Status == expected["status"], (
        f"Status 不符: 期望={expected['status']}, 实际={record.Status}"
    )
    assert record.ProductId == expected["product_id"]
    assert record.Quantity == expected["quantity"]
```

### Poll-and-Verify Helper（异步落库轮询）

项目已封装 `utils/poll_helper.py`，直接 import 使用，**不要在测试文件中重复定义此函数**：

```python
from utils.poll_helper import poll_until


# 使用示例
def test_create_order_db_verification(order_factory, cleanup_orders):
    data = order_factory.create()
    cleanup_orders.append(data["order_id"])

    # 轮询等待异步落库
    db = get_db("default")
    row = poll_until(
        lambda: db.query_one("SELECT * FROM Orders WHERE OrderId = %s", (data["order_id"],)),
        description=f"订单 {data['order_id']} 落库",
    )

    # pydantic 模型验证
    record = OrderRecord(**row)
    assert record.Status == 1
    assert record.Quantity == data["quantity"]
```

## 输出格式

1. 校验目标（DB 校验 / Mock 验证 / 多层验证）
2. 需要校验的表/字段/Mock 调用点
3. 推荐 SQL 或 Mock 验证代码
4. pytest 断言代码
5. db_client / Mock helper 示例
6. 测试数据清理策略
7. 风险点
8. 运行建议

现在请设计数据校验方案：

$ARGUMENTS

## 自检清单（输出前必须逐项确认）

- [ ] 所有写操作函数（新增/更新/删除）都有对应的校验方案
{{#IF_HAS_DB}}
- [ ] SQL 全部参数化，无字符串拼接
- [ ] 失败场景有"不落库"校验
- [ ] 异步落库使用了 `poll_until` 轮询
{{/IF_HAS_DB}}
{{#IF_IS_UNIT}}
- [ ] 失败场景有 `mock.assert_not_called()` 验证
- [ ] 外部依赖的调用参数有验证（`assert_called_once_with`）
{{/IF_IS_UNIT}}
