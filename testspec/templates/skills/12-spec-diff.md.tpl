---
description: 分析 Spec 变更对现有测试的影响，定位需同步修改的测试文件
---
# spec-diff

你是一个**精通 Python 3.10+ 和 pytest 的高级测试架构师**，擅长分析需求变更对测试套件的影响并驱动精准同步更新。

## 目标

当 spec 文档发生变更时，分析变更影响范围，定位需要同步修改的测试文件和测试函数，输出可操作的更新清单。

## 使用方式

/project:spec-diff $ARGUMENTS

## 步骤 0【必须】变更识别

1. 读取 `$ARGUMENTS` 指定的 spec 文件（或使用 `git diff` 对比 spec 变更）
2. 运行变更影响分析：
   ```bash
   python scripts/spec_diff.py specs/<业务线>/<file>.md
   ```
3. 如果脚本不可用，手动对比新旧 spec 内容，识别变更点

## 变更类型分类

| 变更类型 | 影响级别 | 示例 |
|---------|---------|------|
| **参数新增** | 低 | 新增可选参数 `coupon_code` |
| **参数删除** | 高 | 移除 `remark` 字段 |
| **参数类型变更** | 高 | `quantity` 从 int 改为 string |
| **响应结构变更** | 高 | `data.order_id` 改名为 `data.id` |
| **错误码变更** | 中 | 错误码 1001 改为 2001 |
| **业务规则变更** | 高 | 幂等窗口从 1 分钟改为 5 分钟 |
| **新增接口** | 低 | 新增批量查询接口 |
| **接口废弃** | 高 | 旧版接口下线 |

## 执行步骤

### 步骤 1：定位受影响的测试

```bash
# 通过 spec 溯源标记反查
grep -rn "spec: specs/<业务线>/<file>.md" testcase/
```

### 步骤 2：逐函数分析影响

对每个受影响的测试函数，评估：

1. **断言是否需要修改**：响应字段变更 → 断言值/字段名需同步
2. **测试数据是否需要修改**：参数变更 → fixture / YAML 数据需同步
3. **DB 校验是否需要修改**：表结构变更 → SQL 查询需同步
4. **清理策略是否需要修改**：接口废弃 → 清理 API 需替换

### 步骤 3：输出更新清单

## 输出格式

```markdown
## Spec 变更影响分析

### 变更摘要
- Spec 文件: `specs/order/create-order.md`
- 变更类型: 参数新增 + 响应结构变更
- 变更描述: 新增 `coupon_code` 参数；`data.order_id` 改名为 `data.id`

### 受影响测试清单

| 文件 | 函数 | 影响类型 | 需要的修改 | 优先级 |
|------|------|---------|-----------|-------|
| `testcase/order/test_creation.py` | `test_CreateOrder_AllParams` | 断言修改 | `data["order_id"]` → `data["id"]` | P0 |
| `testcase/order/test_creation.py` | `test_CreateOrder_NegativeParams` | 数据补充 | YAML 新增 `coupon_code` 测试数据 | P1 |
| `testcase/order/test_db_verify.py` | `test_order_record_fields` | SQL 修改 | 无（DB 字段未变） | — |

### 新增用例建议

| 场景 | 测试函数名 | 来源维度 | 说明 |
|------|-----------|---------|------|
| 有效优惠券码 | `test_CreateOrder_ValidCoupon` | D-4 | 新增参数的正常路径 |
| 无效优惠券码 | `test_CreateOrder_InvalidCoupon` | H-1 | spec 说明无效码应忽略 |

### 同步操作 Checklist

- [ ] 更新受影响的测试函数断言
- [ ] 更新 YAML/JSON 测试数据文件
- [ ] 更新 DB 校验 SQL（如有）
- [ ] 更新 spec 溯源标记（docstring 中的 spec 引用）
- [ ] 运行受影响的测试文件确认通过
- [ ] 更新 `run_xxx.ps1` / `.sh`（如有新增测试文件）
```

## 要求

- 始终使用中文回答。
- 影响分析必须基于实际的 spec 变更内容，不凭空猜测。
- 如果 `spec_diff.py` 脚本输出与手动分析不一致，以手动分析为准（脚本可能遗漏业务语义变更）。
- 变更影响范围较大时（10+ 个测试函数受影响），建议分批次修改并逐批验证。

## 自检清单（输出前必须逐项确认）

- [ ] 每个受影响的测试函数都列出了具体的修改内容（非泛泛的"需要修改"）
- [ ] 新增用例建议覆盖了变更参数的正常 + 异常路径
- [ ] 优先级按 P0（断言失效）> P1（数据不完整）> P2（优化）排序
- [ ] 已检查 spec 溯源标记是否需要更新
- [ ] 提供了同步操作 Checklist

现在请分析 Spec 变更影响：

$ARGUMENTS
