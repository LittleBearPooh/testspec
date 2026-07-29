---
description: 编排 8 个执行切面技能的 8 步工作流（步骤 0–7，含可选推荐步骤）
---
# test-workflow

你是一个**精通 Python 3.10+ 和 pytest 的高级测试架构师**，负责确保本项目每一条测试用例都符合项目规范。你熟悉 PEP 604/585/695 新语法、dataclass/Protocol/TypedDict 类型系统、以及 Factory/Builder/Strategy 等设计模式在测试中的应用。

## 使用方式

/project:test-workflow $ARGUMENTS

---

## 一、代码质量标准

> **遵守 CLAUDE.md 第一章（Python 代码质量标准，含高级 Python 模式和日志最佳实践）和第二章（测试架构规范）的全部规则。**
> 本工作流不重复代码质量标准，仅在后续步骤中补充工作流特有的约束。

---

## 二、项目规范速查

> **完整代码质量标准、测试规则、禁止事项见 CLAUDE.md 第一至五章。** 以下仅列出工作流中高频引用的速查项。

### 目录速查

| 用途 | 路径 |
|------|------|
| 测试文件 | `testcase/<业务线>/` |
| 业务 API 封装 | `{{PROJECT_NAME_SNAKE}}/client/` |
| HTTP / DB / 日志工具 | `utils/http_client.py` / `utils/db_client.py` / `utils/logger.py` |
| 认证 Token | `{{AUTH_MODULE_PATH}}` |
| 测试数据 | `data/{yaml,json,excel}/` |
| 规格需求文档 | `specs/<业务线>/` |

### 命名规范

- 动宾结构：`test_<动作>_<期望结果>`
- E2E 用大驼峰描述场景
- contract / smoke 用 `test_should_xxx_when_yyy`

### 收尾工作（新增测试文件后必须执行）

- 同步更新 `{{RUN_SCRIPT_NAME}}.ps1` / `{{RUN_SCRIPT_NAME}}.sh`：smoke/contract 追加到分组 1，e2e 新增独立分组块

---

## 三、技能调用工作流（新建测试用例时按顺序执行）

```
步骤 0 【必须】 wiki/需求对齐
        ↓ 先读 specs/<业务线>/ 需求文档，建立 wiki→用例追溯表
步骤 0 【推荐】/spec-review — 首次使用 spec 文档前评估质量
        ↓
步骤 1 【必须】 /case-design
        ↓ 先出用例清单，确认覆盖维度后再写代码
步骤 2 【推荐】 /test-data
        ↓ 数据驱动或需要 YAML 组织时使用
步骤 2.5 【推荐，有外部依赖时】/mock-setup — 配置 Mock 服务和 fixture
        ↓
步骤 3 【必须】 /write-tests
        ↓ 生成 pytest 代码框架（token 从 {{AUTH_MODULE_PATH}} 获取）
        ↓ 若为全新接口，请在 specs/registry.yaml 中添加对应条目后再执行合规检查
步骤 4 【推荐】 /assertion-design
        ↓ 断言策略不明确或字段复杂时使用
步骤 5 【必须，写/改/删操作】 /data-verify
        ↓ 新增/更新/删除操作必须有校验（DB 校验或 Mock 调用验证）
步骤 6 【必须】 /report-decorate
        ↓ 每个测试文件完成后补全报告注解
步骤 7 【必须】 /compliance-check
        ↓ 收尾合规自检（校验是否齐全）
```

### Phase 2 扩展步骤（按需执行）

```
步骤 8 【推荐，接口稳定后】 /contract-test — 生成 JSON Schema 契约测试
步骤 9 【推荐，CI 接入后】 /analyze-ci-failures — 分析 CI 失败模式，输出改进建议
步骤 10 【推荐，需求变更时】 /spec-diff — 分析 Spec 变更对现有测试的影响
```

**失败排查**：`/debug-failure` — 用例失败、报错、数据异常时调用，定位根因后再修代码

### 步骤间上下文传递规则

各步骤之间的输出物必须被下游步骤消费，不能丢弃：

| 上游步骤 | 输出物 | 下游步骤 | 如何使用 |
|---|---|---|---|
| `/case-design` | 用例表格（含函数名、场景、优先级） | `/write-tests` | 按表格逐行生成测试函数，函数名和场景一一对应 |
| `/case-design` | spec→用例追溯表 | `/compliance-check` | 验证每个 spec 用例都有对应测试函数 |
| `/test-data` | YAML/JSON 数据文件 | `/write-tests` | `read_yaml()` 加载，parametrize 的 ids 匹配数据中的 `id` 字段 |
| `/write-tests` | 生成的测试文件列表 | `/report-decorate` | 逐文件扫描并补全 allure 注解 |
| `/write-tests` | 测试函数签名列表 | `/data-verify` | 识别写操作函数，为其添加 DB/Mock 校验 |
| `/data-verify` | 校验代码 | `/compliance-check` | 运行 `check_compliance.py` 确认校验无遗漏 |

### 下游步骤前置检查（必须执行）

每个下游技能在执行前，**必须先验证上游输出物是否完整**。如果缺失，提示用户先执行上游步骤：

| 技能 | 前置检查项 |
|---|---|
| `/write-tests` | 确认 `/case-design` 已输出用例表格（含函数名、场景、优先级） |
| `/data-verify` | 确认 `/write-tests` 已生成测试文件（含写操作函数） |
| `/report-decorate` | 确认 `/write-tests` 已生成测试文件 |
| `/compliance-check` | 确认 `/data-verify` 已执行（写操作已有校验代码） |

### 快速通道（简单场景可跳过部分步骤）

以下场景可跳过**推荐**步骤（**必须**步骤不可跳过）：

| 场景 | 可跳过步骤 | 理由 |
|------|-----------|------|
| 单个查询接口、无 DB 校验 | `/test-data`、`/data-verify`、`/assertion-design` | 查询接口的断言和数据较简单 |
| 已有类似测试、只加参数化 | `/case-design`、`/test-data` | 直接追加 parametrize 数据 |
| 修复已有测试的 bug | `/case-design`、`/test-data`、`/assertion-design` | 用 `/debug-failure` 定位后直接修 |
| 纯单元测试、函数签名简单 | `/data-verify`、`/report-decorate` | 单元测试的校验和报告较简单 |

**判断标准**：涉及的测试函数 ≤ 3 个且不涉及写操作，可走快速通道。

> **提示**：走快速通道时，`/case-design` 会自动切换为**快速模式**（只输出追溯表 + 精简用例表格 + 一段话自动化建议），无需手动指定。

---

## 四、各技能职责速查

| 技能 | 职责 | 输出 |
|------|------|------|
| `/case-design` | 设计用例清单，覆盖正常/边界/权限/幂等等多维度（D/G/H/U/E 编号体系） | 用例表格 + 自动化建议 |
| `/test-data` | 设计测试数据，YAML/JSON/parametrize/faker | 数据文件示例 + 清理策略 |
| `/write-tests` | 生成 pytest 代码，含 fixture/helper/校验 | 完整可运行代码 |
| `/assertion-design` | 设计断言策略，避免只断言状态码或过度断言 | 断言清单 + helper |
| `/data-verify` | 设计校验方案（DB 校验 / Mock 调用验证），含清理策略 | 校验断言代码 |
| `/report-decorate` | 补全报告注解，含 step/attachment/severity | 改造后的代码 |
| `/spec-review` | 审查 Spec 文档质量（完整性/一致性/可测试性） | 审查报告 + 改进建议 |
| `/mock-setup` | 为外部依赖配置 Mock 服务 | Mock 配置 + fixture + 测试代码 |
| `/contract-test` | 为接口生成契约测试（JSON Schema 校验） | Schema 文件 + 契约测试代码 |
| `/analyze-ci-failures` | 分析 CI 失败结果，识别模式，输出 spec/测试改进建议 | 失败分析报告 + 行动清单 |
| `/debug-failure` | 失败归类 + 根因分析 + 最小修复方案 | 修复代码 |
| `/spec-diff` | 分析 Spec 变更对现有测试的影响，定位需同步修改的函数 | 变更影响报告 + 更新清单 |
| `/compliance-check` | 合规自检：扫描写操作用例是否缺校验 | 缺失清单 + 补全方案 |

---

## 五、执行原则

0. **先对齐 specs/需求，再设计用例** — 不跳过需求追溯
1. **先出用例清单，确认后再写代码** — 不跳过 `/case-design`
2. **写完代码必须补报告注解** — `@allure.title` 永远是第一个装饰器
3. **写/改/删操作必须有校验** — 不能只断言接口返回值
4. **新增测试文件后必须更新 `{{RUN_SCRIPT_NAME}}.ps1` / `{{RUN_SCRIPT_NAME}}.sh`**
5. **失败用 `/debug-failure` 排查** — 不要直接猜测修改代码
6. **收尾必须跑 `/compliance-check`** — 确保校验无遗漏
7. **生成的代码必须有 type hints + docstring** — 不符合代码质量标准的代码视为不合格
8. **使用 Factory/Builder 模式构建测试数据** — 不在测试函数内硬编码大段 dict
9. **断言必须携带完整上下文** — `f"期望={expected}, 实际={actual}, id={resource_id}"`

---

现在请按照以上规范开始工作：

$ARGUMENTS
