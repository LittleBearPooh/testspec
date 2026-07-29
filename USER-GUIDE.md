# TestSpec 使用说明书

> **版本**：v1.2.0  
> **适用对象**：测试工程师（含新手）、QA 团队成员、AI 辅助测试开发者  
> **最后更新**：2026-07

---

## 目录

- [第一部分：入门篇](#第一部分入门篇)
  - [1. 框架简介](#1-框架简介)
  - [2. 前置准备](#2-前置准备)
  - [3. 5 分钟快速体验](#3-5-分钟快速体验)
- [第二部分：脚手架详解](#第二部分脚手架详解)
  - [4. init.py 交互式引导](#4-initpy-交互式引导)
  - [5. 生成的项目结构](#5-生成的项目结构)
- [第三部分：配置系统](#第三部分配置系统)
  - [6. 变量系统](#6-变量系统)
  - [7. 敏感配置管理](#7-敏感配置管理)
  - [8. variable_loader API](#8-variable_loader-api)
- [第四部分：工具层](#第四部分工具层)
  - [9. HTTP 客户端](#9-http-客户端)
  - [10. 数据库客户端](#10-数据库客户端)
  - [11. 日志系统](#11-日志系统)
  - [12. 数据读取器](#12-数据读取器)
- [第五部分：8 步工作流（核心）](#第五部分8-步工作流核心)
  - [13. 工作流总览](#13-工作流总览)
  - [14. 步骤 0：规格对齐](#14-步骤-0规格对齐)
  - [15. 步骤 1：用例设计](#15-步骤-1用例设计)
  - [16. 步骤 2：测试数据](#16-步骤-2测试数据)
  - [17. 步骤 3：代码编写](#17-步骤-3代码编写)
  - [18. 步骤 4：断言设计](#18-步骤-4断言设计)
  - [19. 步骤 5：数据验证](#19-步骤-5数据验证)
  - [20. 步骤 6：报告装饰](#20-步骤-6报告装饰)
  - [21. 步骤 7：合规自检](#21-步骤-7合规自检)
  - [22. 辅助命令：失败排查](#22-辅助命令失败排查)
- [第六部分：编写规格文档](#第六部分编写规格文档)
  - [23. spec-template 解读](#23-spec-template-解读)
  - [24. spec-example 走读](#24-spec-example-走读)
  - [25. spec 最佳实践](#25-spec-最佳实践)
- [第七部分：运行与管理](#第七部分运行与管理)
  - [26. pytest 配置](#26-pytest-配置)
  - [27. conftest.py 体系](#27-conftestpy-体系)
  - [28. 执行脚本](#28-执行脚本)
  - [29. 工具脚本](#29-工具脚本)
- [第八部分：进阶指南](#第八部分进阶指南)
  - [30. 多测试类型混合](#30-多测试类型混合)
  - [31. 多数据库配置](#31-多数据库配置)
  - [32. 并行执行](#32-并行执行)
  - [33. CI/CD 集成](#33-cicd-集成)
  - [34. 定制与扩展](#34-定制与扩展)
- [第九部分：FAQ 与排错](#第九部分faq-与排错)
  - [35. 常见问题](#35-常见问题)
  - [36. 错误排查清单](#36-错误排查清单)
- [附录](#附录)
  - [A. 完整命令速查表](#a-完整命令速查表)
  - [B. 模板引擎语法参考](#b-模板引擎语法参考)
  - [C. WRITE_KEYWORDS 完整列表](#c-write_keywords-完整列表)
  - [D. 推荐项目结构参考](#d-推荐项目结构参考)

---

# 第一部分：入门篇

## 1. 框架简介

### 1.1 TestSpec 是什么

TestSpec 是一个**规格优先的测试自动化工程化框架**。它的核心理念可以用一句话概括：

> **先写规格文档，再写测试代码。**

传统做法是工程师凭直觉直接写测试代码（"感觉编码"），容易导致覆盖遗漏、无法追溯、AI 幻觉放大等问题。TestSpec 要求在写任何测试代码之前，先用结构化的规格文档（Spec）描述清楚"要验证什么"。

### 1.2 TestSpec 解决什么问题

| 问题 | TestSpec 的解决方式 |
|---|---|
| 测试覆盖遗漏 | 8 步工作流强制覆盖正常/异常/边界/权限等维度 |
| 代码与需求脱节 | spec 文档是"单一真相来源"，代码从 spec 派生 |
| AI 生成代码质量差 | AI 拿到结构化 spec 而非模糊提示，输出质量大幅提升 |
| 写操作没有 DB 校验 | 合规自检脚本作为收尾门禁，自动扫描缺失 |
| 测试报告不可观测 | 每个步骤必须有 allure.attach，报告包含完整上下文 |
| 敏感信息泄露 | 两层变量系统（variables + override），凭据不进 git |

### 1.3 核心理念一览

```
Spec（规格文档）→ Cases（用例设计）→ Data（测试数据）→ Code（测试代码）
     → Assertion（断言设计）→ Verify（数据验证）→ Report（报告装饰）→ Compliance（合规自检）
```

- **`specs/` 目录**是整条链路的起点，代码的存在是为了执行规格
- **8 步工作流**确保每个测试用例都有完整的覆盖维度、数据策略、断言方案和合规检查
- **AI 在每个步骤中严格按照规范执行**，不会"自由发挥"

### 1.4 支持的测试类型

| 类型 | 说明 | 步骤 5（数据验证）含义 |
|---|---|---|
| **api** | HTTP 接口自动化测试 | DB 查询验证 |
| **unit** | 单元测试 | Mock 调用验证 |
| **integ** | 集成测试 | 系统状态验证（DB 或 API） |
| **e2e** | 端到端测试 | 多层验证（API + DB + 副作用） |

### 1.5 支持的数据库

| 数据库 | Python 驱动 | 条件块标识 |
|---|---|---|
| SQL Server | pymssql + DBUtils | `DB_SQLSERVER` |
| MySQL | PyMySQL + DBUtils | `DB_MYSQL` |
| PostgreSQL | psycopg2 + DBUtils | `DB_POSTGRESQL` |
| SQLite | sqlite3（标准库） | `DB_SQLITE` |

---

## 2. 前置准备

在开始使用 TestSpec 之前，请确保你的开发环境满足以下条件。

### 2.1 Python 环境

TestSpec 要求 **Python 3.9 或更高版本**。

```bash
# 检查 Python 版本
python --version
# 或
python3 --version
```

> 💡 **提示**：推荐使用 Python 3.11+，以获得更好的类型提示支持和性能。

### 2.2 虚拟环境（强烈推荐）

为了避免包版本冲突，建议为每个测试项目创建独立的虚拟环境：

```bash
# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
```

> ⚠️ **注意**：激活虚拟环境后，终端提示符前会出现 `(.venv)` 标记。后续所有 `pip install` 命令都应在虚拟环境中执行。

### 2.3 pip 包管理器

确保 pip 已安装并更新到最新版本：

```bash
python -m pip install --upgrade pip
```

### 2.4 AI 工具（二选一）

TestSpec 使用 Claude Code 作为 AI 编程工具：

- 安装 Claude Code CLI
- `.claude/commands/` 目录下的文件会自动注册为 slash command
- 使用 `/case-design`、`/write-tests` 等命令触发工作流

> 💡 **提示**：框架脚手架会生成 15 个技能命令文件，涵盖 8 步工作流和扩展功能。

### 2.5 Git（推荐）

虽然不是强制要求，但强烈建议使用 Git 管理测试项目：

```bash
git init
git add .
git commit -m "init: TestSpec 项目初始化"
```

### 2.6 环境检查清单

在进入下一步之前，确认以下项目：

- [x] Python 3.9+ 已安装
- [x] 虚拟环境已创建并激活
- [x] pip 已更新
- [x] Claude Code 已安装
- [x] （可选）Git 已安装

---

## 3. 5 分钟快速体验

本节用一个完整的流程，带你从零到运行第一个测试。

### 3.1 运行脚手架

```bash
python testspec/init.py
```

你会看到一个交互式引导界面：

```
========================================================
  TestSpec 框架脚手架 v1.2.0
  规格优先的测试自动化工程化框架
========================================================
```

### 3.2 按提示输入项目信息

按照交互式引导依次输入（括号内为本示例的选择）：

| 步骤 | 问题 | 示例输入 |
|---|---|---|
| 1/8 | 项目名称 | `order-service-tests` |
| 2/8 | 测试类型 | `1`（API 测试） |
| 3/8 | 语言框架 | `1`（Python/pytest） |
| 4/8 | 数据库 | `Y`，然后选 `2`（MySQL） |
| 5/8 | 报告工具 | `1`（Allure） |
| 6/8 | CI/CD 系统 | `1`（GitHub Actions） |
| 7/8 | 业务线 | `order,payment` |
| 8/8 | 输出与语言 | `./order-service-tests`，`1`（中文） |

确认信息后，脚手架开始生成项目。

### 3.3 安装依赖

```bash
cd order-service-tests
pip install -r requirements.txt
```

### 3.4 配置敏感变量

```bash
cp variables_override.yaml.template variables_override.yaml
```

编辑 `variables_override.yaml`，填入真实的数据库密码和测试账号密码：

```yaml
test_accounts:
  default:
    password: "your-test-password"

auth:
  default:
    password: "your-auth-password"

db:
  default:
    host: "192.168.1.100"
    user: "test_user"
    password: "your-db-password"
```

> ⚠️ **注意**：`variables_override.yaml` 已在 `.gitignore` 中，不会被提交到 Git。**永远不要把真实密码写入 `variables.yaml`**。

### 3.5 编写第一个规格文档

在 `specs/order/` 下创建 `create-order.md`，参考 `specs/spec-template.md` 的格式：

```markdown
# 创建订单

## 基本信息

- **测试函数名**: `test_CreateOrder_Success`
- **业务线/模块**: order
- **用例类型**: e2e
- **优先级**: P0
- **所在文件**: `testcase/order/test_order_creation_e2e.py`

## 用例说明

> 验证正常下单后订单在数据库中的状态为 Pending

## 测试步骤

### 步骤 1：创建订单

- **接口**: `POST /api/v1/orders`
- **请求参数**: `{"product_id": "PROD_001", "quantity": 2}`
- **预期响应**: HTTP 201，返回 order_id

## 数据验证

### 数据库校验

- **目标表**: `Orders`
- **查询条件**: `WHERE OrderId = %s`
- **校验字段**: Status == 1 (Pending), ProductId == "PROD_001"
```

### 3.6 使用 AI 工作流生成测试

在 Claude Code 中，依次调用以下命令：

```
# 步骤 1：用例设计（AI 读取 specs/ 后生成用例清单）
/case-design order 创建订单

# 步骤 3：生成测试代码
/write-tests 根据用例清单生成 testcase/order/test_order_creation_e2e.py，
  token 从 order_service_tests/client/token_store.py 获取

# 步骤 5：补全数据库校验
/data-verify testcase/order/test_order_creation_e2e.py

# 步骤 6：补全报告注解
/report-decorate testcase/order/test_order_creation_e2e.py

# 步骤 7：合规自检
/compliance-check
```

### 3.7 运行测试

```bash
# 运行单个测试文件
pytest testcase/order/test_order_creation_e2e.py -v

# 或使用执行脚本（Windows）
.\run_order_service_tests.ps1

# 或使用执行脚本（Linux/macOS）
bash run_order_service_tests.sh
```

### 3.8 查看报告

```bash
# 生成 Allure 报告
pytest testcase --alluredir=reports/allure-results
allure serve reports/allure-results
```

> 💡 **提示**：查看 Allure 报告需要安装 [Allure CLI](https://docs.qameta.io/allure/#_installing_a_commandline)。

---

# 第二部分：脚手架详解

## 4. init.py 交互式引导

`init.py` 是 TestSpec 的脚手架脚本，用于一键生成完整的测试项目结构。它**没有外部依赖**，只需要 Python 3.9+ 即可运行。

### 4.1 运行方式

```bash
python testspec/init.py
```

### 4.2 步骤 1/8：项目名称

```
[步骤 1/8] 项目基本信息
  请输入项目名称（英文连字符格式，例如：order-service-tests）:
```

**规则**：
- 必须以小写字母开头
- 只允许小写字母、数字和连字符 `-`
- 推荐使用 `xxx-tests` 或 `xxx-test` 后缀

**示例**：

| 输入 | 自动派生 |
|---|---|
| `order-service-tests` | snake_case: `order_service_tests`<br>PascalCase: `OrderServiceTests`<br>Title: `Order Service Tests` |
| `payment-gateway-tests` | snake_case: `payment_gateway_tests`<br>PascalCase: `PaymentGatewayTests` |

> ⚠️ **注意**：项目名称会贯穿整个生成项目，用于类名、日志文件名、执行脚本名等。请谨慎选择。

### 4.3 步骤 2/8：测试类型

```
[步骤 2/8] 测试类型（决定技能模板和工具桩的内容）

  请选择测试类型：
    1. HTTP 接口自动化测试（含 DB 校验）
    2. 单元测试（含 Mock 验证）
    3. 集成测试（含系统状态验证）
    4. 端到端测试（完整用户旅程）
  可多选，逗号分隔（例如：1 或 1,4）:
```

**选择建议**：

| 场景 | 推荐选择 |
|---|---|
| 只做接口测试 | `1` |
| 接口 + 端到端 | `1,4` |
| 全栈测试 | `1,2,3,4` |
| 只做单元测试 | `2` |

> 💡 **提示**：可以选多个类型，框架会生成对应的条件模板。但如果选择了 `api`、`integ` 或 `e2e`，后续步骤会建议配置数据库。

### 4.4 步骤 3/8：编程语言与框架

```
[步骤 3/8] 编程语言与测试框架

  请选择语言与框架：
    1. Python / pytest（推荐，工具桩完整） (默认)
    2. Python / unittest
    3. JavaScript / Jest（工具桩需手动移植）
    4. Java / JUnit5（工具桩需手动移植）
  请选择 [1]:
```

**选择建议**：

| 选项 | 状态 | 说明 |
|---|---|---|
| Python / pytest | ✅ 完整支持 | 所有模板和工具桩均为原生 Python |
| Python / unittest | ⚠️ 部分支持 | 工具桩可用，但代码模板以 pytest 风格编写 |
| JavaScript / Jest | ❌ 仅结构 | 只生成目录结构和 AI 规则，工具桩需手动移植 |
| Java / JUnit5 | ❌ 仅结构 | 同上 |

> ⚠️ **注意**：当前版本只有 Python/pytest 提供完整的工具桩模板。选择其他语言后，控制台会显示警告提示。

### 4.5 步骤 4/8：数据库配置

```
[步骤 4/8] 数据库配置
  是否需要数据库校验？ (Y/n):
```

如果选择"是"：

```
  请选择数据库类型：
    1. SQL Server（pymssql） (默认)
    2. MySQL（PyMySQL）
    3. PostgreSQL（psycopg2）
    4. SQLite（标准库，无需安装驱动）
    5. 暂不配置（后续手动添加）
  请选择 [1]:
```

**选择建议**：

| 场景 | 推荐 |
|---|---|
| 被测系统使用 SQL Server | `1` |
| 被测系统使用 MySQL | `2` |
| 被测系统使用 PostgreSQL | `3` |
| 本地开发/原型验证 | `4`（SQLite，零配置） |
| 只做只读查询测试 | `5`（不需要 DB 校验） |

> 💡 **提示**：如果选择了 API 测试或集成测试，脚手架会默认建议开启数据库校验（`Y`），因为写操作接口（POST/PUT/DELETE）强烈建议验证数据是否正确落库。

### 4.6 步骤 5/8：报告工具

```
[步骤 5/8] 测试报告工具

  请选择报告工具：
    1. Allure（推荐） (默认)
    2. pytest-html
    3. Allure + pytest-html
  请选择 [1]:
```

| 选项 | 说明 | 适用场景 |
|---|---|---|
| Allure | 功能最强，支持步骤/附件/时间线/环境信息 | 正式项目，需要给团队展示报告 |
| pytest-html | 轻量级，单个 HTML 文件 | 简单项目，CI 快速查看 |
| Both | 同时生成两种报告 | 需要兼容不同查看方式 |

### 4.7 步骤 6/8：CI/CD 系统

```
[步骤 6/8] CI/CD 系统

  请选择 CI/CD 系统：
    1. GitHub Actions (默认)
    2. GitLab CI
    3. 暂不配置
  请选择 [1]:
```

**选择建议**：

| 场景 | 推荐 |
|---|---|
| 项目托管在 GitHub | `1`（GitHub Actions） |
| 项目托管在 GitLab | `2`（GitLab CI） |
| 本地开发/暂不需要 CI | `3` |

> 💡 **提示**：选择 CI 系统后，脚手架会自动生成对应的 CI 配置文件（如 `.github/workflows/` 或 `.gitlab-ci.yml`）。

### 4.8 步骤 7/8：业务线

```
[步骤 7/8] 业务线 / 功能模块
  请输入业务线或功能模块名称（英文，逗号分隔，例如：order,payment,inventory）:
```

**规则**：
- 使用英文小写
- 多个业务线用逗号分隔
- 不输入则默认 `default`

**示例**：

| 输入 | 生成的目录 |
|---|---|
| `order,payment` | `testcase/order/`、`testcase/payment/`、`specs/order/`、`specs/payment/` |
| `auth,user-center` | `testcase/auth/`、`testcase/user-center/`、`specs/auth/`、`specs/user-center/` |

### 4.9 步骤 8/8：输出与语言

```
[步骤 8/8] 输出与语言
  请输入生成项目的目标目录 [./order-service-tests]:

  文档语言：
    1. 中文 (默认)
    2. English
  请选择 [1]:
```

默认使用 `./<项目名称>` 作为输出目录。可以指定任意路径。

文档语言决定脚手架生成的模板内容使用中文还是英文。

### 4.10 确认与生成

所有步骤完成后，脚手架会显示参数汇总：

```
========================================================
  参数确认：
    项目名称：order-service-tests
    测试类型：api
    语言框架：python / pytest
    数据库  ：MySQL（PyMySQL）
    报告工具：allure
    CI 系统 ：github
    业务线  ：order, payment
    输出目录：./order-service-tests
    文档语言：zh
========================================================
  确认生成？ (Y/n):
```

输入 `Y` 或直接回车即可开始生成。生成完成后会显示所有文件清单和下一步操作指引。

---

## 5. 生成的项目结构

脚手架生成的项目结构如下（以 API 测试 + MySQL + Allure 为例）：

```
order-service-tests/
│
├── CLAUDE.md                          ← AI 行为规则 + 架构指南（给 AI 和新成员的地图）
├── testspec.json                    ← TestSpec 版本标记
│
├── .claude/commands/                ← Claude Code 技能命令（15 个）
│   ├── test-workflow.md             ← 8 步工作流总览
│   ├── case-design.md               ← 用例设计
│   ├── test-data.md                 ← 测试数据设计
│   ├── write-tests.md               ← 代码编写
│   ├── assertion-design.md          ← 断言设计
│   ├── data-verify.md               ← 数据验证
│   ├── report-decorate.md           ← 报告装饰
│   ├── compliance-check.md          ← 合规自检
│   ├── spec-review.md               ← 规约审查
│   ├── mock-setup.md                ← Mock 服务搭建
│   ├── contract-test.md             ← 契约测试生成
│   ├── analyze-ci-failures.md       ← CI 失败分析
│   ├── spec-diff.md                 ← 规约差异对比
│   ├── AutomatedTesting.md          ← 智能调度器（分析输入自动编排技能）
│   └── debug-failure.md             ← 失败排查
│
├── config/
│   └── variable_loader.py           ← 变量加载器（深度合并 + 三级查找）
│
├── utils/
│   ├── http_client.py               ← HTTP 客户端（sentinel 断言模式）
│   ├── db_client.py                 ← 数据库客户端（连接池 + 参数化 SQL）
│   ├── logger.py                    ← 日志工厂（文件写入 + 敏感脱敏）
│   ├── data_reader.py               ← YAML/JSON/Excel 数据读取
│   ├── data_factory.py              ← 测试数据工厂（唯一性 + faker）
│   ├── contract_checker.py          ← 契约校验工具
│   ├── assertions.py                ← 通用断言辅助
│   ├── poll_helper.py               ← 轮询等待辅助（替代裸 sleep）
│   └── mock_server.py               ← Mock 服务
│
├── order_service_tests/             ← 项目专属模块（需自行实现）
│
├── testcase/                        ← 测试用例目录（唯一正式用例目录）
│   ├── conftest.py                  ← 测试级 fixtures
│   ├── order/                       ← order 业务线
│   │   └── __init__.py
│   └── payment/                     ← payment 业务线
│       └── __init__.py
│
├── specs/                           ← 规格文档目录
│   ├── spec-template.md             ← 规格文档模板
│   ├── spec-example.md              ← 规格文档示例
│   ├── registry.yaml                ← Spec 注册表
│   ├── order/                       ← order 业务线的 spec
│   └── payment/                     ← payment 业务线的 spec
│
├── mock/                            ← Mock 服务目录
│   ├── mock_server.py
│   └── mock_responses/
│       └── payment.json
│
├── data/                            ← 测试数据目录
│   ├── yaml/
│   ├── json/
│   └── excel/
│
├── scripts/                         ← 工具脚本（10 个）
│   ├── check_compliance.py          ← 合规自检脚本
│   ├── validate_specs.py            ← Spec 格式校验
│   ├── check_coverage.py            ← 覆盖率检查
│   ├── detect_flaky.py              ← 不稳定用例检测
│   ├── generate_metrics.py          ← 测试指标报告
│   ├── generate_skeletons.py        ← 代码骨架生成
│   ├── generate_clients.py          ← 客户端代码生成
│   ├── import_openapi.py            ← OpenAPI 导入
│   ├── mcp_server.py                ← MCP 服务
│   └── spec_diff.py                 ← Spec 差异分析
│
├── ci/                              ← CI/CD 配置
│   ├── testspec-ci.yaml             ← CI 流水线定义
│   └── pre-commit-config.yaml       ← pre-commit 钩子
├── docker/                          ← Docker 配置（有 DB 且非 SQLite 时生成）
│   └── docker-compose.test.yml
├── schemas/                         ← Schema 文档
│   └── README.md
│
├── logs/                            ← 运行日志（gitignored）
│   └── .gitkeep
├── reports/                         ← 测试报告（gitignored）
│   └── .gitkeep
│
├── variables.yaml                   ← 非敏感默认变量（提交 git）
├── variables_override.yaml.template ← 敏感变量结构指南（提交 git）
├── conftest.py                      ← 根级 conftest（Allure + 失败 attach）
├── pytest.ini                       ← pytest 配置
├── run_order_service_tests.ps1      ← PowerShell 执行脚本
├── run_order_service_tests.sh       ← Bash 执行脚本
├── requirements.txt                 ← Python 依赖
└── .gitignore                       ← Git 忽略规则
```

### 各目录职责速查

| 目录/文件 | 职责 | 谁维护 |
|---|---|---|
| `CLAUDE.md` | AI 行为约束，告诉 AI "什么能做、什么不能做" | 框架生成，团队按需修改 |
| `.claude/commands/` | AI 技能命令定义（15 个命令） | 框架生成，升级时重新生成 |
| `config/` | 变量加载器 | 框架生成，一般不修改 |
| `utils/` | 通用工具层（9 个模块） | 框架生成，团队可扩展 |
| `<项目名>/` | 项目专属模块 | **项目团队自行实现** |
| `testcase/` | 测试代码 | **项目团队编写** |
| `specs/` | 规格文档 | **项目团队编写** |
| `data/` | 测试数据文件 | 项目团队维护 |
| `scripts/` | 工具脚本（10 个） | 框架生成，团队可扩展 |
| `mock/` | Mock 服务与响应数据 | 框架生成，团队可扩展 |
| `variables.yaml` | 非敏感配置 | 项目团队维护 |
| `variables_override.yaml` | 敏感配置 | 项目团队维护（不进 git） |

> ⚠️ **注意**：`<项目名>/` 目录（如 `order_service_tests/`）由脚手架创建，但**不会生成任何代码**。你需要在其中自行实现接口封装类、配置类和 token 管理模块（建议创建 `client/` 子目录）。

---

# 第三部分：配置系统

## 6. 变量系统

TestSpec 的变量系统是整个框架中**最重要的设计之一**。它通过两层文件分离敏感与非敏感配置，通过深度合并让覆盖变得简单直观。

### 6.1 两个文件

| 文件 | 职责 | 是否提交 git |
|---|---|---|
| `variables.yaml` | 存放**非敏感**默认值（base_url、超时时间、DB 端口等） | ✅ 提交 |
| `variables_override.yaml` | 存放**敏感**值（DB 密码、API 密钥、测试账号密码等） | ❌ gitignored |

### 6.2 深度合并规则

当两个文件存在同名 key 时，`variables_override.yaml` 的值会**深度合并**覆盖 `variables.yaml`：

**variables.yaml**（默认值）：
```yaml
db:
  default:
    host: "localhost"
    port: 3306
    user: "test_user"
    password: ""          # 空字符串，留给 override
    name: "test_db"
```

**variables_override.yaml**（敏感覆盖）：
```yaml
db:
  default:
    host: "192.168.1.100"    # 覆盖 host
    user: "real_user"        # 覆盖 user
    password: "S3cret!"      # 覆盖 password
    # port 和 name 没有写，保持 variables.yaml 的 3306 和 test_db
```

**合并后的结果**：
```yaml
db:
  default:
    host: "192.168.1.100"    # ← override
    port: 3306               # ← 来自 variables.yaml
    user: "real_user"        # ← override
    password: "S3cret!"      # ← override
    name: "test_db"          # ← 来自 variables.yaml
```

> 💡 **提示**：深度合并的意思是——如果两边都是 dict，则递归合并；否则 override 直接覆盖。这意味着你不需要在 override 中重复写所有字段，只需要写需要覆盖的。

### 6.3 override 文件查找顺序

当代码执行 `from config.variable_loader import get` 时，加载器按以下顺序查找 `variables_override.yaml`：

```
1. 环境变量 VARIABLES_OVERRIDE_PATH 指定的路径
   ↓ （如果环境变量没设置）
2. 从项目根目录向上逐级查找 variables_override.yaml
   ↓ （如果向上找不到）
3. 使用项目根目录下的 variables_override.yaml（文件可以不存在）
```

| 场景 | 使用哪种方式 |
|---|---|
| 本地开发 | 方式 2：自动找到项目根目录的 override 文件 |
| CI 执行机 | 方式 1：通过环境变量注入 override 文件路径 |
| override 文件不存在 | 正常启动，只使用 variables.yaml 的值 |

---

## 7. 敏感配置管理

### 7.1 什么算"敏感"

以下内容应该放在 `variables_override.yaml` 中：

- 数据库密码（`db.default.password`）
- 数据库 host/user（生产/预发布环境）
- 测试账号密码（`test_accounts.default.password`）
- 认证密码（`auth.default.password`）
- API 密钥/Secret
- SMTP 授权码

以下内容可以放在 `variables.yaml` 中：

- base_url
- 超时时间
- 数据库端口
- 数据库名
- 测试环境 URL

### 7.2 模板文件同步规则

每当 `variables_override.yaml` 新增或删除一个敏感 key 时，**必须同步**更新 `variables_override.yaml.template`：

```yaml
# variables_override.yaml.template
# 用 <FILL_IN> 占位，展示结构但不暴露真实值

db:
  default:
    host: "<FILL_IN>"
    user: "<FILL_IN>"
    password: "<FILL_IN>"
```

**两个文件的结构（key 路径）必须保持一致**，只是值不同：
- `variables_override.yaml` — 真实值
- `variables_override.yaml.template` — `<FILL_IN>` 占位符

> ⚠️ **注意**：`variables_override.yaml.template` 需要提交到 git（它只展示配置结构，不含真实凭据），而 `variables_override.yaml` 绝对不能提交。

### 7.3 CI 场景配置

在 CI 执行机上，override 文件通常不在项目目录内。通过环境变量指定路径：

```bash
# Jenkins / GitLab CI / GitHub Actions
export VARIABLES_OVERRIDE_PATH=/etc/secrets/variables_override.yaml
pytest testcase/ --alluredir=reports/allure-results
```

也可以在 CI 中动态生成 override 文件：

```bash
# CI pipeline 脚本示例
cat > /tmp/override.yaml << EOF
db:
  default:
    host: "${DB_HOST}"
    user: "${DB_USER}"
    password: "${DB_PASSWORD}"
test_accounts:
  default:
    password: "${TEST_PASSWORD}"
EOF

export VARIABLES_OVERRIDE_PATH=/tmp/override.yaml
pytest testcase/
```

---

## 8. variable_loader API

`config/variable_loader.py` 提供了三种读取变量的方式。

### 8.1 `get(key, default)` — 读取顶层变量

```python
from config.variable_loader import get as var_get

base_url = var_get("base_url", "http://localhost")
timeout = var_get("timeout", 30)
```

- `key`：顶层 key 名称
- `default`：key 不存在时的默认值
- 返回值：变量值

> 💡 **提示**：`get()` 只能读取顶层 key。要读取嵌套值（如 `db.default.host`），请使用 `get_nested()`。

### 8.2 `get_nested(path, default)` — 读取嵌套变量

```python
from config.variable_loader import get_nested as var_get_nested

# 读取 db.default 下所有字段（返回 dict）
db_cfg = var_get_nested("db.default")
# db_cfg = {"host": "192.168.1.100", "port": 3306, "user": "...", ...}

# 读取测试账号
account = var_get_nested("test_accounts.default")
# account = {"username": "test@example.com", "password": "..."}

# 读取特定字段
db_host = var_get_nested("db.default.host")
# db_host = "192.168.1.100"

# 路径不存在时返回默认值
missing = var_get_nested("nonexistent.path", "fallback")
# missing = "fallback"
```

- `path`：用点号 `.` 分隔的嵌套路径
- `default`：路径不存在时的默认值

### 8.3 `_config` — 直接访问合并后的字典

```python
from config.variable_loader import _config as project_vars

timeout = project_vars.get("timeout", 30)
all_keys = list(project_vars.keys())
```

> ⚠️ **注意**：`_config` 是一个全局字典，在模块首次 import 时自动加载。直接修改 `_config` 的内容可能会影响其他模块，建议只读不写。

### 8.4 加载时机

变量在模块首次被 import 时**自动加载**（`_load()` 在模块末尾被调用），无需手动触发：

```python
# 这行 import 执行后，变量就已经加载好了
from config.variable_loader import get
```

---

# 第四部分：工具层

## 9. HTTP 客户端

`utils/http_client.py` 提供了 `HttpClient` 类，封装了 HTTP 请求的常用功能。

### 9.1 基本用法

```python
from utils.http_client import HttpClient

# 创建客户端（base_url 和 timeout 自动从 variables.yaml 读取）
client = HttpClient()

# 也可以显式指定
client = HttpClient(base_url="https://api.example.com", timeout=60)
```

### 9.2 发送请求

```python
# GET 请求
resp = client.get("/api/users")

# POST 请求
resp = client.post("/api/orders", json={"product_id": 1001, "quantity": 2})

# PUT 请求
resp = client.put("/api/orders/123", json={"status": "shipped"})

# PATCH 请求
resp = client.patch("/api/users/1", json={"name": "New Name"})

# DELETE 请求
resp = client.delete("/api/orders/123")
```

### 9.3 Sentinel 断言模式（核心特性）

`HttpClient` 的每个请求方法都有一个 `assert_status` 参数，使用**哨兵模式**区分三种语义：

```python
# 1. 不传 assert_status → 自动断言状态码为 200
client.get("/api/users")                    # 如果返回 404，自动抛出 AssertionError

# 2. 传指定状态码 → 断言该状态码
client.post("/api/orders", json={...}, assert_status=201)

# 3. 传列表 → 断言状态码在列表中
client.delete("/api/items/1", assert_status=[200, 204])

# 4. 传 None → 关闭自动断言，手动处理
resp = client.get("/api/maybe-404", assert_status=None)
if resp.status_code == 404:
    # 手动处理 404 场景
    pass
```

**断言失败时的错误信息**包含响应体预览（前 500 字符），方便快速定位问题：

```
AssertionError: GET /api/users — 期望状态码 [200]，实际 500。
响应体：{"code": 500, "message": "Internal Server Error", ...}
```

### 9.4 路径拼接规则

```python
# path 以 / 开头 → 自动拼接 base_url
client.get("/api/users")
# → https://api.example.com/api/users

# path 不以 / 开头 → 视为完整 URL
client.get("https://other-service.com/health")
# → https://other-service.com/health
```

### 9.5 上下文管理器

`HttpClient` 支持 `with` 语法，自动关闭连接：

```python
with HttpClient() as client:
    resp = client.get("/api/users")
# 离开 with 块后，Session 自动关闭
```

### 9.6 与 conftest 的集成

在 `testcase/conftest.py` 中，`http_client` 是一个 session 级 fixture：

```python
# 在测试函数中直接使用
def test_example(http_client):
    resp = http_client.get("/api/users")
    assert resp.json()["code"] == 0
```

根级 `conftest.py` 还注册了 `_track_last_response` fixture（autouse），在测试失败时自动将最后一次 HTTP 响应 attach 到 Allure 报告。

---

## 10. 数据库客户端

`utils/db_client.py` 提供了 `DbClient` 类和 `get_db()` 工厂函数。

### 10.1 基本用法

```python
from utils.db_client import get_db

# 获取默认数据库客户端
db = get_db("default")

# 获取其他数据库
secondary_db = get_db("secondary")
```

`get_db()` 的参数对应 `variables.yaml` 中 `db` 节点下的 key：

```yaml
db:
  default:     # → get_db("default")
    host: "..."
    port: 3306
    ...
  secondary:   # → get_db("secondary")
    host: "..."
    ...
```

### 10.2 查询操作

```python
# query() — 返回所有匹配行（list[dict]）
rows = db.query("SELECT * FROM Orders WHERE Status = %s", (1,))
for row in rows:
    print(row["OrderId"], row["Status"])

# query_one() — 返回第一行（dict），无结果返回 None
row = db.query_one("SELECT * FROM Orders WHERE OrderId = %s", (order_id,))
if row is None:
    print("订单不存在")
else:
    print(f"订单状态: {row['Status']}")
```

### 10.3 写操作

```python
# execute() — 执行 INSERT/UPDATE/DELETE，返回受影响行数
affected = db.execute(
    "UPDATE Orders SET Status = %s WHERE OrderId = %s",
    (2, order_id)
)
print(f"更新了 {affected} 行")
```

### 10.4 参数化 SQL（必须遵守）

```python
# ✅ 正确：参数化查询
db.query("SELECT * FROM Users WHERE Id = %s", (user_id,))

# ❌ 错误：字符串拼接 SQL（SQL 注入风险！）
db.query(f"SELECT * FROM Users WHERE Id = {user_id}")
```

> ⚠️ **注意**：SQL 必须使用 `%s` 占位符（SQLite 使用 `?`），配合参数元组传递。**永远不要**用 f-string 或 `%` 格式化拼接 SQL。

### 10.5 连接池

非 SQLite 数据库使用 DBUtils 连接池，配置如下：

| 参数 | 默认值 | 说明 |
|---|---|---|
| `mincached` | 1 | 初始空闲连接数 |
| `maxcached` | 5 | 最大空闲连接数 |
| `maxconnections` | 20 | 最大连接数 |
| `blocking` | True | 连接池满时是否阻塞等待 |

连接池是**懒初始化**的：第一次调用 `get_db()` 时才会创建连接池，后续调用复用已有池。连接池的创建是**线程安全**的（双重检查锁定模式）。

### 10.6 错误处理

`execute()` 方法在异常时自动回滚：

```python
try:
    db.execute("INSERT INTO Orders ...", (...))
except Exception:
    # execute() 内部已自动 rollback
    # 这里做额外处理（如记录日志）
    raise
```

---

## 11. 日志系统

`utils/logger.py` 提供了统一的项目日志功能。

### 11.1 基本用法

```python
from utils.logger import get_logger

logger = get_logger(__name__)

logger.info("测试开始")
logger.debug("请求参数：%s", params)
logger.error("断言失败：%s", error_msg)
```

> ⚠️ **注意**：框架要求统一使用 `from utils.logger import get_logger`，不要使用 `logging.getLogger()` 或其他方式创建 logger。

### 11.2 日志文件路径

日志文件按**日期 + 项目名**组织：

```
logs/
├── 2026-07-07/
│   ├── order.log          ← order 业务线的日志
│   ├── payment.log        ← payment 业务线的日志
│   ├── common.log         ← 通用日志
│   ├── pytest.log         ← pytest 框架日志
│   ├── order_gw0.log      ← xdist worker 0 的 order 日志
│   └── order_gw1.log      ← xdist worker 1 的 order 日志
└── 2026-07-08/
    └── ...
```

### 11.3 日志归属推断

`infer_project()` 函数会自动从模块名或 pytest nodeid 中推断日志归属：

```python
# 模块名包含 "order" → 写入 order.log
logger = get_logger("testcase.order.test_create")

# nodeid 包含 "payment" → 写入 payment.log
# pytest 自动传入 nodeid，无需手动指定
```

### 11.4 敏感字段脱敏

写日志时，以下字段名会被自动替换为 `"***"`：

```
authorization, access_token, refresh_token, id_token,
password, licensekey, license_key, clientsecret,
client_secret, token
```

脱敏是**递归**的——即使敏感字段嵌套在 dict 或 list 中也会被处理：

```python
logger.info("请求 headers：%s", headers)
# 输出：请求 headers：{"Authorization": "***", "Content-Type": "application/json"}
```

### 11.5 xdist 并行日志

使用 `pytest-xdist` 并行执行时，每个 worker 进程会写**独立的日志文件**（后缀 `_gwN`），避免多进程同时写同一文件导致日志行交叉乱序。

### 11.6 日志只写文件

日志**不会输出到控制台**，只写入文件。这是为了避免 CI 日志被大量调试信息污染。如果需要查看日志，请打开 `logs/` 目录下对应日期的文件。

---

## 12. 数据读取器

`utils/data_reader.py` 提供了三种数据文件的读取功能。

### 12.1 YAML 读取

```python
from utils.data_reader import read_yaml

cases = read_yaml("yaml/login_cases.yaml")
# 实际读取路径：<项目根>/data/yaml/login_cases.yaml
# 返回 list 或 dict（取决于 YAML 内容）
```

示例 YAML 文件（`data/yaml/login_cases.yaml`）：

```yaml
- id: normal_login
  username: "test@example.com"
  password: "Test123!"
  expected_code: 0

- id: wrong_password
  username: "test@example.com"
  password: "wrong"
  expected_code: 1001
  expected_message: "密码错误"
```

### 12.2 JSON 读取

```python
from utils.data_reader import read_json

cases = read_json("json/order_cases.json")
# 实际读取路径：<项目根>/data/json/order_cases.json
```

### 12.3 Excel 读取

```python
from utils.data_reader import read_excel

cases = read_excel("excel/test_cases.xlsx", sheet="Sheet1")
# 第一行为表头，返回 list[dict]
# 例如：[{"用例名": "正常下单", "参数": "...", "预期": "..."}, ...]
```

> 💡 **提示**：`read_excel` 需要安装 `openpyxl`，框架已在 `requirements.txt` 中包含。

### 12.4 配合 pytest.mark.parametrize

最常见的用法是将数据文件与 `@pytest.mark.parametrize` 配合：

```python
import pytest
from utils.data_reader import read_yaml

@pytest.mark.parametrize("case", read_yaml("yaml/login_cases.yaml"))
def test_login(case):
    """数据驱动的登录测试"""
    resp = client.post("/api/login", json={
        "username": case["username"],
        "password": case["password"],
    }, assert_status=None)

    assert resp.json()["code"] == case["expected_code"]
```

### 12.5 路径约定

所有路径都是**相对于 `data/` 目录**的：

| 调用 | 实际文件路径 |
|---|---|
| `read_yaml("yaml/a.yaml")` | `<项目根>/data/yaml/a.yaml` |
| `read_json("json/b.json")` | `<项目根>/data/json/b.json` |
| `read_excel("excel/c.xlsx")` | `<项目根>/data/excel/c.xlsx` |

---

# 第五部分：8 步工作流（核心）

## 13. 工作流总览

TestSpec 的核心工作流分为 8 个步骤（步骤 0-7），外加 1 个按需调用的辅助命令。

### 13.1 流程图

```
规格文档（specs/）
    │
    ▼ 步骤 0：规格对齐（读 spec，建立追溯表）
    │
    ▼ 步骤 1：用例设计（结构化用例清单）
    │
    ├──▶ 步骤 2：测试数据（YAML/参数化数据）[推荐]
    │
    ▼ 步骤 3：代码编写（pytest 代码框架）
    │
    ├──▶ 步骤 4：断言设计（断言策略）[推荐]
    │
    ▼ 步骤 5：数据验证（DB 校验 / Mock 验证）[写操作必须]
    │
    ▼ 步骤 6：报告装饰（Allure 注解）
    │
    ▼ 步骤 7：合规自检（门禁扫描）
    │
    ▼
可交付的测试套件
```

### 13.2 步骤速查表

| 步骤 | 命令 | 必须/推荐 | 核心产物 |
|---|---|---|---|
| — | `/AutomatedTesting` | **入口** | 执行计划（分析输入自动编排后续技能） |
| 0 | （内嵌在 `/case-design`） | **必须** | 需求追溯表 |
| 1 | `/case-design` | **必须** | 结构化用例清单 |
| 2 | `/test-data` | 推荐 | YAML 参数化数据 |
| 3 | `/write-tests` | **必须** | pytest 测试文件 |
| 4 | `/assertion-design` | 推荐 | 断言策略 + 代码 |
| 5 | `/data-verify` | **必须**（写操作） | DB 查询 + 校验代码 |
| 6 | `/report-decorate` | **必须** | Allure 注解 |
| 7 | `/compliance-check` | **必须** | 合规报告 |
| — | `/spec-review` | 推荐 | Spec 质量审查报告 |
| — | `/mock-setup` | 按需 | Mock 服务配置 |
| — | `/contract-test` | 按需 | 契约测试文件 |
| — | `/analyze-ci-failures` | 按需 | CI 失败分析报告 |
| — | `/spec-diff` | 按需 | 规约变更差异报告 |
| — | `/debug-failure` | 按需 | 失败分析 + 修复 |

### 13.3 步骤间依赖

```
步骤 0 → 步骤 1 → 步骤 2 + 步骤 3 → 步骤 4 + 步骤 5 → 步骤 6 → 步骤 7
```

- 步骤 3 依赖步骤 1：没有用例清单就没有"写什么"的边界
- 步骤 5 依赖步骤 3：DB 校验是补充到已有代码框架中的
- 步骤 7 依赖步骤 5：自检的前提是 DB 校验已经写入代码

### 13.4 不同规模项目的步骤选择

| 项目规模 | 必须步骤 | 可选步骤 |
|---|---|---|
| 小型（< 50 个测试） | 1、3、7 | 0、2、4、5、6 |
| 中型（50-200 个测试） | 0、1、3、5、7 | 2、4、6 |
| 大型（> 200 个测试） | 全部 8 步 | — |

> 💡 **提示**：无论项目多小，有一条原则不应跳过：**写操作接口必须有数据库校验**。

---

## 14. 步骤 0：规格对齐

### 14.1 目标

在写任何测试之前，先确认 AI 和工程师对"要验证什么"有一致的理解。

### 14.2 触发方式

步骤 0 内嵌在 `/case-design` 命令中，**无需单独调用**。当你执行 `/case-design` 时，AI 会自动先执行步骤 0。

### 14.3 AI 执行的动作

1. 读取 `specs/<业务线>/` 下的相关文档
2. 提炼关键业务规则和约束条件
3. 生成初步的**需求追溯表**
4. 向工程师确认理解是否正确

### 14.4 追溯表示例

| spec 文件 | spec 用例编号/标题 | 场景 | 对应测试函数名 | 覆盖维度 | 优先级 |
|---|---|---|---|---|---|
| specs/order/create.md | TC-001 正常下单 | 正常路径 | test_CreateOrder_Success | 正常场景 | P0 |
| specs/order/create.md | TC-002 缺参数 | 异常路径 | test_CreateOrder_MissingParam | 必填缺失 | P1 |
| specs/order/create.md | TC-003 库存不足 | 边界条件 | test_CreateOrder_InsufficientStock | 业务规则 | P1 |

### 14.5 常见陷阱

| 陷阱 | 后果 | 正确做法 |
|---|---|---|
| 跳过步骤 0 直接写代码 | AI 基于"直觉"生成用例，遗漏项目特有的业务规则 | 始终先准备 specs/ 文档 |
| specs/ 目录为空 | 没有输入源，追溯表无法建立 | 先补充基础 spec 文档，哪怕 2-3 页也好过没有 |
| 需求文档过期 | 追溯表与系统实际行为不符 | 使用 spec 前确认版本一致 |

---

## 15. 步骤 1：用例设计

### 15.1 目标

将规格文档转化为结构化的用例清单，作为后续代码生成的"合同"。

### 15.2 使用方法

```
/case-design order 创建订单功能
```

你可以在 `$ARGUMENTS` 中指定：
- 业务线名称（如 `order`）
- 接口名称（如 `创建订单`）
- 需要覆盖的维度（如 `正常/异常/边界/权限`）

### 15.3 覆盖维度（17 个）

AI 在设计用例时，会检查以下维度是否被覆盖：

**基础维度（所有测试类型通用）**：
1. 正常场景
2. 数据不存在
3. 参数长度边界
4. 业务规则校验
5. 权限不足
6. 重复执行
7. 幂等性
8. 数据库落库校验（有 DB 时）
9. 响应结构校验
10. 错误码校验
11. 错误信息校验

**HTTP 接口附加维度**：
12. 必填参数缺失
13. 参数为空
14. 参数类型错误
15. 枚举值非法
16. 未登录
17. Token 失效

### 15.4 输出格式

AI 会输出以下内容：

1. **spec → 用例追溯表**（表格）
2. **接口/功能理解**（一段描述）
3. **测试范围**（哪些做、哪些不做）
4. **测试用例表格**，字段包括：
   - 用例编号、场景、前置条件
   - 请求方法、路径、参数
   - 预期状态码、业务码、响应
   - 数据库校验、优先级
5. **自动化建议**
6. **哪些用例适合参数化**
7. **哪些用例需要数据前置或清理**

### 15.5 用例清单示例

```markdown
### 正常路径（P0）
- [ ] 标准下单：必填参数齐全，返回 201 + 订单号
- [ ] 含可选参数下单：含备注字段，字段正确落库

### 异常路径（P1）
- [ ] 缺少必填参数 itemId：返回 400
- [ ] 无效的 productId：返回 404
- [ ] 库存不足：返回 422 + 具体错误信息

### 边界条件（P1）
- [ ] 开始日期等于今天：正常处理
- [ ] 开始日期早于今天：返回 400

### 权限场景（P2）
- [ ] 未登录请求：返回 401
- [ ] 无下单权限的账号：返回 403
```

### 15.6 为什么用例设计必须先于代码

1. **覆盖可审查**：用例清单可以由产品、测试负责人、开发三方共同确认
2. **优先级明确**：P0 必须写，P2 可以延后
3. **AI 边界约束**：用例清单告诉 AI "写哪些"，防止 AI 自行增删场景

---

## 16. 步骤 2：测试数据

### 16.1 目标

为参数化用例设计 YAML/JSON 数据文件，确保测试数据唯一、结构清晰、便于维护。

### 16.2 何时需要此步骤

- 同一个测试逻辑需要用**多组参数**覆盖（数据驱动测试）
- 测试数据需要**版本管理**
- 数据量较大，内联在代码中会影响可读性

### 16.3 使用方法

```
/test-data 设计创建订单接口的测试数据，覆盖正常/异常/边界场景
```

### 16.4 数据设计原则

1. 测试数据和测试逻辑分离
2. 简单用例用 `pytest.mark.parametrize`
3. 大量用例放入 YAML/JSON 文件
4. 测试数据必须可重复执行
5. **写操作测试数据必须具备唯一性**
6. 不能依赖线上真实数据
7. 必须考虑数据清理（测试前 + 测试后）
8. 不把密码、token、DB 连接写进数据文件

### 16.5 数据唯一性策略

测试数据必须在并发执行时不互相冲突：

```python
# 方式 1：使用 UUID
import uuid
order_id = str(uuid.uuid4())

# 方式 2：使用 faker
from faker import Faker
fake = Faker()
username = fake.user_name() + f"_{int(time.time())}"

# 方式 3：嵌入 worker_id（xdist 并行时）
import os
worker_id = os.environ.get("PYTEST_XDIST_WORKER", "main")
unique_name = f"test_order_{worker_id}_{uuid.uuid4().hex[:8]}"
```

### 16.6 YAML 数据文件示例

```yaml
# data/yaml/order_create_cases.yaml

- id: normal_full_params
  desc: "标准下单：所有必填 + 可选参数"
  product_id: 1001
  quantity: 2
  start_date: "2026-08-01"
  remark: "测试备注"
  expected_status: 201

- id: missing_required_param
  desc: "缺少必填参数 product_id"
  quantity: 2
  expected_status: 400
  expected_error: "product_id is required"

- id: invalid_quantity
  desc: "数量为负数"
  product_id: 1001
  quantity: -1
  expected_status: 400
```

### 16.7 在代码中使用

```python
import pytest
from utils.data_reader import read_yaml

@pytest.mark.parametrize(
    "case",
    read_yaml("yaml/order_create_cases.yaml"),
    ids=lambda c: c["id"]
)
def test_create_order(http_client, case):
    resp = http_client.post("/api/orders", json={
        "product_id": case.get("product_id"),
        "quantity": case.get("quantity"),
    }, assert_status=None)

    assert resp.status_code == case["expected_status"]
```

### 16.8 数据清理策略

每个创建型用例必须有对应的清理逻辑：

```python
@pytest.fixture(autouse=True)
def cleanup_orders():
    """自动清理测试创建的订单"""
    created_ids = []
    yield created_ids
    # teardown：清理所有已创建的订单
    for order_id in created_ids:
        http_client.delete(f"/api/orders/{order_id}", assert_status=None)
```

> ⚠️ **注意**：清理注册必须在**创建成功后立即执行**，不能等到断言通过后。否则如果断言失败，测试数据就不会被清理。

---

## 17. 步骤 3：代码编写

### 17.1 目标

基于用例清单和数据文件，生成结构化的 pytest 测试代码。

### 17.2 使用方法

```
/write-tests 根据用例清单生成 testcase/order/test_order_creation_e2e.py，
  token 从 order_service_tests/client/token_store.py 获取，
  需要 DB 校验，需要清理策略
```

**在 `$ARGUMENTS` 中建议说明**：
- 测试文件放置路径
- token 获取方式
- 是否需要 DB 校验
- 是否需要清理策略

### 17.3 代码规范

生成的测试代码必须遵循以下约定：

**命名规范**：
```python
# E2E 用例：大驼峰动宾结构
def test_CreateOrder_ReturnsOrderNumber(self):

# contract/smoke 用例：should_xxx_when_yyy
def test_should_return_401_when_not_authenticated(self):
```

**Allure 注解**（每个测试函数必须有）：
```python
@allure.epic("订单管理")
@allure.feature("下单流程")
class TestOrderCreate:

    @allure.title("标准下单：必填参数齐全，返回订单号")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.e2e
    def test_CreateOrder_ReturnsOrderNumber(self, api_client, cleanup_orders):
        ...
```

**步骤块**（关键操作用 `allure.step` 包裹）：
```python
with allure.step("准备下单参数"):
    params = {"product_id": 1001, "quantity": 2}
    allure.attach(str(params), name="请求参数", attachment_type=allure.attachment_type.TEXT)

with allure.step("调用下单接口"):
    resp = api_client.create_order(**params)
    allure.attach(str(resp), name="响应结果", attachment_type=allure.attachment_type.TEXT)

with allure.step("断言响应"):
    assert resp["order_number"] is not None
    assert resp["status"] == "PENDING"
    cleanup_orders.append(resp["order_number"])  # 立即注册清理
```

### 17.4 代码禁止事项

| 禁止 | 正确替代 |
|---|---|
| 硬编码 base_url、token、密码 | 通过 fixture 或 variables.yaml 获取 |
| 依赖测试执行顺序 | 每个测试独立，不依赖其他测试的结果 |
| 裸 `time.sleep(5)` | 带超时轮询：`while time.monotonic() <= deadline` |
| E2E 用例加 `skipif` 门控 | E2E 默认直接执行 |
| 函数体内 import | 所有 import 放在文件顶部 |
| 一个函数覆盖多个场景 | 每个函数只覆盖一个场景 |

### 17.5 Spec 溯源标记

由 spec 文档生成的测试函数，docstring 首行必须写溯源标记：

```python
def test_CreateOrder_Success(api_client):
    """
    spec: specs/order/create-order.md#TC-001
    正常下单：验证订单创建成功并落库
    """
    ...
```

这样可以方便地通过 `grep` 反查追溯关系：
```bash
grep -rn "spec:" testcase/
```

### 17.6 完整测试文件示例

```python
"""创建订单 E2E 测试"""
import allure
import pytest
import time
from utils.logger import get_logger
from utils.db_client import get_db

logger = get_logger(__name__)


@allure.epic("订单管理")
@allure.feature("创建订单")
class TestOrderCreate:

    @allure.title("标准下单：必填参数齐全，返回订单号并正确落库")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.e2e
    def test_CreateOrder_Success(self, http_client, cleanup_orders):
        """
        spec: specs/order/create-order.md#TC-001
        正常下单：验证订单创建成功并落库
        """
        with allure.step("准备下单参数"):
            params = {
                "product_id": "PROD_TEST_001",
                "quantity": 2,
                "shipping_address": "测试地址-自动化用例专用"
            }
            allure.attach(str(params), "请求参数", allure.attachment_type.JSON)

        with allure.step("发送请求（创建订单）"):
            resp = http_client.post("/api/v1/orders", json=params, assert_status=201)
            data = resp.json()
            order_id = data["data"]["order_id"]
            allure.attach(str(data), "响应结果", allure.attachment_type.JSON)

        # 创建成功后立即注册清理（在断言之前！）
        cleanup_orders.append(order_id)

        with allure.step("校验响应：order_id 非空，status=pending"):
            assert order_id is not None
            assert data["data"]["status"] == "pending"

        with allure.step("数据库校验：订单正确落库"):
            db = get_db("default")
            deadline = time.monotonic() + 10
            db_order = None
            while time.monotonic() <= deadline:
                db_order = db.query_one(
                    "SELECT * FROM Orders WHERE OrderId = %s", (order_id,)
                )
                if db_order:
                    break
                time.sleep(0.5)

            assert db_order is not None, f"订单 {order_id} 未在数据库中找到"
            assert db_order["Status"] == 1
            assert db_order["ProductId"] == "PROD_TEST_001"
            assert db_order["Quantity"] == 2
            allure.attach(str(db_order), "DB 记录", allure.attachment_type.TEXT)
```

---

## 18. 步骤 4：断言设计

### 18.1 目标

确保断言有实质意义，不只是检查 HTTP 状态码。

### 18.2 何时使用

- 接口返回字段多（20+），不知道该断言哪些
- 断言策略不明确（精确值 vs 类型 vs 存在性）
- 有嵌套 JSON 结构需要部分断言

### 18.3 使用方法

```
/assertion-design 以下是创建订单的响应 JSON，请设计断言策略：
{
  "code": 0,
  "message": "success",
  "data": {
    "order_id": "ORD-20260707-001",
    "status": "pending",
    "created_at": "2026-07-07T10:30:00Z",
    "total_amount": 199.00,
    "items": [...]
  }
}
```

### 18.4 断言分层策略

| 层次 | 内容 | 何时使用 |
|---|---|---|
| 状态断言 | HTTP status_code | 每个测试必须有 |
| 结构断言 | 关键字段存在性（is not None） | 所有非空字段 |
| 语义断言 | 字段值等于业务预期 | 核心业务字段 |
| 稳定性断言 | 未修改字段保持不变 | 更新操作 |
| DB 一致性断言 | 响应值与数据库值一致 | 所有写操作 |

### 18.5 常见断言误区

| 误区 | 问题 | 正确做法 |
|---|---|---|
| 只断言 `status_code == 200` | 接口逻辑错误但状态码正确时无法发现 | 加上核心业务字段断言 |
| 断言所有字段精确值 | 动态字段（时间戳、ID）导致测试脆弱 | 动态字段只断言格式或存在性 |
| `assert resp != {}` | 空检查，没有实质意义 | 断言具体字段值 |
| 断言精确时间 | 时间每秒变化，测试不稳定 | 断言时间格式或 ±N 分钟范围 |

### 18.6 动态字段断言

```python
# 时间字段：断言格式和合理范围
from datetime import datetime, timedelta
created_at = datetime.fromisoformat(resp["created_at"])
assert datetime.now() - timedelta(minutes=5) <= created_at <= datetime.now()

# ID 字段：断言非空
assert resp["order_id"] is not None
assert len(resp["order_id"]) > 0

# 金额字段：断言类型和范围
assert isinstance(resp["total_amount"], (int, float))
assert resp["total_amount"] > 0
```

---

## 19. 步骤 5：数据验证

### 19.1 目标

验证写操作确实影响了数据库，且数据与业务规则一致。

### 19.2 使用方法

```
/data-verify testcase/order/test_order_creation_e2e.py，
  表名 Orders，关键字段 Status/ProductId/Quantity，
  异步落库需要轮询
```

### 19.3 各操作类型的校验要求

**新增接口**：
| 必须校验 | 可选校验 |
|---|---|
| 记录存在 | 关联表一致性 |
| 关键字段值正确 | 触发器效果 |
| 默认值正确 | |
| 创建人/时间正确 | |

**更新接口**：
| 必须校验 | 可选校验 |
|---|---|
| 变更字段新值正确 | 更新时间戳 |
| 未变更字段保持原值 | 操作日志 |
| 非法更新不应落库 | |

**删除接口**：
| 必须校验 | 可选校验 |
|---|---|
| 软删除：deleted_at 非空或 status 变更 | 关联数据级联 |
| 物理删除：记录不存在 | |

**失败场景**：
| 必须校验 |
|---|
| 数据库无脏数据（记录不存在或未变更） |

### 19.4 DB 校验代码模板

```python
with allure.step("数据库校验：验证订单已落库"):
    db = get_db("default")

    # 带超时轮询（异步落库场景）
    deadline = time.monotonic() + 10  # 10 秒超时
    db_order = None
    while time.monotonic() <= deadline:
        db_order = db.query_one(
            "SELECT * FROM Orders WHERE OrderNumber = %s",
            (order_number,)
        )
        if db_order:
            break
        time.sleep(0.5)

    assert db_order is not None, f"订单 {order_number} 未在数据库中找到"
    assert db_order["Status"] == "PENDING"
    assert db_order["ProductId"] == expected_product_id
    allure.attach(str(db_order), name="DB 记录", attachment_type=allure.attachment_type.TEXT)
```

### 19.5 失败场景的校验

```python
with allure.step("校验失败场景：数据库无脏数据"):
    db = get_db("default")
    # 等待足够时间确保如果有异步写入也已完成
    time.sleep(2)
    row = db.query_one(
        "SELECT * FROM Orders WHERE ProductId = %s AND CreatedBy = %s",
        (product_id, test_user_id)
    )
    assert row is None, f"失败场景产生了脏数据：{row}"
```

### 19.6 单元测试的 Mock 验证

单元测试中，数据验证通过 Mock 调用验证替代 DB 校验：

```python
# 验证外部服务被正确调用
mock_db.execute.assert_called_once_with(
    "INSERT INTO Orders ...", (expected_params,)
)

# 验证失败场景未调用外部服务
mock_db.execute.assert_not_called()

# 验证调用次数
assert mock_service.send_email.call_count == 2
```

---

## 20. 步骤 6：报告装饰

### 20.1 目标

补全 Allure 注解，让测试报告对非技术人员也可读，并支持用例追踪。

### 20.2 使用方法

```
/report-decorate testcase/order/test_order_creation_e2e.py
```

### 20.3 必须有的注解

| 注解 | 位置 | 说明 |
|---|---|---|
| `@allure.title` | 每个测试函数的**第一个**装饰器 | 报告标题，必填 |
| `@allure.severity` | 每个测试函数 | BLOCKER/CRITICAL/NORMAL/MINOR/TRIVIAL |
| `@allure.epic` | 类或模块级 | 对应业务模块 |
| `@allure.feature` | 类或模块级 | 对应功能特性 |
| `with allure.step(...)` | 测试函数内部 | 每个主要操作步骤 |
| `allure.attach(...)` | 每个 step 内部 | 输出关键数据 |

### 20.4 severity 选择标准

| 级别 | 适用场景 | 示例 |
|---|---|---|
| BLOCKER | 核心功能不可用 | 支付、下单完全不可用 |
| CRITICAL | 核心功能有严重缺陷 | 订单金额计算错误 |
| NORMAL | 普通功能测试 | 普通查询、筛选 |
| MINOR | 边界条件、格式校验 | 备注字段超长 |
| TRIVIAL | 可选功能 | UI 提示信息 |

### 20.5 allure.step + allure.attach 规范

**每个 `allure.step` 块内必须有 `allure.attach`**：

```python
with allure.step("前置：准备测试数据"):
    payload = {"item_id": 1001, "quantity": 2}
    allure.attach(str(payload), "请求参数", allure.attachment_type.JSON)

with allure.step("发送请求（创建订单）：item_id=1001"):
    resp = api_client.create_order(payload)
    allure.attach(str(resp), "响应结果", allure.attachment_type.JSON)

with allure.step("校验响应：code=0, orderId 存在"):
    assert resp["code"] == 0
    assert resp["data"]["orderId"]
    allure.attach(str(resp["data"]), "响应 data", allure.attachment_type.TEXT)

with allure.step("校验数据库：Status=PENDING"):
    row = db.query_one("SELECT * FROM Orders WHERE Id = %s", (order_id,))
    assert row["Status"] == "PENDING"
    allure.attach(str(row), "DB 记录", allure.attachment_type.TEXT)

with allure.step("清理：取消测试订单"):
    api_client.cancel_order(order_id)
    allure.attach(order_id, "已清理订单号", allure.attachment_type.TEXT)
```

> ⚠️ **注意**：step 名称应**携带期望值**（如 `"校验响应：code=0"`），而不是只写操作名（如 `"校验响应"`）。这样在报告中一眼就能看到预期结果。

### 20.6 不使用 Allure 时

如果项目使用 `pytest-html` 而非 Allure，使用结构化注释 + 显式 assert 消息替代：

```python
@pytest.mark.feature("订单管理")
@pytest.mark.story("创建订单")
@pytest.mark.severity("critical")
def test_CreateOrder_Success():
    """
    [CRITICAL] 创建订单 - 正常下单场景

    spec: specs/order/create-order.md#TC-001
    前置条件: 用户已登录，商品库存充足
    预期结果: 订单创建成功，返回 orderId
    """
    # === 步骤 1：准备参数 ===
    payload = {"item_id": 1001, "quantity": 2}

    # === 步骤 2：发送请求 ===
    resp = api_client.create_order(payload)

    # === 步骤 3：校验响应 ===
    assert resp["code"] == 0, f"预期 code=0，实际 code={resp['code']}"
    assert "orderId" in resp["data"], "响应 data 中未包含 orderId"
```

---

## 21. 步骤 7：合规自检

### 21.1 目标

作为收尾门禁，确保所有写操作用例都有 DB 校验（或 Mock 验证），防止遗漏。

### 21.2 使用方法

```
/compliance-check
```

等价于运行：
```bash
python scripts/check_compliance.py
```

### 21.3 输出解读

**全部通过**：
```
[OK] 合规自检通过：所有写操作用例均满足合规要求。
```

**有缺失**：
```
[WARN] 发现 2 个写操作用例存在合规问题：

文件                                              函数名                                       行号  缺失项
-----------------------------------------------------------------------------------------------------------------------
testcase/order/test_order_create_e2e.py            test_CreateOrder_WithRemark                  45  DB 校验
testcase/flight/test_flight_book_e2e.py            test_BookFlight_Success                     123  DB 校验（文件未 import db_client）

共 2 项缺失，请补全对应校验后重新运行本脚本。
```

### 21.4 自动排除规则

以下函数/文件会被自动排除，无需 DB 校验：

- 函数名含 `_contract` 或 `_smoke` 后缀
- 文件名含 `_contract` 的文件
- 只读操作（GET 接口，函数名不含写操作关键词）

### 21.5 识别写操作的关键词

合规脚本通过以下关键词识别写操作函数：

```
create, void, transfer, mark, switch, grab,
complete, escalate, close, cancel, update, delete,
assign, confirm, reply, send
```

> 💡 **提示**：如果你的测试函数名使用了其他写操作动词（如 `place`、`book`、`submit`），可能不会被自动识别。建议在函数名中包含上述关键词之一，或修改合规脚本的 `WRITE_KEYWORDS`。

### 21.6 补全后的自检流程

1. 运行 `/compliance-check`，获取缺失清单
2. 对每个缺失项，使用 `/data-verify` 补全校验代码
3. 再次运行 `/compliance-check`，确认全部通过
4. 提交代码

---

## 22. 辅助命令：失败排查

### 22.1 目标

当用例失败时，系统性地分析根因，而非盲目修改代码。

### 22.2 使用方法

```
/debug-failure testcase/order/test_order_creation_e2e.py::TestOrderCreate::test_CreateOrder_Success 失败了
```

### 22.3 调用时机

- 用例在 CI 上失败但本地通过
- 某个断言持续失败，看不出原因
- 数据库校验发现异常数据
- 接口返回预期之外的状态码

### 22.4 AI 分析流程

1. 检查失败的断言和实际值
2. 检查 Allure attach 中的请求/响应数据
3. 检查数据库中的实际状态
4. 与规格文档对比，判断是**测试 bug** 还是**被测系统 bug**
5. 给出修改建议（修改测试还是提 bug）

### 22.5 15 种失败根因分类

| # | 根因类型 | 典型现象 | 修复位置 |
|---|---|---|---|
| 1 | 测试代码问题 | 逻辑错误、fixture 配置不当 | 测试文件 |
| 2 | 被测服务问题 | 接口返回非预期结果 | 提 bug 给开发 |
| 3 | 测试数据问题 | ID 不存在、并发冲突 | 数据设计（步骤 2） |
| 4 | 环境配置问题 | base_url 错误、DB 连不上 | variables.yaml |
| 5 | Token 问题 | token 过期、权限不足 | auth 模块 |
| 6 | 请求参数问题 | 参数格式不对、必填项遗漏 | 测试代码 |
| 7 | 断言过严 | 动态字段精确匹配失败 | 断言设计（步骤 4） |
| 8 | DB 校验 SQL 错误 | 查询条件不对、表名错误 | DB 校验代码 |
| 9 | 数据未清理 | 旧数据干扰新测试 | 清理策略 |
| 10 | 异步未等待 | DB 数据未就绪就查询 | 替换为带超时轮询 |
| 11 | 第三方不稳定 | 外部服务超时 | mock 第三方 |
| 12 | 测试顺序依赖 | 只有按特定顺序才通过 | 重构为独立测试 |
| 13 | 并发数据冲突 | xdist 并行时数据互相影响 | 数据唯一性策略 |
| 14 | 环境差异 | 只在特定环境失败 | 环境配置对齐 |
| 15 | fixture 使用错误 | scope 不当、依赖缺失 | conftest.py |

---

# 第六部分：编写规格文档

## 23. spec-template 解读

`specs/spec-template.md` 是编写规格文档的标准模板。

### 23.1 各字段说明

**基本信息**：
```markdown
## 基本信息

- **测试函数名**: `test_XXX`          ← 与代码中的函数名一一对应
- **业务线/模块**: <业务线>           ← 对应 testcase/<业务线>/ 目录
- **用例类型**: (smoke / contract / unit / integration / e2e)
- **优先级**: (P0 / P1 / P2)         ← P0 必须写，P2 可延后
- **所在文件**: `testcase/<业务线>/test_xxx.py`
```

**用例说明**：
```markdown
## 用例说明

> 一句话描述这个测试用例验证的业务场景。
```

> 💡 **提示**：这句话会直接对应到 `@allure.title` 的内容。

**前置条件**：
```markdown
## 前置条件

- 需要准备的测试数据
- 需要登录的账号（从 variables.yaml 获取）
- 需要 Mock 的外部依赖（单元测试适用）
```

**测试步骤**：每个步骤包含接口/函数、操作描述、请求参数、预期响应和断言要点。

**数据验证**：根据测试类型选择：
- 数据库校验（API/集成测试）
- Mock 验证（单元测试）
- 多层验证（E2E 测试）

**清理策略**：清理时机、清理方式、清理函数。

**报告注解**：对应的 Allure 装饰器。

---

## 24. spec-example 走读

`specs/spec-example.md` 是一个完整的 spec 示例，以"创建订单"为例。

### 24.1 基本信息

```markdown
- **测试函数名**: `test_CreateOrder_Success_StatusPending`
- **业务线/模块**: order
- **用例类型**: e2e
- **优先级**: P0
- **所在文件**: `testcase/order/test_order_creation_e2e.py`
```

### 24.2 用例说明

```markdown
> 验证用户正常下单后，订单在数据库中的初始状态为 Pending（状态值 1），且订单号唯一。
```

### 24.3 前置条件

```markdown
- 已登录的测试账号（从 variables.yaml 的 test_accounts.default 获取）
- 商品 ID 存在于测试环境（使用固定的测试商品 PROD_TEST_001）
- 订单号通过 UUID 生成，确保唯一性
```

### 24.4 测试步骤

```markdown
### 步骤 1：创建订单
- 接口: POST /api/v1/orders
- 请求参数: {"product_id": "PROD_TEST_001", "quantity": 2, "shipping_address": "测试地址-自动化用例专用"}
- 预期响应: HTTP 201
- 断言: order_id 非空、status == "pending"、created_at 为合法 ISO 时间格式

### 步骤 2：数据库校验
- 查询 Orders 表
- 断言: Status == 1, ProductId == "PROD_TEST_001", Quantity == 2, CreatedAt 非空
```

### 24.5 数据库校验详细表

```markdown
| 字段 | 期望值 | 说明 |
|---|---|---|
| Status | 1 | Pending 状态 |
| ProductId | PROD_TEST_001 | 商品 ID 一致 |
| Quantity | 2 | 数量一致 |
| CreatedAt | 非空，±5min | 创建时间合理 |
| CreatedBy | 测试账号 ID | 创建人正确 |
```

### 24.6 异步落库处理

```python
# spec 中明确标注了异步等待策略
deadline = time.monotonic() + 30.0
while time.monotonic() <= deadline:
    row = db.query_one("SELECT Status FROM Orders WHERE OrderId = %s", (order_id,))
    if row is not None:
        break
    time.sleep(2.0)
else:
    raise AssertionError(f"订单未在 30s 内落库: {order_id}")
```

---

## 25. spec 最佳实践

### 25.1 粒度建议

| 粒度 | 适用场景 | 示例 |
|---|---|---|
| 一个 spec 对应一个测试函数 | 核心功能，P0 用例 | `create-order.md` |
| 一个 spec 包含多个相关用例 | 同一接口的多种场景 | `order-crud.md`（增删改查） |
| 一个 spec 对应一个业务流程 | E2E 测试 | `order-full-journey.md` |

### 25.2 spec 文件组织

```
specs/
├── order/
│   ├── create-order.md        ← 创建订单 spec
│   ├── update-order.md        ← 更新订单 spec
│   ├── cancel-order.md        ← 取消订单 spec
│   └── query-order.md         ← 查询订单 spec
├── payment/
│   ├── make-payment.md
│   └── refund.md
└── spec-template.md           ← 模板（参考用）
```

### 25.3 版本管理

- spec 文件应纳入 Git 版本管理
- spec 变更时，在文档头部记录变更历史：

```markdown
## 变更记录

| 版本 | 日期 | 变更内容 | 影响测试 |
|---|---|---|---|
| v1.0 | 2026-06-01 | 初始版本 | 全部 |
| v1.1 | 2026-07-01 | 新增字段 shipping_method | test_CreateOrder_WithShipping |
```

### 25.4 spec 审查清单

在 spec 文档提交前，检查以下项目：

- [ ] 基本信息完整（函数名、业务线、类型、优先级）
- [ ] 测试步骤清晰，每个步骤有明确的输入和预期输出
- [ ] 数据库校验字段列表完整（写操作）
- [ ] 清理策略已定义
- [ ] 异常场景已覆盖（至少包括参数缺失、权限不足）
- [ ] 报告注解已填写

---

# 第七部分：运行与管理

## 26. pytest 配置

`pytest.ini` 是 pytest 的核心配置文件。

### 26.1 核心配置项

```ini
[pytest]
minversion = 7.0                              # 最低 pytest 版本
addopts = -v --tb=short --strict-markers --strict-config
testpaths = testcase                          # 只在 testcase/ 目录下查找测试
pythonpath = .                                # 项目根目录加入 Python 路径
python_files = test_*.py                      # 测试文件命名规则
python_classes = Test*                        # 测试类命名规则
python_functions = test_*                     # 测试函数命名规则
```

### 26.2 strict-markers 模式

`--strict-markers` 表示：**所有 marker 必须先在 pytest.ini 中声明，才能使用**。

已声明的 marker：
```ini
markers =
    smoke: 冒烟测试（配置验证/契约检查，不依赖真实环境）
    regression: 回归测试
    e2e: 端到端测试（调用真实环境接口）
    p0: 最高优先级（阻塞发布）
    p1: 高优先级（核心业务流程）
```

如果你需要使用新的 marker（如 `performance`），必须先在 pytest.ini 中声明：

```ini
markers =
    smoke: 冒烟测试
    ...
    performance: 性能测试    # ← 新增
```

否则会报错：`PytestUnknownMarkWarning: Unknown pytest.mark.performance`

### 26.3 常用运行命令

```bash
# 运行所有测试
pytest testcase/

# 运行指定业务线
pytest testcase/order/ -v

# 运行指定文件
pytest testcase/order/test_order_creation_e2e.py -v

# 运行指定函数
pytest testcase/order/test_order_creation_e2e.py::TestOrderCreate::test_CreateOrder_Success -v

# 只运行 smoke 测试
pytest testcase/ -m smoke

# 排除 e2e 测试
pytest testcase/ -m "not e2e"

# 并行执行（4 个 worker）
pytest testcase/ -n 4

# 生成 Allure 报告
pytest testcase/ --alluredir=reports/allure-results

# 查看 Allure 报告
allure serve reports/allure-results
```

---

## 27. conftest.py 体系

TestSpec 项目有两层 conftest.py。

### 27.1 根级 conftest.py

位置：项目根目录的 `conftest.py`

**职责**：
1. **Allure 环境信息**：传入 `--alluredir` 时，将 base_url 写入 `environment.properties`
2. **失败自动 attach**：用例失败时，将最后一次 HTTP 响应 attach 到 Allure
3. **日志 hooks**：记录测试开始/结束/失败到日志文件

### 27.2 testcase 级 conftest.py

位置：`testcase/conftest.py`

**职责**：
1. **http_client fixture**：session 级的 HTTP 客户端，所有测试共享同一个 Session
2. **_track_last_response fixture**：autouse，每个测试后记录最后响应供根级 conftest 使用

### 27.3 fixture scope 选择原则

| Scope | 适用场景 | 示例 |
|---|---|---|
| `session` | 无状态/只读资源 | HTTP client、DB 连接 |
| `function` | 有副作用的资源 | 测试数据、临时文件 |
| `module` | 同模块测试共享状态 | 需要谨慎使用 |

```python
# session 级：整个测试会话只创建一次
@pytest.fixture(scope="session")
def http_client():
    client = HttpClient()
    yield client
    client.close()

# function 级：每个测试函数独立创建
@pytest.fixture
def unique_order(http_client):
    order_id = create_test_order(http_client)
    yield order_id
    delete_test_order(http_client, order_id)
```

---

## 28. 执行脚本

### 28.1 使用方式

```bash
# Windows PowerShell
.\run_order_service_tests.ps1

# Linux/macOS
bash run_order_service_tests.sh
```

### 28.2 分组策略

执行脚本按业务线分组运行，每组独立生成 HTML 报告：

| 分组 | 内容 | 特点 |
|---|---|---|
| 1 | Contract & Smoke | 始终执行，验证基础配置 |
| 2 | 第一个业务线 E2E | 按需执行 |
| 3+ | 后续业务线 E2E | 按需执行 |

### 28.3 输出示例

```
==============================================================
  1. Contract & Smoke
==============================================================
... pytest 输出 ...

==============================================================
  2. Order E2E
==============================================================
... pytest 输出 ...

==============================================================
  执行结果汇总
==============================================================
  [PASS]  1. Contract & Smoke
  [FAIL]  2. Order E2E (exit=1)

  存在失败分组，请检查上方详情
```

### 28.4 新增用例时的同步更新

> ⚠️ **这是最容易被遗忘的操作之一！**

新增测试文件后，**必须同步更新执行脚本**：

**新增 smoke/contract 用例**：追加到分组 1 的参数列表
```powershell
Invoke-PytestGroup "1. Contract & Smoke" @(
    "testcase/order/test_order_contract.py",    # ← 新增
    "testcase/payment/test_payment_smoke.py",   # ← 新增
    "-v"
)
```

**新增 E2E 用例**：新增独立分组块
```powershell
Invoke-PytestGroup "3. Inventory E2E" @(        # ← 分组编号递增
    "testcase/inventory/test_inventory_e2e.py",
    "-v", "-s"
)
```

### 28.5 报告目录

每次运行会在 `reports/` 下创建独立目录：

```
reports/
├── 2026-07-07_103015/
│   ├── 1_Contract_Smoke.html
│   ├── 1_Contract_Smoke.xml      ← JUnit XML（CI 可解析）
│   ├── 2_Order_E2E.html
│   ├── 2_Order_E2E.xml
│   └── results.json              ← 各分组退出码
└── 2026-07-07_143022/
    └── ...
```

---

## 29. 工具脚本

脚手架在 `scripts/` 目录下生成了 10 个工具脚本：

| 脚本 | 用途 | 使用方式 |
|---|---|---|
| `check_compliance.py` | 合规自检：扫描写操作用例是否缺少 DB 校验 | `python scripts/check_compliance.py` |
| `validate_specs.py` | Spec 格式校验：检查 spec 文档是否符合模板规范 | `python scripts/validate_specs.py` |
| `check_coverage.py` | 覆盖率检查：分析测试覆盖情况 | `python scripts/check_coverage.py` |
| `detect_flaky.py` | 不稳定用例检测：识别偶发失败的测试 | `python scripts/detect_flaky.py` |
| `generate_metrics.py` | 测试指标报告：生成测试执行统计数据 | `python scripts/generate_metrics.py` |
| `generate_skeletons.py` | 代码骨架生成：根据 spec 生成测试代码骨架 | `python scripts/generate_skeletons.py` |
| `generate_clients.py` | 客户端代码生成：根据 API 定义生成客户端 | `python scripts/generate_clients.py` |
| `import_openapi.py` | OpenAPI 导入：从 OpenAPI/Swagger 文档生成 spec | `python scripts/import_openapi.py` |
| `mcp_server.py` | MCP 服务：提供 MCP 协议的测试辅助服务 | `python scripts/mcp_server.py` |
| `spec_diff.py` | Spec 差异分析：对比 spec 变更对测试的影响 | `python scripts/spec_diff.py` |

### 29.1 合规自检脚本

以下详细说明 `check_compliance.py` 的用法（其他脚本可通过 `--help` 查看用法）。

### 29.1 运行方式

```bash
python scripts/check_compliance.py
```

### 29.2 扫描范围

- 扫描 `testcase/` 下所有子目录（自动发现）
- 跳过 `__pycache__` 和 `__init__.py`
- 跳过文件名含 `_contract` 的文件
- 跳过函数名含 `contract` 或 `smoke` 的函数

### 29.3 检测逻辑

对于每个匹配 `WRITE_KEYWORDS` 的测试函数：

| 测试类型 | 检查项 |
|---|---|
| 有 DB 的项目 | 文件是否 import 了 `get_db`，函数体内是否调用了 `db.query/query_one/execute` |
| 单元测试项目 | 是否使用了 `mock.patch / MagicMock / mocker.patch` |
| E2E 项目 | 函数体内是否包含 `assert` 语句 |

### 29.4 退出码

| 退出码 | 含义 |
|---|---|
| 0 | 全部通过 |
| 1 | 存在缺失项 |

### 29.5 在 CI 中使用

```bash
# CI pipeline 中作为质量门禁
python scripts/check_compliance.py
if [ $? -ne 0 ]; then
    echo "合规自检未通过，阻止合并"
    exit 1
fi
```

---

# 第八部分：进阶指南

## 30. 多测试类型混合

当项目同时包含 API、Unit、E2E 测试时，目录组织建议：

```
testcase/
├── order/
│   ├── test_order_api_contract.py     ← contract/smoke 测试
│   ├── test_order_creation_e2e.py     ← E2E 测试
│   └── test_order_service_unit.py     ← 单元测试
├── payment/
│   ├── test_payment_e2e.py
│   └── test_payment_calculator_unit.py
└── conftest.py
```

不同测试类型的 marker 区分：

```python
# E2E 测试
@pytest.mark.e2e
def test_CreateOrder_E2E(http_client):
    ...

# 单元测试
@pytest.mark.smoke
def test_should_calculate_total_correctly():
    ...
```

在 CI 中按类型分组运行：

```bash
# 先跑 smoke/contract（快速反馈）
pytest testcase/ -m "smoke or contract" -n 4

# 再跑 E2E（可能较慢）
pytest testcase/ -m "e2e"
```

---

## 31. 多数据库配置

### 31.1 variables.yaml 配置

```yaml
db:
  default:
    host: "localhost"
    port: 3306
    user: "test_user"
    password: ""
    name: "main_db"
  secondary:
    host: "localhost"
    port: 5432
    user: "test_user"
    password: ""
    name: "analytics_db"
```

### 31.2 代码中使用

```python
from utils.db_client import get_db

# 操作主库
main_db = get_db("default")
main_db.query("SELECT * FROM Orders ...")

# 操作分析库
analytics_db = get_db("secondary")
analytics_db.query("SELECT * FROM Reports ...")
```

### 31.3 跨库校验场景

```python
with allure.step("校验主库订单记录"):
    main_db = get_db("default")
    order = main_db.query_one("SELECT * FROM Orders WHERE Id = %s", (order_id,))
    assert order is not None

with allure.step("校验分析库统计记录"):
    analytics_db = get_db("secondary")
    report = analytics_db.query_one(
        "SELECT * FROM DailyReport WHERE OrderId = %s", (order_id,)
    )
    assert report is not None
```

---

## 32. 并行执行

### 32.1 安装 pytest-xdist

`requirements.txt` 已包含 `pytest-xdist`，无需额外安装。

### 32.2 运行方式

```bash
# 4 个 worker 并行
pytest testcase/ -n 4

# 自动检测 CPU 核心数
pytest testcase/ -n auto
```

### 32.3 数据唯一性要求

并行执行时，**测试数据必须唯一**，否则会产生冲突：

```python
# 嵌入 worker_id 确保唯一
import os, uuid
worker_id = os.environ.get("PYTEST_XDIST_WORKER", "main")
unique_name = f"test_{worker_id}_{uuid.uuid4().hex[:8]}"

# 使用 faker 生成唯一数据
from faker import Faker
fake = Faker()
unique_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
```

### 32.4 日志文件

xdist 并行时，每个 worker 写独立的日志文件（`logs/日期/项目名_gwN.log`），避免多进程写同一文件。

---

## 33. CI/CD 集成

### 33.1 环境变量注入 override 路径

```yaml
# GitHub Actions 示例
- name: Run Tests
  env:
    VARIABLES_OVERRIDE_PATH: ${{ secrets.OVERRIDE_FILE_PATH }}
  run: |
    pytest testcase/ --alluredir=reports/allure-results --junit-xml=reports/results.xml
```

### 33.2 JUnit XML 输出

执行脚本自动生成 JUnit XML（`reports/<时间>/<分组名>.xml`），可被 Jenkins、GitLab CI、GitHub Actions 等解析。

### 33.3 CI 模式快速运行

```bash
# CI 模式：直接跑 pytest，跳过分组脚本
pytest testcase/ \
    --junit-xml=reports/results.xml \
    --alluredir=reports/allure-results \
    -n auto \
    -q
```

### 33.4 Allure 报告发布

```bash
# 生成 Allure 报告（CI 末尾）
allure generate reports/allure-results -o reports/allure-report --clean

# 或使用 allure-pytest 的 history 特性追踪趋势
allure generate reports/allure-results -o reports/allure-report --clean
# 将 reports/allure-report 发布为 CI 产物
```

---

## 34. 定制与扩展

### 34.1 新增测试类型

在 `init.py` 的 `TEST_TYPES` 中添加：

```python
TEST_TYPES = {
    "1": ("api", "HTTP 接口自动化测试（含 DB 校验）"),
    "2": ("unit", "单元测试（含 Mock 验证）"),
    "3": ("integ", "集成测试（含系统状态验证）"),
    "4": ("e2e", "端到端测试（完整用户旅程）"),
    "5": ("perf", "性能测试（负载/压力/基准）"),    # ← 新增
}
```

然后在模板中添加对应的条件块：

```markdown
{{#IF_IS_PERF}}
## 性能测试规则
- 响应时间断言使用 assert elapsed < threshold
- 并发测试使用 pytest-xdist 的 --numprocesses 参数
{{/IF_IS_PERF}}
```

### 34.2 新增技能命令

1. 在 `templates/skills/` 下创建 `NN-skill-name.md.tpl`
2. 在 `testspec/constants.py` 的 `SKILL_FILES` 列表中注册
3. 在 `00-test-workflow.md.tpl` 的步骤表中添加引用

### 34.3 新增工具模块

1. 在 `templates/utils/` 下创建 `your_module.py.tpl`
2. 在对应的 SectionRenderer 中调用 `generator.render_template_file()` 添加一行
3. 在 `CLAUDE.md.tpl` 中添加使用说明

### 34.4 新增数据库驱动

在 `templates/utils/db_client.py.tpl` 中添加条件块：

```python
{{#IF_DB_ORACLE}}
import oracledb
from dbutils.pooled_db import PooledDB
# ...
{{/IF_DB_ORACLE}}
```

同时在 `init.py` 的 `DB_TYPES` 中注册。

### 34.5 新增合规规则

编辑 `templates/scripts/check_compliance.py.tpl`：

```python
# 在 WRITE_KEYWORDS 中添加新关键词
WRITE_KEYWORDS = re.compile(
    r"(create|void|transfer|...|place|book|submit)",  # ← 新增
    re.IGNORECASE,
)

# 或添加项目特定的检查规则
def _check_cleanup_strategy(lines, start, end):
    """检查 E2E 测试是否有清理策略"""
    ...
```

### 34.6 使用 HookRegistry 扩展生命周期（v1.2.0）

TestSpec 在生成过程中提供 4 个生命周期事件，可通过 `HookRegistry` 注册自定义回调：

| 事件 | 触发时机 | kwargs |
|---|---|---|
| `pre_generate` | 生成开始前 | `ctx` |
| `post_section` | 每个 Section 渲染完成后 | `section`, `ctx` |
| `pre_atomic_move` | 原子移动前（仅非 dry-run） | `ctx` |
| `post_generate` | 生成完成后 | `ctx`, `generated` |

```python
from testspec import HookRegistry, ProjectGenerator

hooks = HookRegistry()

# 非关键事件：单个回调失败不影响后续回调（safe_fire）
hooks.register("post_generate", lambda ctx, generated: print(f"生成了 {len(generated)} 个文件"))

# 关键事件：回调失败会中断生成流程
hooks.register("pre_generate", lambda ctx: validate_prerequisites(ctx))

gen = ProjectGenerator(ctx, templates_dir, hook_registry=hooks)
gen.generate()
```

> 💡 `post_section` 和 `post_generate` 使用 `safe_fire()` — 单个回调抛异常不会中断后续回调或其他 Section 的执行。`pre_generate` 和 `pre_atomic_move` 使用 `fire()` — 异常会中断整个生成流程。

### 34.7 使用插件扩展 Section（v1.2.0）

TestSpec 支持通过 Python `entry_points` 机制加载第三方 Section Renderer 插件，**无需修改框架源码**。

**创建插件包**：

```python
# my_plugin/sections.py
from testspec import BaseSectionRenderer

class MyCustomSection(BaseSectionRenderer):
    name = "生成自定义配置"

    @classmethod
    def managed_files(cls):
        return frozenset({"custom-config.yaml"})

    def render(self, ctx, generator):
        generator.render_template_file(
            "自定义配置", "custom/config.yaml.tpl", "custom-config.yaml"
        )
```

在插件包的 `pyproject.toml` 中注册 entry-point：

```toml
[project.entry-points."testspec.sections"]
my_custom = "my_plugin.sections:MyCustomSection"
```

**使用插件**：

```bash
# 初始化项目时自动加载已安装的插件
testspec init --plugin

# 或指定自定义 entry-point 分组
testspec init --plugin my.custom.group
```

---

# 第九部分：FAQ 与排错

## 35. 常见问题

### Q1：运行 init.py 报错 "ModuleNotFoundError"？

A：`init.py` 没有任何外部依赖，只需要 Python 3.9+。检查你的 Python 版本：
```bash
python --version  # 应该 >= 3.9
```

### Q2：生成的项目中 import 报错 "ModuleNotFoundError: No module named 'config'"？

A：确保在项目根目录下运行 pytest，或者 `pytest.ini` 中 `pythonpath = .` 已配置。

### Q3：`variables_override.yaml` 不生效？

A：检查以下可能原因：
1. 文件名是否正确（不是 `.yml` 后缀）
2. YAML 缩进是否正确（使用空格，不是 Tab）
3. 嵌套 key 路径是否与 `variables.yaml` 一致
4. 尝试设置环境变量调试：`export VARIABLES_OVERRIDE_PATH=/绝对路径/variables_override.yaml`

### Q4：pytest 报错 "PytestUnknownMarkWarning"？

A：你在测试代码中使用了 `@pytest.mark.xxx`，但没有在 `pytest.ini` 的 `markers` 节中声明。添加声明即可。

### Q5：Allure 报告显示空白？

A：确保 pytest 运行时传入了 `--alluredir` 参数：
```bash
pytest testcase/ --alluredir=reports/allure-results
allure serve reports/allure-results
```

### Q6：并行执行时测试数据冲突？

A：在测试数据中嵌入 `worker_id` 和 `uuid` 确保唯一性（参见第 32 章）。

### Q7：合规自检通过但实际缺少 DB 校验？

A：合规脚本使用正则匹配，可能被绕过。检查以下情况：
1. 函数名是否包含 `WRITE_KEYWORDS` 中的关键词
2. 是否 import 了 `get_db` 但函数体内没有实际调用
3. 参考第 29.5 节的绕过风险说明

### Q8：数据库连接超时？

A：检查：
1. `variables_override.yaml` 中的 host/port 是否正确
2. 防火墙是否放通端口
3. DB 服务器是否运行
4. 连接池是否已满（默认 maxconnections=20）

### Q9：日志文件在哪里？

A：`logs/<日期>/<项目名>.log`。日志只写文件，不输出到控制台。

### Q10：`time.sleep()` 被禁止了，怎么等待异步操作？

A：使用带超时的轮询循环：
```python
deadline = time.monotonic() + 10  # 10 秒超时
result = None
while time.monotonic() <= deadline:
    result = check_something()
    if result:
        break
    time.sleep(0.5)  # 轮询间隔内的 sleep 是允许的
assert result is not None, "操作超时"
```

### Q11：如何在不 Allure 的情况下生成报告？

A：使用 pytest-html：
```bash
pytest testcase/ --html=reports/report.html --self-contained-html
```

### Q12：新增测试文件后执行脚本没有运行新文件？

A：你需要手动将新测试文件路径添加到 `run_xxx_tests.ps1`（或 `.sh`）的对应分组中。参见第 28.4 节。

### Q13：如何在 CI 中使用 Allure？

A：参见第 33 章 CI/CD 集成。关键是：
1. 运行时加 `--alluredir`
2. CI 末尾执行 `allure generate`
3. 将生成的报告目录发布为 CI 产物

### Q14：如何查看 spec 和测试代码的追溯关系？

A：使用 grep 搜索 spec 标记：
```bash
grep -rn "spec:" testcase/
```

### Q15：项目使用了非标准 HTTP 客户端（如 httpx、aiohttp）？

A：替换 `utils/http_client.py`，保持 `HttpClient` 类名和 `request()` 方法签名，保持 `_SENTINEL` / `assert_status` 模式和 `_last_response` 存储。

---

## 36. 错误排查清单

| 错误信息 | 可能原因 | 解决方案 |
|---|---|---|
| `ModuleNotFoundError: No module named 'xxx'` | 依赖未安装 | `pip install -r requirements.txt` |
| `ModuleNotFoundError: No module named 'config'` | pythonpath 未配置 | 检查 `pytest.ini` 中 `pythonpath = .` |
| `yaml.scanner.ScannerError` | YAML 格式错误 | 检查缩进（空格非 Tab）和冒号后空格 |
| `pymysql.err.OperationalError: (2003, ...)` | DB 连不上 | 检查 host/port/防火墙 |
| `AssertionError: GET /api — 期望状态码 [200]，实际 401` | Token 问题 | 检查 token 获取方式和有效期 |
| `FileNotFoundError: data/yaml/xxx.yaml` | 数据文件路径错误 | 路径相对于 `data/` 目录 |
| `PytestUnknownMarkWarning` | marker 未声明 | 在 `pytest.ini` 的 `markers` 中添加 |
| `allure: command not found` | Allure CLI 未安装 | 安装 Allure CLI |
| `Permission denied: run_xxx.sh` | 脚本无执行权限 | `chmod +x run_xxx.sh` |
| `Connection pool exhausted` | 并发数超过池大小 | 增大 `maxconnections` 或减少并行度 |
| `sqlite3.OperationalError: near "%s"` | SQLite 占位符错误 | SQLite 使用 `?` 而非 `%s` |

---

# 附录

## A. 完整命令速查表

| 命令 | 说明 | 必须 | 示例 |
|---|---|---|---|
| `/AutomatedTesting` | 智能调度器（分析输入自动编排技能序列） | 入口 | `/AutomatedTesting docs/payment-api.md` |
| `/test-workflow` | 8 步工作流总览 | — | `/test-workflow order 创建订单` |
| `/case-design` | 用例清单设计（含步骤 0） | ✅ | `/case-design order 创建订单` |
| `/test-data` | 测试数据设计 | 推荐 | `/test-data 设计创建订单的 YAML 数据` |
| `/write-tests` | 生成 pytest 代码 | ✅ | `/write-tests testcase/order/test_create.py` |
| `/assertion-design` | 断言策略设计 | 推荐 | `/assertion-design 订单响应 JSON 如下...` |
| `/data-verify` | 数据验证方案 | ✅（写操作） | `/data-verify 表 Orders，字段 Status/ProductId` |
| `/report-decorate` | 补全报告注解 | ✅ | `/report-decorate testcase/order/test_create.py` |
| `/compliance-check` | 合规自检 | ✅ | `/compliance-check` |
| `/spec-review` | 规约审查（AI 审查 spec 质量） | 推荐 | `/spec-review specs/order/create-order.md` |
| `/mock-setup` | 搭建 Mock 服务 | 按需 | `/mock-setup order 支付回调接口` |
| `/contract-test` | 生成契约测试 | 按需 | `/contract-test order 查询订单接口` |
| `/analyze-ci-failures` | 分析 CI 失败 | 按需 | `/analyze-ci-failures` |
| `/spec-diff` | 规约差异对比 | 按需 | `/spec-diff specs/order/create-order.md` |
| `/debug-failure` | 失败排查 | 按需 | `/debug-failure test_CreateOrder 返回 500` |

## B. 模板引擎语法参考

TestSpec 的模板引擎支持以下语法：

| 语法 | 说明 | 示例 |
|---|---|---|
| `{{KEY}}` | 占位符替换 | `{{PROJECT_NAME}}` → `my-project` |
| `{{#IF_KEY}}...{{/IF_KEY}}` | 条件包含（KEY 为真时保留） | `{{#IF_HAS_DB}}...{{/IF_HAS_DB}}` |
| `{{#IF_NOT_KEY}}...{{/IF_NOT_KEY}}` | 条件排除（KEY 为假时保留） | `{{#IF_NOT_HAS_ALLURE}}...{{/IF_NOT_HAS_ALLURE}}` |
| `{{#IF_KEY}}...{{#ELSE}}...{{/IF_KEY}}` | 条件分支 | `{{#IF_HAS_ALLURE}}...{{#ELSE}}...{{/IF_HAS_ALLURE}}` |
| `{{#FOR var IN LIST_KEY}}...{{/FOR}}` | 循环遍历列表 | `{{#FOR biz IN BUSINESS_LINES}}...{{/FOR}}` |
| `{{> partial_name}}` | 包含片段（从 `_partials/` 目录加载） | `{{> header}}` |
| `\{{KEY}}` | 转义：输出字面量 `{{KEY}}`（v1.2.0） | `\{{LITERAL}}` → `{{LITERAL}}` |

条件块支持嵌套（最多 2 层）。FOR 循环支持嵌套（不同变量名）。

> 💡 **v1.2.0 新增**：FOR 循环具有**局部作用域** — 循环变量可在循环体内的条件块中使用，例如 `{{#IF_var}}` 会基于当前迭代值的真值性判断。局部变量不污染外层上下文。

**常用条件块**：

| 条件块 | 何时为真 |
|---|---|
| `{{#IF_HAS_DB}}` | 选择了数据库 |
| `{{#IF_HAS_HTTP}}` | 选择了 API/集成/E2E 测试 |
| `{{#IF_HAS_ALLURE}}` | 选择了 Allure 报告 |
| `{{#IF_HAS_EMAIL}}` | 启用了邮件配置 |
| `{{#IF_IS_API}}` | 选择了 API 测试类型 |
| `{{#IF_IS_UNIT}}` | 选择了 Unit 测试类型 |
| `{{#IF_IS_INTEG}}` | 选择了 Integ 测试类型 |
| `{{#IF_IS_E2E}}` | 选择了 E2E 测试类型 |
| `{{#IF_DB_SQLSERVER}}` | 选择了 SQL Server |
| `{{#IF_DB_MYSQL}}` | 选择了 MySQL |
| `{{#IF_DB_POSTGRESQL}}` | 选择了 PostgreSQL |
| `{{#IF_DB_SQLITE}}` | 选择了 SQLite |

## C. WRITE_KEYWORDS 完整列表

合规脚本 `check_compliance.py` 通过以下关键词识别写操作测试函数：

```
create      — 创建
void        — 作废
transfer    — 转移
mark        — 标记
switch      — 切换
grab        — 抓取/领取
complete    — 完成
escalate    — 升级
close       — 关闭
cancel      — 取消
update      — 更新
delete      — 删除
assign      — 分配
confirm     — 确认
reply       — 回复
send        — 发送
```

如果你的测试函数名不包含以上任何关键词，合规脚本将跳过检查。

## D. 推荐项目结构参考

### 小型项目（< 50 个测试）

```
testcase/
├── conftest.py
└── default/
    ├── test_api_contract.py
    └── test_api_e2e.py
```

### 中型项目（50-200 个测试）

```
testcase/
├── conftest.py
├── order/
│   ├── test_order_contract.py
│   ├── test_order_creation_e2e.py
│   ├── test_order_update_e2e.py
│   └── test_order_query_e2e.py
├── payment/
│   ├── test_payment_contract.py
│   └── test_payment_e2e.py
└── auth/
    └── test_auth_e2e.py
```

### 大型项目（> 200 个测试）

```
testcase/
├── conftest.py
├── order/
│   ├── test_order_create_e2e.py
│   ├── test_order_update_e2e.py
│   ├── test_order_cancel_e2e.py
│   ├── test_order_query_e2e.py
│   ├── test_order_contract.py
│   └── test_order_service_unit.py
├── payment/
│   ├── test_payment_create_e2e.py
│   ├── test_payment_refund_e2e.py
│   └── test_payment_contract.py
├── inventory/
│   ├── test_stock_check_e2e.py
│   └── test_stock_update_e2e.py
└── notification/
    └── test_email_send_e2e.py
```

---

> **文档版本**：v1.2.0  
> **框架版本**：v1.2.0  
> **编写日期**：2026-07-07  
>  
> 如有问题或建议，欢迎反馈。
