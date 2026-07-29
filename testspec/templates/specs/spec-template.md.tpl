# {{PROJECT_NAME_TITLE}} — Spec 文档模板

> 请根据以下结构编写你的测试规格文档。
> 完成后在 `specs/registry.yaml` 中注册此文档。
>
> TestSpec 版本: {{TESTSPEC_VERSION}}

---

## 基本信息

- **测试函数名**: `test_XXX`
- **业务线/模块**: <业务线>
- **用例类型**: (smoke / contract / unit / integration / e2e)
- **优先级**: (P0 / P1 / P2)
- **所在文件**: `testcase/<业务线>/test_xxx.py`
- **认证方式**: (bearer / api_key / basic / none / inherit)
- **响应时间 SLA**: <毫秒数>（可选）

## 用例说明

> 一句话描述这个测试用例验证的业务场景。

## 前置条件

- 需要准备的测试数据
- 需要登录的账号（从 `variables.yaml` 获取）
- 需要 Mock 的外部依赖（单元测试适用）

## 测试步骤

### 步骤 1：<步骤描述>

- **接口/函数**: `<接口路径或函数名>`
- **操作**: <具体操作描述>
- **请求参数**:
  ```json
  {
    "field": "value"
  }
  ```
- **预期响应**: HTTP 200，业务码 0
- **预期响应字段**: (列出必须存在的字段名)
- **断言**: 关键字段校验

### 步骤 2：<步骤描述>

（同上格式）

## 数据验证

### 数据库校验（API / 集成测试适用）

- **目标表**: `<表名>`
- **操作类型**: (INSERT / UPDATE / DELETE / SELECT / UPSERT)
- **查询条件**: `WHERE Id = %s`，参数为 `(<id>,)`
- **校验字段**:
  | 字段 | 期望值 | 说明 |
  |---|---|---|
  | Status | 1 | 新建状态 |
  | CreatedAt | 非空 | 创建时间已记录 |

### Mock 验证（单元测试适用）

- **Mock 目标**: `module.function_name`
- **验证方式**: `mock.assert_called_once_with(expected_args)`
- **调用次数**: 1
- **返回值**: `{"key": "value"}`

### 多层验证（E2E 测试适用）

- **层 1 — API 响应**: 状态码 200，业务码正确
- **层 2 — DB 状态**: 记录已创建/更新
- **层 3 — 副作用**: 邮件已发送 / 消息已入队

## 契约 Schema

- **Schema 文件**: `schemas/<spec-id>.yaml`（可选，配合 `/contract-test` 技能使用）

## 清理策略

- **清理时机**: 测试完成后（autouse fixture 或手动）
- **清理方式**: 按唯一标识删除测试数据
- **清理函数**: `<fixture_name>` fixture 中注册

## 报告注解

```python
@allure.title("<用例标题>")
@allure.feature("<业务线/模块>")
@allure.story("<接口操作 业务对象>")
@allure.severity(allure.severity_level.CRITICAL)  # 或 NORMAL / MINOR
```

## 业务规则

| 规则 ID | 描述 | 类型 |
|---------|------|------|
| BR-001 | <规则描述> | idempotency / precondition / invariant / transition / authorization |

## 反向测试场景（Negative Testing）

> 除了验证"系统应该做什么"，还要验证"系统不应该做什么"。
> 每个反向场景都需要对应一个 `test_should_reject_when_<condition>` 测试函数。
> 场景类型列使用 `/case-design` 的维度编号（D/G/H/U/E），便于追溯。

| 反向场景 | 预期行为 | 维度编号 | 说明 |
|----------|---------|---------|------|
| 用已删除的 ID 再次操作 | 返回 404，不产生副作用 | D-2 | 数据不存在 |
| 并发提交相同请求 | 只有一个成功，其余被拒绝 | G-2 | 并发安全 |
| 使用过期 Token 操作 | 返回 401，数据不受影响 | H-6 | Token 失效 |
| 传入超出范围的数值 | 返回 400，数据库无变化 | D-3 | 参数边界 |

## 关联 Spec

> 列出与本接口有业务关联的其他 Spec，便于端到端追溯。

| 关联 Spec ID | 关系类型 | 说明 |
|-------------|---------|------|
| `<related-spec-id>` | 后续操作 / 依赖 / 前置 | <关系说明> |

## 注意事项

- 异步结果使用带超时的轮询循环（`while time.monotonic() <= deadline`），禁止无条件 `time.sleep`
- 禁止在测试代码中硬编码 base_url、token、账号密码
- 所有 SQL 必须参数化，禁止字符串拼接
- 每个 `with allure.step(...)` 块内必须 `allure.attach(...)` 输出关键参数和响应
- 测试数据必须唯一，避免并发执行冲突
- 日志统一使用 `from utils.logger import get_logger`
