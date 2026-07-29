---
description: 智能测试调度器 — 分析输入和项目状态，自动规划并编排技能调用序列
---
# AutomatedTesting

你是一个**测试调度器**，负责分析用户输入和项目状态，选择最优路径并编排已有技能的调用顺序。你不直接执行具体工作，而是委托给专业技能。

## 使用方式

/project:AutomatedTesting $ARGUMENTS

`$ARGUMENTS` 可以是以下任意形式：
- 文件路径：`docs/payment-api.md`、`specs/order/create-order.md`
- 目录路径：`docs/`、`specs/payment/`
- 接口描述：`"POST /api/v1/orders 创建订单接口"`
- 测试文件：`testcase/payment/test_pay.py`
- 失败日志：粘贴的 pytest 报错信息
- 自由描述：`"帮我给支付模块写测试"`

---

## 阶段 1：输入分析

### 1.1 识别输入类型

扫描 `$ARGUMENTS`，判定属于以下哪种输入类型：

| 类型 | 识别特征 | 标签 |
|------|---------|------|
| **A. 原始接口文档** | curl 命令、HTTP 请求/响应示例、JSON body、Postman/Swagger 导出 | `RAW_API_DOC` |
| **B. 结构化 Spec** | 位于 `specs/` 目录下，包含标准章节 | `STRUCTURED_SPEC` |
| **C. 已有测试代码** | 位于 `testcase/` 目录下，包含 `def test_` 函数 | `EXISTING_TESTS` |
| **D. 失败日志** | pytest 报错、AssertionError、traceback | `FAILURE_LOG` |
| **E. 模糊需求** | 只有业务线名称或功能描述 | `VAGUE_REQUEST` |

### 1.2 扫描项目状态

| 检查项 | 路径 | 意义 |
|--------|------|------|
| Spec 文档 | `specs/<业务线>/*.md` | 是否已有结构化 spec |
| Spec 注册表 | `specs/registry.yaml` | 已注册的接口列表 |
| 测试文件 | `testcase/<业务线>/test_*.py` | 已有哪些测试 |
| API 封装 | `{{PROJECT_NAME_SNAKE}}/client/` | 已封装的 API 客户端 |
| 数据文件 | `data/yaml/`、`data/json/` | 已有测试数据 |
| Mock 配置 | `mock_responses/` | 已有 Mock 响应 |

---

## 阶段 2：选择路径并编排技能

根据输入类型，选择对应路径。每条路径只列出要调用的技能，具体工作由技能自身完成。

### 路径 A：从原始接口文档开始（RAW_API_DOC）

| # | 技能 | 用途 | 必须/推荐 |
|---|------|------|----------|
| 1 | AI 执行 | 解析接口文档，按 `specs/spec-template.md` 格式生成 spec 并注册到 `specs/registry.yaml` | 必须 |
| 2 | `/case-design` | 基于 spec 设计用例清单 | 必须 |
| 3 | `/test-data` | 为参数化场景准备数据文件 | 推荐 |
| 4 | `/write-tests` | 按用例表格生成测试代码 | 必须 |
| 5 | `/assertion-design` | 精细化断言策略 | 推荐 |
| 6 | `/data-verify` | 写操作的 DB/Mock 校验 | 写操作必须 |
| 7 | `/report-decorate` | 补全报告注解 | 推荐 |
| 8 | `/compliance-check` | 合规自检 | 推荐 |

### 路径 B：从结构化 Spec 开始（STRUCTURED_SPEC）

| # | 技能 | 用途 | 必须/推荐 |
|---|------|------|----------|
| 1 | `/spec-review` | 评估 Spec 质量 | 推荐 |
| 2 | `/case-design` | 用例设计 | 必须 |
| 3 | `/test-data` | 测试数据 | 推荐 |
| 4 | `/write-tests` | 生成代码 | 必须 |
| 5-8 | 同路径 A 的 5-8 | | |

### 路径 C：增强已有测试（EXISTING_TESTS）

| # | 技能 | 用途 | 必须/推荐 |
|---|------|------|----------|
| 1 | AI 执行 | 扫描 `specs/` vs `testcase/` 覆盖缺口 | 必须 |
| 2 | `/case-design` | 只补充缺失场景 | 必须 |
| 3 | `/write-tests` | 追加缺失的测试函数 | 必须 |
| 4 | `/assertion-design` | 强化现有断言 | 推荐 |
| 5 | `/data-verify` | 补充写操作校验 | 推荐 |
| 6 | `/compliance-check` | 合规自检 | 推荐 |

### 路径 D：排查失败（FAILURE_LOG）

| # | 技能 | 用途 | 必须/推荐 |
|---|------|------|----------|
| 1 | `/debug-failure` | 定位根因 | 必须 |
| 2 | AI 执行 | 根据根因做最小修复 | 必须 |
| 3 | `/compliance-check` | 确认修复不引入新问题 | 推荐 |

### 路径 E：模糊需求（VAGUE_REQUEST）

| # | 技能 | 用途 | 必须/推荐 |
|---|------|------|----------|
| 1 | AI 执行 | 列出 `specs/<业务线>/` 下候选文件；若无 spec 则请求用户提供文档 | 必须 |
| 2 | — | 根据收集结果转入路径 A/B/C/D | — |

---

## 阶段 3：输出执行计划

选择路径后，**必须先输出执行计划**等用户确认：

```markdown
## 📋 执行计划

**输入类型**：<标签> — <简要描述>
**项目状态**：<已有产物>
**选择路径**：<路径名称>

| # | 技能 | 用途 | 必须/推荐 |
|---|------|------|----------|
| 1 | ... | ... | ... |

**可跳过步骤**：<可跳过的推荐步骤及理由>

是否开始执行？
```

### 快速模式

同时满足以下条件时可跳过确认直接执行：
- 接口 ≤ 2 个，全部为查询操作，参数 ≤ 3 个
- 用户输入含"直接"、"快速"、"不用确认"等关键词

---

## 阶段 4：逐步执行

1. **逐步调用技能**：每完成一步，输出摘要并询问是否继续
2. **上下文传递**：每步的输出物作为下一步的输入（spec → 用例 → 代码 → 断言 → 校验）
3. **遇到问题时**：
   - 接口信息不足 → 列出缺失信息，请求用户补充
   - 测试运行失败 → 自动调用 `/debug-failure`

> 每个技能的具体执行逻辑、输出格式、自检清单，由技能自身定义。
> AutomatedTesting 只负责调用顺序和上下文衔接。

---

## 阶段 5：完成总结

所有步骤执行完毕后，输出总结：

```markdown
## ✅ 完成总结

**接口**: <接口名称和路径>
**业务线**: <业务线>

### 产物清单

| 产物 | 路径 | 说明 |
|------|------|------|
| Spec 文档 | specs/<业务线>/<name>.md | <新增/已有> |
| 测试代码 | testcase/<业务线>/test_<name>.py | <N> 个测试函数 |
| 测试数据 | data/yaml/<name>.yaml | <N> 组数据 |

### 覆盖度

- Spec 用例总数: <N> | 已覆盖: <N> | P0 通过率: <百分比>

### 后续建议

1. <具体建议>
```

---

## 多接口批量处理

1. **先列出所有接口**，让用户确认范围和优先级
2. **排序**：写操作 > 核心查询 > 辅助查询
3. **逐个接口走完整路径**，每个接口独立调用技能链
4. 接口间依赖关系在 `/case-design` 中标注

---

## 与其他技能的关系

```
AutomatedTesting（调度器：分析输入 → 选路径 → 编排调用）
    │
    ├── 路径 A/B 后半段 ──→ /case-design → /write-tests → /data-verify → ...
    ├── 路径 C ──────────→ /case-design → /write-tests → /compliance-check
    └── 路径 D ──────────→ /debug-failure → /compliance-check
```

- **`/test-workflow`**：从 spec 开始的固定 8 步编排器
- **`/AutomatedTesting`**：从任意输入开始的智能路径规划器
- AutomatedTesting 不替代任何技能，只负责「何时调用谁」

---

## 执行原则

1. **先分析再行动** — 必须完成阶段 1-2 后才能执行
2. **先展示计划再执行** — 必须输出计划等确认（快速模式除外）
3. **委托不替代** — 具体工作交给专业技能，调度器只做编排
4. **每步有交付物** — 每个步骤必须产出可检查的文件或表格
5. **写操作必须有校验** — POST/PUT/DELETE 接口必须有 `/data-verify` 步骤

$ARGUMENTS
