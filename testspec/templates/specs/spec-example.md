# 示例：创建订单后状态正确落库

## 基本信息

- **测试函数名**: `test_CreateOrder_Success_StatusPending`
- **业务线/模块**: order
- **用例类型**: e2e
- **优先级**: P0
- **所在文件**: `testcase/order/test_order_creation_e2e.py`
- **认证方式**: bearer
- **响应时间 SLA**: 500

## 用例说明

> 验证用户正常下单后，订单在数据库中的初始状态为 Pending（状态值 1），且订单号唯一。

## 前置条件

- 已登录的测试账号（从 `variables.yaml` 的 `test_accounts.default` 获取）
- 商品 ID 存在于测试环境（使用固定的测试商品 `PROD_TEST_001`）
- 订单号通过 UUID 生成，确保唯一性

## 测试步骤

### 步骤 1：创建订单

- **接口**: `POST /api/v1/orders`
- **操作**: 发送创建订单请求
- **请求参数**:
  ```json
  {
    "product_id": "PROD_TEST_001",
    "quantity": 2,
    "shipping_address": "测试地址-自动化用例专用"
  }
  ```
- **预期响应**: HTTP 201
- **断言**:
  - 响应中 `order_id` 非空
  - 响应中 `status` == `"pending"`
  - 响应中 `created_at` 为合法 ISO 时间格式

### 步骤 2：数据库校验

- **接口**: 直接查询 DB
- **操作**: 查询 Orders 表
- **断言**:
  - 记录存在
  - Status 字段 == 1（Pending）
  - ProductId == `"PROD_TEST_001"`
  - Quantity == 2
  - CreatedAt 非空且合理（±5 分钟内）

## 数据验证

### 数据库校验

- **目标表**: `Orders`
- **查询条件**: `WHERE OrderId = %s`，参数为 `(order_id,)`
- **校验字段**:

  | 字段 | 期望值 | 说明 |
  |---|---|---|
  | Status | 1 | Pending 状态 |
  | ProductId | PROD_TEST_001 | 商品 ID 一致 |
  | Quantity | 2 | 数量一致 |
  | CreatedAt | 非空，±5min | 创建时间合理 |
  | CreatedBy | 测试账号 ID | 创建人正确 |

### 关联表校验

- **目标表**: `OrderItems`
- **查询条件**: `WHERE OrderId = %s`
- **校验**: 至少存在 1 条明细记录

## 清理策略

- **清理时机**: 测试函数执行完毕后（通过 autouse fixture）
- **清理方式**: 调用 `DELETE /api/v1/orders/{order_id}` 或直接 DB 软删除
- **清理函数**: `_cleanup_registry` fixture 中注册，teardown 时执行
- **注意**: 清理操作应在断言之前注册（先注册清理，再执行断言，确保即使断言失败也能清理）

## 报告注解

```python
@allure.title("创建订单成功 — 状态正确落库为 Pending")
@allure.feature("订单管理")
@allure.story("创建订单")
@allure.severity(allure.severity_level.CRITICAL)
```

## 注意事项

- 订单号使用 `uuid.uuid4()` 生成，确保并发执行不冲突
- `shipping_address` 使用固定前缀 `"测试地址-自动化用例专用"` 便于识别和清理
- 创建订单是异步操作，需要等待 DB 落库完成后再查询：
  ```python
  deadline = time.monotonic() + 30.0
  while time.monotonic() <= deadline:
      row = db.query_one("SELECT Status FROM Orders WHERE OrderId = %s", (order_id,))
      if row is not None:
          break
      time.sleep(2.0)
  else:
      raise AssertionError(f"订单未在 30s 内落库: {order_id}")
  ```
- 清理操作必须在断言之前注册，确保异常情况下也能清理
