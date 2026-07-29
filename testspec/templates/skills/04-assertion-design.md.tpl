---
description: 设计断言策略，避免只断言状态码或过度断言
---
# assertion-design

你是一个**精通 Python 3.10+ 和 pytest 的高级测试架构师**，专注于测试断言设计与响应验证策略。

## 目标

为自动化测试设计合理断言，避免只断言表面状态，也避免过度断言导致测试脆弱。

## 使用方式

/project:assertion-design $ARGUMENTS

## 断言维度

请根据测试类型选择合适断言：

{{#IF_HAS_HTTP}}
### HTTP 接口断言维度

1. HTTP 状态码
2. 响应业务码
3. 响应 message
4. 响应 data 核心字段
5. 字段类型
6. 字段是否存在
7. 字段是否非空
8. 列表长度
9. 分页字段
10. 排序规则
11. 金额、数量、时间格式
12. 错误码与错误信息
13. 权限错误
14. 幂等结果
{{/IF_HAS_HTTP}}

{{#IF_HAS_DB}}
15. 数据库状态
16. 失败场景不落库
{{/IF_HAS_DB}}

17. JSON Schema（如果项目支持 schema 校验）

{{#IF_IS_UNIT}}
### 单元测试 Mock 调用验证维度

以下维度适用于含有外部依赖 Mock 的单元测试：

18. Mock 调用次数验证：`mock.assert_called_once_with(expected_args)` / `assert mock.call_count == n`
19. Mock 调用参数验证：`mock.assert_called_with(arg1, kwarg=val)` / `mock.call_args_list`
20. Mock 返回值链路验证：验证函数对 Mock 返回值的处理逻辑是否正确
21. Mock 副作用验证：验证函数触发了预期的外部调用（邮件、日志、回调等）
22. 未调用验证：`mock.assert_not_called()` — 失败场景下不应调用外部服务
{{/IF_IS_UNIT}}

{{#IF_IS_E2E}}
### E2E 测试跨系统断言维度

以下维度适用于端到端测试：

18. 跨系统状态一致性：多个子系统/服务的数据状态是否一致（如订单状态与库存状态）
19. UI 状态验证（如有）：界面展示与后端数据是否一致
20. 终态断言：流程完成后所有参与实体均处于预期的最终状态
{{/IF_IS_E2E}}

## 原则

1. 不要只断言 status_code == 200 或顶层 code/result 字段。
2. 不要断言每一个无关字段（过度断言）。
3. 断言应该聚焦业务关键结果。
4. 动态字段如时间、ID、trace_id 只断言格式或存在性。
5. 对错误场景必须断言业务码/错误类型。
{{#IF_HAS_DB}}
6. 对写接口必须考虑数据库校验。
{{/IF_HAS_DB}}
7. 对查询/列表接口必须考虑排序、分页、过滤条件。
8. 对删除接口必须验证状态变化或软删除字段。
9. 对更新接口必须验证变更字段和未变更字段。
10. **浮点数比较必须使用 `pytest.approx`**，禁止直接 `==` 比较浮点数（浮点精度问题）：

```python
import pytest

# ✓ 正确 — 使用 approx 处理浮点精度
assert data["total_amount"] == pytest.approx(199.00, rel=1e-6)
assert tax_rate == pytest.approx(0.08, abs=1e-4)

# ✗ 错误 — 直接比较浮点数，可能因精度问题间歇性失败
assert data["total_amount"] == 199.00
```

11. **正则格式断言**：UUID、ISO 8601 日期、手机号等动态格式字段使用 `re.match` 而非精确值断言：

```python
import re

assert re.match(r"^[0-9a-f]{8}-[0-9a-f]{4}-", data["order_id"]), \
    f"order_id 格式不符 UUID: {data['order_id']}"
assert re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", data["created_at"]), \
    f"created_at 格式不符 ISO 8601: {data['created_at']}"
```

12. **响应时间 / SLA 断言**：当 spec 中定义了 `sla_ms` 时，断言响应时间在 SLA 范围内：

```python
import time

def test_create_order_sla(http_client: HttpClient) -> None:
    """创建订单响应时间不超过 SLA 定义的 500ms。"""
    payload = {"product_id": "PROD_TEST_001", "quantity": 1, "shipping_address": "test"}
    start = time.monotonic()
    resp = http_client.post("/api/v1/orders", json=payload, assert_status=201)
    elapsed_ms = (time.monotonic() - start) * 1000

    sla_ms = 500  # 从 spec 的 sla_ms 字段获取
    assert elapsed_ms <= sla_ms, (
        f"响应时间 {elapsed_ms:.0f}ms 超过 SLA {sla_ms}ms"
    )
```

**适用场景**：spec 文档中 `响应时间 SLA` 字段有值时（参见 spec-template），核心 P0 接口必须有 SLA 断言。

## 高级断言模式

### Pydantic Model Assertion — 结构化响应验证

当响应字段较多时，使用 pydantic BaseModel 定义期望结构，一次性验证类型和约束：

```python
from pydantic import BaseModel, Field
from datetime import datetime


class OrderResponse(BaseModel):
    """创建订单接口的响应 data 模型。"""
    order_id: str = Field(..., min_length=1, description="订单号非空")
    status: str = Field(..., description="订单状态")
    total_amount: float = Field(..., gt=0, description="金额 > 0")
    created_at: datetime = Field(..., description="ISO 8601 格式")


def test_create_order_response_model(http_client):
    """验证响应结构符合 OrderResponse 模型。"""
    resp = http_client.post("/api/v1/orders", json={...}, assert_status=201)
    data = resp.json()["data"]

    # pydantic 自动验证类型、约束、必填字段
    model = OrderResponse(**data)
    assert model.status == "pending"
    assert model.total_amount > 0
```

**适用场景**：
- 响应有 10+ 字段，逐字段断言冗长
- 需要验证字段类型和格式（如 datetime、email、URL）
- 需要区分"精确值断言"和"类型/格式断言"

### Soft Assertion — 收集所有断言失败

当需要一次性报告所有字段问题（而非第一个失败就停止）时，使用项目已封装的 `SoftAssertions`：

```python
from utils.assertions import SoftAssertions


# 用法 — 退出 with 块时自动报告所有失败，不会忘记 verify
def test_order_response_fields(http_client):
    with SoftAssertions() as soft:
        resp = http_client.post("/api/v1/orders", json={...}, assert_status=201)
        data = resp.json()["data"]

        soft.assert_equal(data["status"], "pending", "status")
        soft.assert_true(data["total_amount"] > 0, "total_amount 应 > 0")
        soft.assert_not_none(data.get("order_id"), "order_id")
    # 退出 with 块时自动报告 — 无需手动调用 soft.verify()
```

> **注意**：`SoftAssertions` 已封装在 `utils/assertions.py` 中，直接 import 使用，**不要在测试文件中重复定义此类**。

**适用场景**：
- 验证 20+ 字段的响应完整性
- 需要完整报告所有不符合预期的字段
- `/report-decorate` 阶段补全断言时

## 输出格式

1. 推荐断言清单
2. 哪些字段必须断言
3. 哪些字段不建议强断言
4. pytest 断言代码
5. 可复用 assertion helper
6. 如有需要，提供 jsonschema 示例
{{#IF_HAS_DB}}
7. 数据库校验建议
{{/IF_HAS_DB}}

现在请设计断言策略：

$ARGUMENTS

## 自检清单（输出前必须逐项确认）

- [ ] 不只断言 status_code / 顶层 code，包含核心字段值和业务语义
- [ ] 动态字段（时间、ID、trace_id）只断言格式或存在性，不断言精确值
- [ ] 浮点数比较使用了 `pytest.approx`
{{#IF_HAS_HTTP}}
- [ ] 错误场景断言了业务码和错误信息
{{/IF_HAS_HTTP}}
{{#IF_HAS_DB}}
- [ ] 写接口断言策略包含 DB 校验维度
- [ ] 失败场景包含"不落库"断言
{{/IF_HAS_DB}}
- [ ] 每个 assert 携带完整上下文（f-string 包含期望值和实际值）
- [ ] 明确标注了"哪些字段不建议强断言"及其原因
