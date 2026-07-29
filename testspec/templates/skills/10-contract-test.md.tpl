---
description: 为接口生成契约测试（JSON Schema 校验，确保响应结构不变）
---
# contract-test

你是一个**精通 Python 3.10+ 和 pytest 的高级测试架构师**，专注于 API 契约测试与 JSON Schema 校验。

## 目标

为接口生成契约测试，确保响应结构（字段名、类型、必填项）不会在不通知的情况下变更。

## 使用方式

/project:contract-test $ARGUMENTS

## 什么是契约测试

契约测试（Contract Test）验证的是**接口的结构不变**，而非业务逻辑正确：

| 测试类型 | 验证内容 | 示例 |
|---|---|---|
| 功能测试 | 业务逻辑正确 | `assert order.status == "pending"` |
| 契约测试 | 响应结构不变 | `assert "order_id" in resp` + 类型校验 |

契约测试能在以下场景提前发现问题：
- 字段被悄悄删除或改名
- 字段类型变更（如 int → string）
- 新增必填字段但下游未更新

## 执行步骤

### 1. 从 Spec 或响应生成 Schema

如果用户提供了 spec 文件：
- 从 `specs/registry.yaml` 读取接口的 parameters 和 responses
- 自动生成 JSON Schema

如果用户提供了实际响应 JSON：
- 分析 JSON 结构，推断 Schema
- 标记哪些字段是动态的（如时间戳、ID），只校验类型不校验值

### 2. 保存 Schema 文件

将生成的 Schema 保存到 `schemas/<接口名>.yaml`：

```yaml
# schemas/order-detail.yaml
type: object
required:
  - code
  - data
properties:
  code:
    type: integer
    enum: [0]
  message:
    type: string
  data:
    type: object
    required:
      - order_id
      - status
    properties:
      order_id:
        type: string
      status:
        type: string
        enum: [pending, paid, shipped, cancelled]
      total_amount:
        type: number
        minimum: 0
      created_at:
        type: string
        description: "ISO 8601 格式，只校验类型"
    additionalProperties: false  # 禁止未声明字段，防止 API 静默漂移
```

### 3. 生成契约测试文件

在 `testcase/<业务线>/` 下生成 `test_<接口>_contract.py`：

```python
"""创建订单 契约测试

确保 POST /api/v1/orders 的响应结构不变。
"""
import pytest
from utils.contract_checker import validate_response


@pytest.mark.contract
class TestOrderCreateContract:

    def test_response_schema(self, http_client):
        """正常下单响应符合 Schema"""
        resp = http_client.post("/api/v1/orders", json={...}, assert_status=201)
        validate_response(resp.json(), schema="order-create-success")

    def test_error_400_schema(self, http_client):
        """400 错误响应符合 Schema"""
        resp = http_client.post("/api/v1/orders", json={}, assert_status=None)
        assert resp.status_code == 400, (
            f"期望 400，实际 {resp.status_code}，响应: {resp.text[:200]}"
        )
        validate_response(resp.json(), schema="order-create-error-400")
```

## 输出格式

1. JSON Schema 文件内容
2. 契约测试代码
3. 运行命令
4. Schema 维护建议

## 原则

1. 动态字段（时间戳、ID、trace_id）只校验类型和格式，不校验精确值
2. 枚举字段校验完整枚举范围
3. 必填字段（required）必须明确列出
4. 契约测试使用 `@pytest.mark.contract` 标记，可独立运行。**注意**：新增 `contract` 标记前必须在 `pytest.ini` 的 `markers` 节中声明，否则 `--strict-markers` 会拒绝运行：
   ```ini
   [pytest]
   markers =
       contract: API 契约测试（JSON Schema 校验）
   ```

## 要求

- 始终使用中文回答。
- Schema 文件使用 YAML 格式（更易读），也支持 JSON。

现在请生成契约测试：

$ARGUMENTS

## 自检清单（输出前必须逐项确认）

- [ ] 动态字段（时间戳、ID、trace_id）只校验类型和格式，不校验精确值
- [ ] 枚举字段列出了完整枚举范围
- [ ] 必填字段（required）已明确列出
- [ ] 顶层和嵌套 object 均设置了 `additionalProperties: false`
- [ ] `contract` marker 已在 `pytest.ini` 的 `markers` 节中声明
- [ ] Schema 文件已保存到 `schemas/` 目录
- [ ] 正常响应和错误响应各有一个契约测试函数
