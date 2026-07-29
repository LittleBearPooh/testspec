# TestSpec 实操手册

> 本手册以**电商订单管理系统**为例，从零演示如何用 TestSpec 框架完成：  
> 项目初始化 → 编写规格 → 拆分用例 → 生成代码 → 运行测试 → 新增业务流程。  
> **每一步都展示"你输入什么"和"AI 输出什么"**，可直接跟着操作。

---

## 目录

- [第一部分：从零开始](#第一部分从零开始)
  - [1. 创建项目](#1-创建项目)
  - [2. 安装与配置](#2-安装与配置)
  - [3. 跑通第一个空测试](#3-跑通第一个空测试)
- [第二部分：第一个业务流程 — 创建订单](#第二部分第一个业务流程--创建订单)
  - [4. 写规格文档（specs/）](#4-写规格文档specs)
  - [5. 拆分测试用例（/case-design）](#5-拆分测试用例case-design)
  - [6. 设计测试数据（/test-data）](#6-设计测试数据test-data)
  - [7. 生成测试代码（/write-tests）](#7-生成测试代码write-tests)
  - [8. 设计断言（/assertion-design）](#8-设计断言assertion-design)
  - [9. 补全数据验证（/data-verify）](#9-补全数据验证data-verify)
  - [10. 装饰报告（/report-decorate）](#10-装饰报告report-decorate)
  - [11. 合规自检（/compliance-check）](#11-合规自检compliance-check)
  - [12. 运行测试](#12-运行测试)
- [第三部分：测试用例拆分方法论](#第三部分测试用例拆分方法论)
  - [13. 拆分思路：从一个接口到一组用例](#13-拆分思路从一个接口到一组用例)
  - [14. 拆分维度矩阵](#14-拆分维度矩阵)
  - [15. 优先级排序：P0/P1/P2 怎么定](#15-优先级排序p0p1p2-怎么定)
  - [16. 拆分反模式：常见错误](#16-拆分反模式常见错误)
  - [17. 实战练习：取消订单接口的拆分](#17-实战练习取消订单接口的拆分)
- [第四部分：新增第二个业务流程 — 支付](#第四部分新增第二个业务流程--支付)
  - [18. 完整操作流程（精简版）](#18-完整操作流程精简版)
  - [19. 新增业务线的 Checklist](#19-新增业务线的-checklist)
- [第五部分：日常操作](#第五部分日常操作)
  - [20. 每日工作流](#20-每日工作流)
  - [21. 测试失败排查](#21-测试失败排查)
  - [22. 需求变更时怎么改](#22-需求变更时怎么改)
  - [23. 新人入职交接清单](#23-新人入职交接清单)
- [附录](#附录)
  - [A. 操作命令速查卡](#a-操作命令速查卡)
  - [B. 新增业务流程 Checklist](#b-新增业务流程-checklist)

---

# 第一部分：从零开始

> 假设你是一名测试工程师，负责为公司的电商订单系统搭建自动化测试。  
> 系统有订单、支付、库存三个业务线，后端是 REST API + MySQL。

## 1. 创建项目

### 你执行

```bash
cd /path/to/workspace
python testspec/init.py
```

### 终端交互过程

```
========================================================
  TestSpec 框架脚手架 v1.2.0
  规格优先的测试自动化工程化框架
========================================================

[步骤 1/8] 项目基本信息
  请输入项目名称（英文连字符格式，例如：order-service-tests）: ecommerce-tests

[步骤 2/8] 测试类型（决定技能模板和工具桩的内容）

  请选择测试类型：
    1. HTTP 接口自动化测试（含 DB 校验）
    2. 单元测试（含 Mock 验证）
    3. 集成测试（含系统状态验证）
    4. 端到端测试（完整用户旅程）
  可多选，逗号分隔（例如：1 或 1,4）: 1,4

[步骤 3/8] 编程语言与测试框架

  请选择语言与框架：
    1. Python / pytest（推荐，工具桩完整） (默认)
    2. Python / unittest
    3. JavaScript / Jest（工具桩需手动移植）
    4. Java / JUnit5（工具桩需手动移植）
  请选择 [1]:

[步骤 4/8] 数据库配置
  是否需要数据库校验？ (Y/n): Y

  请选择数据库类型：
    1. SQL Server（pymssql） (默认)
    2. MySQL（PyMySQL）
    3. PostgreSQL（psycopg2）
    4. SQLite（标准库，无需安装驱动）
    5. 暂不配置（后续手动添加）
  请选择 [1]: 2

[步骤 5/8] 测试报告工具

  请选择报告工具：
    1. Allure（推荐） (默认)
    2. pytest-html
    3. Allure + pytest-html
  请选择 [1]:

[步骤 6/8] CI/CD 系统

  请选择 CI/CD 系统：
    1. GitHub Actions (默认)
    2. GitLab CI
    3. 暂不配置
  请选择 [1]:

[步骤 7/8] 业务线 / 功能模块
  请输入业务线或功能模块名称（英文，逗号分隔）: order,payment,inventory

[步骤 8/8] 输出与语言
  请输入生成项目的目标目录 [./ecommerce-tests]:

  文档语言：
    1. 中文 (默认)
    2. English
  请选择 [1]:

========================================================
  参数确认：
    项目名称：ecommerce-tests
    测试类型：api, e2e
    语言框架：python / pytest
    数据库  ：MySQL（PyMySQL）
    报告工具：allure
    CI 系统 ：github
    业务线  ：order, payment, inventory
    输出目录：./ecommerce-tests
    文档语言：zh
========================================================
  确认生成？ (Y/n): Y
```

### 脚手架生成

```
正在生成项目到 /path/to/workspace/ecommerce-tests ...

  [AI规则层]
  [OK] CLAUDE.md

  [技能层]
  [OK] .claude/commands/test-workflow.md
  [OK] .claude/commands/case-design.md
  [OK] ...（共 15 个命令）

  [配置层]
  [OK] variables.yaml
  [OK] variables_override.yaml.template
  [OK] config/variable_loader.py

  [工具层]
  [OK] utils/http_client.py
  [OK] utils/db_client.py
  [OK] utils/logger.py
  [OK] utils/data_reader.py
  [OK] utils/assertions.py
  [OK] utils/data_factory.py
  [OK] utils/poll_helper.py
  [OK] utils/contract_checker.py
  [OK] utils/mock_server.py

  [脚本层]
  [OK] scripts/check_compliance.py
  [OK] scripts/validate_specs.py
  [OK] scripts/check_coverage.py
  [OK] scripts/detect_flaky.py
  [OK] scripts/generate_metrics.py
  [OK] ...（共 10 个脚本）

  [CI/CD]
  [OK] .github/workflows/ci.yml
  [OK] .pre-commit-config.yaml

  ...

  生成完成！共约 80 个文件
```

---

## 2. 安装与配置

### 你执行

```bash
cd ecommerce-tests

# 激活虚拟环境（如果没有，先创建）
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 配置敏感变量

```bash
# 复制模板
cp variables_override.yaml.template variables_override.yaml
```

用编辑器打开 `variables_override.yaml`，填入真实值：

```yaml
# variables_override.yaml — 你填入的内容

test_accounts:
  default:
    password: "<your-test-password>"    # 测试账号密码

auth:
  default:
    password: "<your-auth-password>"    # 认证密码

db:
  default:
    host: "192.168.1.100"               # 测试环境数据库地址
    user: "test_user"
    password: "<your-db-password>"
```

### 修改非敏感配置

打开 `variables.yaml`，修改 base_url 和数据库非敏感信息：

```yaml
# variables.yaml — 你修改的内容

base_url: "https://staging-api.ecommerce.internal"    # 测试环境地址
timeout: 30

db:
  default:
    host: "localhost"       # 保持默认，override 中覆盖真实地址
    port: 3306
    user: "test_user"       # 保持默认
    password: ""            # 空，override 中填真实密码
    name: "ecommerce_test"  # 测试数据库名
```

### 创建认证模块

脚手架只创建了 `ecommerce_tests/client/` 空目录，你需要自己实现 token 获取逻辑。最简单的起步方式：

```python
# ecommerce_tests/client/auth_store.py

from config.variable_loader import get_nested as var_get_nested

def get_auth_header(account_name: str = "default") -> dict:
    """获取认证请求头。简单实现：从 variables.yaml 读取 API Key。"""
    account = var_get_nested(f"test_accounts.{account_name}")
    return {
        "Authorization": f"Bearer {account.get('token', '')}",
        "Content-Type": "application/json",
    }
```

> 💡 **提示**：`auth_store.py` 的具体实现取决于你们系统的认证方式（API Key / OAuth2 / JWT）。上面是最简单的版本，后续可以逐步完善。

---

## 3. 跑通第一个空测试

在正式使用 AI 工作流之前，先确认环境能正常运行。

### 创建一个临时测试文件

```python
# testcase/order/test_smoke.py

import pytest

@pytest.mark.smoke
def test_environment_ready():
    """验证测试环境基本可用"""
    assert True
```

### 运行

```bash
pytest testcase/order/test_smoke.py -v
```

### 预期输出

```
testcase/order/test_smoke.py::test_environment_ready PASSED

============= 1 passed in 0.01s =============
```

### 测试 HTTP 连通性

```python
# testcase/order/test_smoke.py（追加）

from utils.http_client import HttpClient

@pytest.mark.smoke
def test_api_reachable():
    """验证测试环境 API 可达"""
    client = HttpClient()
    resp = client.get("/health", assert_status=None)
    assert resp.status_code in (200, 204, 404), f"API 不可达: {resp.status_code}"
```

```bash
pytest testcase/order/test_smoke.py -v
```

如果看到 `PASSED`，说明 HTTP 客户端和变量系统都正常工作。

> ⚠️ **注意**：如果报错 `ModuleNotFoundError: No module named 'config'`，检查 `pytest.ini` 中是否有 `pythonpath = .`，以及你是否在项目根目录下运行 pytest。

---

# 第二部分：第一个业务流程 — 创建订单

> 现在开始正式使用 TestSpec 的 8 步工作流。  
> 目标：为"创建订单"接口编写完整的自动化测试。  
> 接口：`POST /api/v1/orders`

## 4. 写规格文档（specs/）

### 这一步做什么

在写任何测试代码之前，先把"要验证什么"写成文档。这份文档就是你、AI、以及未来接手的同事共同参照的"合同"。

### 你执行

在 `specs/order/` 目录下创建 `create-order.md`：

```markdown
# 创建订单

## 基本信息

- **业务线/模块**: order
- **接口**: POST /api/v1/orders
- **请求方式**: JSON Body
- **认证要求**: 需要登录 Token

## 接口说明

> 用户登录后，选择商品并提交订单。系统创建订单记录，返回订单号。
> 订单初始状态为 Pending (Status=1)。

## 请求参数

| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| product_id | string | 是 | 商品 ID，必须存在于商品表中 |
| quantity | int | 是 | 购买数量，最小 1，最大 999 |
| shipping_address | string | 是 | 收货地址，最长 200 字符 |
| remark | string | 否 | 订单备注，最长 100 字符 |
| coupon_code | string | 否 | 优惠券码 |

## 正常响应（HTTP 201）

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "order_id": "ORD-20260707-001",
    "status": "pending",
    "total_amount": 199.00,
    "created_at": "2026-07-07T10:30:00Z"
  }
}
```

## 错误响应

| HTTP 状态码 | code | message | 触发条件 |
|---|---|---|---|
| 400 | 1001 | "product_id is required" | 缺少必填参数 |
| 400 | 1002 | "quantity must be >= 1" | 数量非法 |
| 404 | 2001 | "product not found" | 商品 ID 不存在 |
| 422 | 3001 | "insufficient stock" | 库存不足 |
| 401 | 4001 | "unauthorized" | 未登录 |
| 403 | 4002 | "forbidden" | 无下单权限 |

## 数据库影响

- 写入 `Orders` 表：Status=1, ProductId, Quantity, CreatedBy, CreatedAt
- 写入 `OrderItems` 表：关联订单明细
- 更新 `Inventory` 表：库存数量扣减

## 业务规则

1. 同一用户 1 分钟内不能重复提交相同商品的订单（幂等校验）
2. 库存不足时不创建订单，不扣库存
3. 优惠券码不存在时忽略（不报错），存在时扣减金额
```

### 为什么这样写

| 区域 | 给谁看 | 作用 |
|---|---|---|
| 请求参数表 | AI + 人 | 告诉 AI 有哪些字段可以组合测试 |
| 错误响应表 | AI | AI 据此生成异常路径用例 |
| 数据库影响 | AI | AI 据此生成 DB 校验 SQL |
| 业务规则 | AI + 人 | 边界条件和特殊场景的来源 |

> 💡 **提示**：spec 不需要写得像 PRD 那样完整，但**必须包含**：请求参数、预期响应（正常 + 异常）、数据库影响。这三项是 AI 生成用例的核心输入。

---

## 5. 拆分测试用例（/case-design）

### 这一步做什么

让 AI 读取你的 spec 文档，自动生成结构化的测试用例清单。你在这个环节的角色是**审查员**——确认 AI 的用例是否覆盖了所有应该覆盖的场景。

### 你输入（在 Claude Code 中）

```
/case-design order 创建订单接口，specs/order/create-order.md
```

### AI 输出（节选关键部分）

AI 会输出以下结构：

**① spec → 用例追溯表**

| spec 来源 | 场景 | 测试函数名 | 维度 | 优先级 |
|---|---|---|---|---|
| create.md 请求参数 | 正常下单（全参数） | test_CreateOrder_AllParams | 正常场景 | P0 |
| create.md 请求参数 | 正常下单（仅必填） | test_CreateOrder_RequiredOnly | 正常场景 | P0 |
| create.md 错误 400-1001 | 缺少 product_id | test_CreateOrder_MissingProductId | 必填缺失 | P1 |
| create.md 错误 400-1002 | quantity=0 | test_CreateOrder_QuantityZero | 参数边界 | P1 |
| create.md 错误 400-1002 | quantity=-1 | test_CreateOrder_QuantityNegative | 参数边界 | P1 |
| create.md 错误 400-1002 | quantity=1000 | test_CreateOrder_QuantityOverMax | 参数边界 | P1 |
| create.md 错误 404-2001 | 商品不存在 | test_CreateOrder_ProductNotFound | 数据不存在 | P1 |
| create.md 错误 422-3001 | 库存不足 | test_CreateOrder_InsufficientStock | 业务规则 | P1 |
| create.md 错误 401-4001 | 未登录 | test_CreateOrder_Unauthorized | 权限 | P1 |
| create.md 错误 403-4002 | 无权限账号 | test_CreateOrder_Forbidden | 权限 | P2 |
| create.md 规则 1 | 重复提交相同订单 | test_CreateOrder_DuplicateSubmit | 幂等性 | P1 |
| create.md 规则 3 | 无效优惠券码 | test_CreateOrder_InvalidCoupon | 业务规则 | P2 |
| create.md DB 影响 | 订单正确落库 | （内嵌在成功用例中） | DB 校验 | P0 |

**② 完整用例表（每个用例的详细信息）**

AI 会为每个用例输出一个表格，包含：场景、前置条件、请求参数、预期状态码、预期业务码、预期响应、数据库校验、优先级。

**③ 自动化建议**

AI 会建议：
- 哪些用例适合参数化（如 400 错误的多种参数组合）
- 哪些用例需要前置数据（如库存不足需要先清空库存）
- 哪些用例需要清理（如成功下单后需要取消订单）

### 你的审查动作

拿到 AI 的用例清单后，你需要检查：

| 检查项 | 问题示例 | 修正方式 |
|---|---|---|
| 覆盖遗漏 | "shpping_address 超长 200 字符没有用例" | 告诉 AI 补充 |
| 优先级不合理 | "未登录应该是 P0 不是 P1" | 告诉 AI 调整 |
| 不切实际的用例 | "我们没有优惠券功能" | 告诉 AI 删除 |
| 重复用例 | "quantity=0 和 quantity=-1 可以合并" | 告诉 AI 合并为参数化 |

确认后，这个用例清单就成了后续步骤的"合同"。

---

## 6. 设计测试数据（/test-data）

### 这一步做什么

为参数化用例设计 YAML 数据文件。如果用例数据简单（2-3 组），可以跳过此步直接内联在代码中。

### 什么时候需要这一步

| 场景 | 是否需要 /test-data |
|---|---|
| 只有 1-2 个正常场景 | 不需要，直接写在代码里 |
| 5+ 个异常参数组合 | 需要，用 YAML 参数化 |
| 需要 faker 生成随机数据 | 需要 |
| 需要多组账号测试权限 | 需要 |

### 你输入

```
/test-data 为创建订单的异常参数场景设计 YAML 数据，
覆盖：缺参数、参数非法、商品不存在、库存不足
```

### AI 输出

```yaml
# data/yaml/order_create_negative.yaml

- id: missing_product_id
  desc: "缺少 product_id"
  body:
    quantity: 2
    shipping_address: "测试地址"
  expected_status: 400
  expected_code: 1001

- id: quantity_zero
  desc: "quantity = 0"
  body:
    product_id: "PROD_TEST_001"
    quantity: 0
    shipping_address: "测试地址"
  expected_status: 400
  expected_code: 1002

- id: quantity_negative
  desc: "quantity = -1"
  body:
    product_id: "PROD_TEST_001"
    quantity: -1
    shipping_address: "测试地址"
  expected_status: 400
  expected_code: 1002

- id: quantity_over_max
  desc: "quantity = 1000 (超过上限 999)"
  body:
    product_id: "PROD_TEST_001"
    quantity: 1000
    shipping_address: "测试地址"
  expected_status: 400
  expected_code: 1002

- id: product_not_found
  desc: "商品 ID 不存在"
  body:
    product_id: "NON_EXISTENT_999"
    quantity: 1
    shipping_address: "测试地址"
  expected_status: 404
  expected_code: 2001

- id: insufficient_stock
  desc: "库存不足（商品库存为 0）"
  body:
    product_id: "PROD_NO_STOCK"
    quantity: 1
    shipping_address: "测试地址"
  expected_status: 422
  expected_code: 3001
```

### 你执行

把 AI 输出的 YAML 保存到 `data/yaml/order_create_negative.yaml`。

> 💡 **提示**：注意 `body` 字段中没有包含 `product_id` 的用例（如 missing_product_id）——这是因为我们故意不传这个字段来测试缺参场景。

---

## 7. 生成测试代码（/write-tests）

### 这一步做什么

让 AI 根据用例清单和测试数据，生成完整的 pytest 测试代码。

### 你输入

```
/write-tests 根据 specs/order/create-order.md 的用例清单生成测试代码：
- 文件路径：testcase/order/test_order_creation_e2e.py
- token 从 ecommerce_tests/client/auth_store.py 的 get_auth_header() 获取
- 需要 DB 校验（表 Orders、OrderItems、Inventory）
- 需要清理策略（测试创建的订单要取消）
- 异常参数用例使用 data/yaml/order_create_negative.yaml 参数化
```

### AI 输出（核心结构）

```python
"""创建订单 E2E 测试

spec: specs/order/create-order.md
"""
import allure
import pytest
import time
from utils.http_client import HttpClient
from utils.db_client import get_db
from utils.logger import get_logger
from utils.data_reader import read_yaml
from ecommerce_tests.client.auth_store import get_auth_header

logger = get_logger(__name__)


@allure.epic("订单管理")
@allure.feature("创建订单")
class TestOrderCreation:
    """POST /api/v1/orders 创建订单测试"""

    # =====================================================================
    # P0 - 正常路径
    # =====================================================================

    @allure.title("正常下单：全部参数，返回订单号并正确落库")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.e2e
    def test_CreateOrder_AllParams(self, http_client, cleanup_orders):
        """
        spec: specs/order/create-order.md#正常响应
        """
        with allure.step("前置：准备请求参数"):
            params = {
                "product_id": "PROD_TEST_001",
                "quantity": 2,
                "shipping_address": "自动化测试地址-勿发货",
                "remark": "自动化测试备注",
            }
            allure.attach(str(params), "请求参数", allure.attachment_type.JSON)

        with allure.step("发送请求：POST /api/v1/orders"):
            resp = http_client.post(
                "/api/v1/orders",
                json=params,
                headers=get_auth_header(),
                assert_status=201,
            )
            data = resp.json()["data"]
            order_id = data["order_id"]
            allure.attach(str(resp.json()), "完整响应", allure.attachment_type.JSON)

        # ⚠️ 创建成功后立即注册清理（在断言之前！）
        cleanup_orders.append(order_id)

        with allure.step("校验响应：order_id 非空, status=pending"):
            assert data["order_id"] is not None, "order_id 为空"
            assert data["status"] == "pending", f"期望 pending，实际 {data['status']}"
            assert data["total_amount"] > 0, "total_amount 应大于 0"

        with allure.step("校验数据库：Orders 表记录正确"):
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

            assert db_order is not None, f"订单 {order_id} 未落库"
            assert db_order["Status"] == 1, f"期望 Status=1，实际 {db_order['Status']}"
            assert db_order["ProductId"] == "PROD_TEST_001"
            assert db_order["Quantity"] == 2
            allure.attach(str(db_order), "Orders 表记录", allure.attachment_type.TEXT)

        with allure.step("校验数据库：OrderItems 表有明细记录"):
            items = db.query(
                "SELECT * FROM OrderItems WHERE OrderId = %s", (order_id,)
            )
            assert len(items) >= 1, "OrderItems 表无明细记录"
            allure.attach(str(items), "OrderItems 表记录", allure.attachment_type.TEXT)

    # =====================================================================
    # P1 - 异常路径（参数化）
    # =====================================================================

    @allure.title("异常参数：{case[desc]}")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.e2e
    @pytest.mark.parametrize(
        "case",
        read_yaml("yaml/order_create_negative.yaml"),
        ids=lambda c: c["id"],
    )
    def test_CreateOrder_NegativeParams(self, http_client, case):
        """
        spec: specs/order/create-order.md#错误响应
        参数化异常场景：缺参数、非法值、商品不存在、库存不足
        """
        with allure.step(f"发送请求：{case['desc']}"):
            resp = http_client.post(
                "/api/v1/orders",
                json=case["body"],
                headers=get_auth_header(),
                assert_status=None,  # 异常场景关闭自动断言
            )
            allure.attach(str(resp.json()), "响应体", allure.attachment_type.JSON)

        with allure.step(f"校验响应：status={case['expected_status']}, code={case['expected_code']}"):
            assert resp.status_code == case["expected_status"], \
                f"期望 {case['expected_status']}，实际 {resp.status_code}"
            assert resp.json()["code"] == case["expected_code"], \
                f"期望 code={case['expected_code']}，实际 {resp.json()['code']}"

        with allure.step("校验数据库：失败场景无脏数据"):
            db = get_db("default")
            # 轮询等待确保异步处理完成（禁止无条件 time.sleep）
            deadline = time.monotonic() + 5
            row = None
            while time.monotonic() <= deadline:
                row = db.query_one(
                    "SELECT * FROM Orders WHERE ProductId = %s AND ShippingAddress = %s",
                    (case["body"].get("product_id", ""), case["body"].get("shipping_address", "")),
                )
                if row:
                    break
                time.sleep(0.5)
            assert row is None, f"失败场景产生了脏数据: {row}"

    # =====================================================================
    # P1 - 权限场景
    # =====================================================================

    @allure.title("未登录下单：返回 401")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.e2e
    def test_CreateOrder_Unauthorized(self, http_client):
        """
        spec: specs/order/create-order.md#错误 401-4001
        """
        with allure.step("发送请求：不带 Token"):
            resp = http_client.post(
                "/api/v1/orders",
                json={"product_id": "PROD_TEST_001", "quantity": 1, "shipping_address": "test"},
                assert_status=None,
            )
            allure.attach(str(resp.status_code), "状态码", allure.attachment_type.TEXT)

        with allure.step("校验响应：401"):
            assert resp.status_code == 401

    # =====================================================================
    # P1 - 幂等性
    # =====================================================================

    @allure.title("重复提交相同订单：幂等校验")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.e2e
    def test_CreateOrder_DuplicateSubmit(self, http_client, cleanup_orders):
        """
        spec: specs/order/create-order.md#规则 1
        """
        params = {
            "product_id": "PROD_TEST_001",
            "quantity": 1,
            "shipping_address": "幂等测试地址",
        }

        with allure.step("第一次提交：应成功"):
            resp1 = http_client.post(
                "/api/v1/orders", json=params, headers=get_auth_header(), assert_status=201,
            )
            order_id = resp1.json()["data"]["order_id"]
            cleanup_orders.append(order_id)
            allure.attach(order_id, "第一次订单号", allure.attachment_type.TEXT)

        with allure.step("1 秒内第二次提交相同参数：应被拒绝"):
            resp2 = http_client.post(
                "/api/v1/orders", json=params, headers=get_auth_header(), assert_status=None,
            )
            allure.attach(str(resp2.json()), "第二次响应", allure.attachment_type.JSON)
            # 根据业务规则，应该返回重复提交错误
            assert resp2.status_code in (400, 409, 422), \
                f"重复提交未被拦截，status={resp2.status_code}"


# =====================================================================
# Fixtures
# =====================================================================

@pytest.fixture(autouse=True)
def cleanup_orders(http_client):
    """自动清理测试创建的订单"""
    created_ids = []
    yield created_ids
    for order_id in created_ids:
        try:
            http_client.delete(
                f"/api/v1/orders/{order_id}",
                headers=get_auth_header(),
                assert_status=None,
            )
            logger.info("已清理订单: %s", order_id)
        except Exception as e:
            logger.warning("清理订单失败: %s, 错误: %s", order_id, e)
```

### 你的审查动作

| 检查项 | 为什么重要 |
|---|---|
| `cleanup_orders.append(order_id)` 是否在断言之前 | 断言失败时也要能清理 |
| 异常场景是否 `assert_status=None` | 异常场景期望非 200，不能让 HttpClient 自动断言 |
| DB 校验是否用了轮询 | 异步落库时直接查可能查不到 |
| import 是否都在文件顶部 | 规范，不在函数体内 import |

把代码保存到 `testcase/order/test_order_creation_e2e.py`。

---

## 8. 设计断言（/assertion-design）

### 这一步做什么

当接口返回字段很多时，让 AI 帮你决定**哪些字段必须断言、哪些只断言类型、哪些不断言**。

### 什么时候需要这一步

| 场景 | 是否需要 |
|---|---|
| 响应只有 3-5 个字段 | 不需要，直接写 |
| 响应有 20+ 字段 | 需要 |
| 不确定哪些字段是动态的 | 需要 |

### 你输入

```
/assertion-design 创建订单接口的响应 JSON 如下：
{
  "code": 0,
  "message": "success",
  "data": {
    "order_id": "ORD-20260707-001",
    "status": "pending",
    "total_amount": 199.00,
    "created_at": "2026-07-07T10:30:00Z",
    "items": [{"product_id": "PROD_001", "quantity": 2, "unit_price": 99.50}],
    "coupon_discount": 0,
    "shipping_fee": 0
  }
}
哪些字段必须精确断言，哪些只断言类型或存在性？
```

### AI 输出（核心部分）

| 字段 | 断言策略 | 原因 |
|---|---|---|
| `code` | 精确值 == 0 | 业务成功标记，必须精确 |
| `data.order_id` | 非空 + 类型 str | 动态生成，无法预知精确值 |
| `data.status` | 精确值 == "pending" | 业务规则，初始状态固定 |
| `data.total_amount` | 类型 float + > 0 | 金额可能因优惠券变化 |
| `data.created_at` | ISO 格式 + ±5 分钟 | 动态值，只验合理性 |
| `data.items` | 长度 >= 1 | 至少有一个明细 |
| `data.coupon_discount` | 类型 float | 值取决于优惠券逻辑 |
| `data.shipping_fee` | 类型 float | 值取决于运费规则 |

> 💡 **提示**：如果你在第 7 步已经觉得断言写得够好了，可以跳过这一步。它更适合字段多、业务逻辑复杂的接口。

---

## 9. 补全数据验证（/data-verify）

### 这一步做什么

检查每个写操作测试是否有完整的数据库校验，并补充缺失的校验。

### 你输入

```
/data-verify testcase/order/test_order_creation_e2e.py，
表 Orders 校验 Status/ProductId/Quantity/CreatedBy，
表 OrderItems 校验明细记录数量，
表 Inventory 校验库存扣减
```

### AI 输出（补充到已有代码中）

AI 会检查你已有的 DB 校验代码，并补充缺失的部分。比如发现 `test_CreateOrder_AllParams` 缺少库存扣减校验，会建议添加：

```python
with allure.step("校验数据库：Inventory 库存已扣减"):
    inventory = db.query_one(
        "SELECT Stock FROM Inventory WHERE ProductId = %s",
        ("PROD_TEST_001",),
    )
    assert inventory is not None, "Inventory 记录不存在"
    # 假设初始库存已知（从前置数据中获取）
    assert inventory["Stock"] == initial_stock - 2, \
        f"库存未正确扣减：期望 {initial_stock - 2}，实际 {inventory['Stock']}"
    allure.attach(str(inventory), "Inventory 记录", allure.attachment_type.TEXT)
```

### 你执行

把 AI 补充的校验代码合并到测试文件中对应的位置。

---

## 10. 装饰报告（/report-decorate）

### 这一步做什么

扫描测试文件，补全缺失的 Allure 注解。

### 你输入

```
/report-decorate testcase/order/test_order_creation_e2e.py
```

### AI 输出

AI 会检查每个测试函数是否有 `@allure.title`（第一个装饰器）、`@allure.severity`，每个 `allure.step` 是否有 `allure.attach`。如果缺失会补全。

如果第 7 步的代码已经写得够完整，AI 可能只输出"已完整，无需补充"。

---

## 11. 合规自检（/compliance-check）

### 这一步做什么

运行合规脚本，自动扫描写操作测试是否缺少 DB 校验。

### 你输入

```
/compliance-check
```

或手动运行：

```bash
python scripts/check_compliance.py
```

### 输出解读

**通过**：

```
[OK] 合规自检通过：所有写操作用例均满足合规要求。
```

**有缺失**：

```
[WARN] 发现 1 个写操作用例存在合规问题：

文件                                              函数名                                  行号  缺失项
-----------------------------------------------------------------------------------------------------------------
testcase/order/test_order_creation_e2e.py          test_CreateOrder_DuplicateSubmit        95  DB 校验

共 1 项缺失，请补全对应校验后重新运行本脚本。
```

### 你的处理

如果报缺失，回到 `/data-verify` 补全，然后**再次运行自检**直到通过。

---

## 12. 运行测试

### 运行单个测试文件

```bash
pytest testcase/order/test_order_creation_e2e.py -v
```

### 预期输出

```
testcase/order/test_order_creation_e2e.py::TestOrderCreation::test_CreateOrder_AllParams PASSED
testcase/order/test_order_creation_e2e.py::TestOrderCreation::test_CreateOrder_NegativeParams[missing_product_id] PASSED
testcase/order/test_order_creation_e2e.py::TestOrderCreation::test_CreateOrder_NegativeParams[quantity_zero] PASSED
testcase/order/test_order_creation_e2e.py::TestOrderCreation::test_CreateOrder_NegativeParams[quantity_negative] PASSED
testcase/order/test_order_creation_e2e.py::TestOrderCreation::test_CreateOrder_NegativeParams[quantity_over_max] PASSED
testcase/order/test_order_creation_e2e.py::TestOrderCreation::test_CreateOrder_NegativeParams[product_not_found] PASSED
testcase/order/test_order_creation_e2e.py::TestOrderCreation::test_CreateOrder_NegativeParams[insufficient_stock] PASSED
testcase/order/test_order_creation_e2e.py::TestOrderCreation::test_CreateOrder_Unauthorized PASSED
testcase/order/test_order_creation_e2e.py::TestOrderCreation::test_CreateOrder_DuplicateSubmit PASSED

============= 9 passed in 12.34s =============
```

### 查看报告

```bash
# 生成 Allure 报告
pytest testcase/order/ --alluredir=reports/allure-results
allure serve reports/allure-results
```

### 同步执行脚本

> ⚠️ **别忘了这一步！** 新增测试文件后必须同步更新执行脚本。

打开 `run_ecommerce_tests.ps1`（或 `.sh`），在分组 1 中添加新文件：

```powershell
Invoke-PytestGroup "1. Contract & Smoke" @(
    "testcase/order/test_smoke.py",
    "testcase/order/test_order_creation_e2e.py",    # ← 新增
    "-v"
)
```

---

# 第三部分：测试用例拆分方法论

> 这一部分是 TestSpec 框架最有价值的内容之一。  
> 学会拆分用例，比学会写代码更重要。

## 13. 拆分思路：从一个接口到一组用例

### 核心理念

拿到一个接口后，**不要上来就写代码**。先在脑子里（或纸上）回答三个问题：

1. **这个接口能做什么？**（正常路径）
2. **什么情况会出错？**（异常路径）
3. **有没有边界情况？**（边界条件）

### 拆分流程

```
一个接口
  │
  ├─→ 正常路径：按参数组合拆分
  │     ├─ 全部参数
  │     ├─ 仅必填参数
  │     └─ 含可选参数的各种组合
  │
  ├─→ 异常路径：按错误类型拆分
  │     ├─ 必填参数缺失（每个必填参数各一条）
  │     ├─ 参数类型错误
  │     ├─ 参数值非法（枚举越界、格式不对）
  │     └─ 业务规则违反（如库存不足、重复提交）
  │
  ├─→ 边界条件：按字段约束拆分
  │     ├─ 最小值 / 最大值
  │     ├─ 空字符串 / 超长字符串
  │     └─ 特殊字符
  │
  └─→ 权限场景：按角色拆分
        ├─ 未登录
        ├─ 无权限
        └─ 不同角色的差异化行为
```

### 实际案例：POST /api/v1/orders

```
POST /api/v1/orders
  │
  ├─ 正常路径
  │   ├─ P0: 全部参数下单（product_id + quantity + shipping_address + remark + coupon_code）
  │   └─ P0: 仅必填参数下单（product_id + quantity + shipping_address）
  │
  ├─ 异常路径
  │   ├─ P1: 缺少 product_id → 400
  │   ├─ P1: 缺少 quantity → 400
  │   ├─ P1: 缺少 shipping_address → 400
  │   ├─ P1: product_id 不存在 → 404
  │   ├─ P1: quantity = 0 → 400
  │   ├─ P1: quantity = -1 → 400
  │   ├─ P1: quantity = 1000（超过上限）→ 400
  │   ├─ P1: shipping_address 超过 200 字符 → 400
  │   ├─ P1: 库存不足 → 422
  │   ├─ P1: 1 分钟内重复提交 → 409
  │   └─ P2: 无效优惠券码 → 201（忽略）
  │
  ├─ 权限场景
  │   ├─ P1: 不带 Token → 401
  │   ├─ P1: Token 过期 → 401
  │   └─ P2: 无下单权限 → 403
  │
  └─ DB 校验（内嵌在正常路径中）
      ├─ Orders 表：Status=1, ProductId, Quantity, CreatedBy, CreatedAt
      ├─ OrderItems 表：至少 1 条明细
      └─ Inventory 表：库存数量已扣减
```

---

## 14. 拆分维度矩阵

把上面的思路总结成一张表，每拿到一个新接口就对着这张表过一遍：

| 维度 | 要问的问题 | 创建订单的答案 |
|---|---|---|
| **正常场景** | 最标准的调用方式是什么？ | 全部参数，返回 201 |
| **正常变体** | 必填参数够了但可选参数不同呢？ | 仅必填参数 / 含优惠券 |
| **数据不存在** | 引用的资源不存在会怎样？ | product_id 不存在 → 404 |
| **必填缺失** | 每个必填参数不传会怎样？ | 缺 product_id → 400 |
| **参数边界** | 最小值/最大值/空/超长？ | quantity=0, -1, 1000 |
| **类型错误** | 参数类型不对会怎样？ | quantity="abc" → 400 |
| **业务规则** | 有什么特殊业务限制？ | 重复提交、库存不足 |
| **权限** | 不同角色调用有区别吗？ | 未登录 401、无权限 403 |
| **幂等性** | 重复调用有副作用吗？ | 1 分钟内重复提交 |
| **DB 影响** | 数据库会怎么变？ | Orders + OrderItems + Inventory |
| **失败无脏数据** | 失败后数据库干净吗？ | 失败场景 Orders 无新记录 |

### 使用方法

```
1. 把接口信息填入左列
2. 逐行过一遍，每行回答右列的问题
3. 能回答出具体场景的，就是一条用例
4. 回答"不适用"的，跳过
```

> 💡 **提示**：不需要每次都覆盖所有维度。简单接口（如 GET /health）可能只有 2-3 条用例。复杂接口（如支付回调）可能有 20+ 条。关键是**有意识地过一遍**，而不是凭感觉写。

---

## 15. 优先级排序：P0/P1/P2 怎么定

| 优先级 | 定义 | 判断标准 | 示例 |
|---|---|---|---|
| **P0** | 阻塞发布 | 这个场景不过，产品不能上线 | 正常下单、支付成功 |
| **P1** | 核心覆盖 | 高频使用或高风险的场景 | 参数校验、权限校验、库存不足 |
| **P2** | 完善覆盖 | 低频或低风险的边界场景 | 无效优惠券、超长备注 |

### 排序口诀

```
先问"不做会死吗" → P0
再问"用户会碰到吗" → P1
最后"锦上添花吗" → P2
```

### 创建订单的优先级分布

```
P0（不做不能上线）：
  - 正常下单全参数
  - 正常下单仅必填
  - DB 校验

P1（高频/高风险）：
  - 缺少 product_id
  - 缺少 quantity
  - quantity 非法值
  - 商品不存在
  - 库存不足
  - 未登录
  - 重复提交

P2（边界补充）：
  - 无下单权限
  - 无效优惠券码
  - shipping_address 超长
```

---

## 16. 拆分反模式：常见错误

### ❌ 反模式 1：一个函数测所有场景

```python
# 错误示例
def test_create_order():
    # 正常下单
    resp1 = client.post("/orders", json={...})
    assert resp1.status_code == 201

    # 缺参数
    resp2 = client.post("/orders", json={})
    assert resp2.status_code == 400

    # 未登录
    resp3 = client.post("/orders", json={...}, headers={})
    assert resp3.status_code == 401
```

**问题**：如果第一个断言失败，后面的场景全部跳过。无法知道哪些场景通过、哪些失败。

**正确做法**：每个场景一个函数，或使用 parametrize。

### ❌ 反模式 2：用例描述太笼统

```python
# 错误示例
def test_order():
    """测试订单功能"""
    ...
```

**问题**：看不出测了什么、预期是什么。

**正确做法**：`test_CreateOrder_MissingProductId_Returns400` — 函数名说清楚输入条件和预期结果。

### ❌ 反模式 3：只测正常路径

```python
# 只有这一个测试
def test_CreateOrder_Success():
    resp = client.post("/orders", json={...})
    assert resp.status_code == 201
```

**问题**：80% 的 bug 在异常路径。只测正常路径等于没测。

**正确做法**：至少覆盖：正常 + 缺参数 + 权限 + 业务规则。

### ❌ 反模式 4：断言只有 status_code

```python
# 错误示例
def test_CreateOrder_Success():
    resp = client.post("/orders", json={...})
    assert resp.status_code == 201
    # 没了？！
```

**问题**：状态码 201 但数据全错的情况真实存在。

**正确做法**：状态码 + 核心字段 + DB 校验。

### ❌ 反模式 5：忘记清理

```python
# 错误示例
def test_CreateOrder_Success():
    resp = client.post("/orders", json={...})
    assert resp.status_code == 201
    # 测试结束，订单留在数据库里了
```

**问题**：脏数据积累，影响后续测试和其他人。

**正确做法**：创建成功后**立即**注册清理（在断言之前）。

---

## 17. 实战练习：取消订单接口的拆分

现在用同样的方法来拆分另一个接口：**取消订单 `PUT /api/v1/orders/{order_id}/cancel`**

### 接口信息

```
PUT /api/v1/orders/{order_id}/cancel

请求参数：
  - order_id (path): 订单号
  - reason (body, 必填): 取消原因，最长 200 字符

业务规则：
  - 只有 Pending 状态的订单可以取消
  - 已发货的订单不能取消
  - 取消后库存回补
  - 只有订单创建者或管理员可以取消
```

### 拆分结果

```
PUT /api/v1/orders/{order_id}/cancel
  │
  ├─ 正常路径
  │   ├─ P0: 正常取消 Pending 订单 → 200，DB: Status=已取消
  │   └─ P1: 管理员取消他人订单 → 200
  │
  ├─ 异常路径
  │   ├─ P1: 订单不存在 → 404
  │   ├─ P1: 订单已发货（不可取消）→ 422
  │   ├─ P1: 订单已取消（重复取消）→ 422
  │   ├─ P1: reason 为空 → 400
  │   └─ P2: reason 超长 → 400
  │
  ├─ 权限场景
  │   ├─ P1: 未登录 → 401
  │   └─ P1: 非订单创建者且非管理员 → 403
  │
  ├─ DB 校验（内嵌在正常路径中）
  │   ├─ Orders 表：Status 变为已取消
  │   ├─ Inventory 表：库存回补
  │   └─ 失败场景：Orders 表 Status 不变
  │
  └─ 前置数据
      └─ 需要一个 Pending 状态的订单（先创建再取消）
```

### 转化为 AI 命令

```
/case-design order 取消订单接口 PUT /api/v1/orders/{order_id}/cancel，
业务规则：只有 Pending 状态可取消，已发货不可取消，取消后库存回补，
只有创建者或管理员可操作
```

---

# 第四部分：新增第二个业务流程 — 支付

> 现在你已经完成了"创建订单"的全流程。  
> 接下来为"支付"业务线新增测试。流程完全相同，这里用精简版演示。

## 18. 完整操作流程（精简版）

### 第一步：写 spec

```markdown
# specs/payment/make-payment.md

## 基本信息
- 接口: POST /api/v1/payments
- 认证: 需要登录 Token

## 请求参数
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| order_id | string | 是 | 订单号 |
| payment_method | string | 是 | 支付方式: alipay/wechat/bank_card |
| amount | float | 是 | 支付金额 |

## 正常响应 (200)
{ "code": 0, "data": { "payment_id": "PAY-xxx", "status": "paid" } }

## 错误响应
| HTTP | code | message | 触发条件 |
|---|---|---|---|
| 400 | 1001 | "order_id is required" | 缺少订单号 |
| 404 | 2001 | "order not found" | 订单不存在 |
| 422 | 3001 | "order already paid" | 订单已支付 |
| 422 | 3002 | "amount mismatch" | 金额不匹配 |

## 数据库影响
- Payments 表新增记录
- Orders 表 Status 更新为已支付
```

### 第二步：拆分用例

```
/case-design payment 支付接口 specs/payment/make-payment.md
```

### 第三步：生成代码

```
/write-tests 根据 specs/payment/make-payment.md 生成：
- testcase/payment/test_make_payment_e2e.py
- token 从 auth_store.py 获取
- 前置：需要先创建一个 Pending 订单
- DB 校验：Payments 表 + Orders 表状态更新
```

### 第四步：DB 校验

```
/data-verify testcase/payment/test_make_payment_e2e.py，
Payments 表校验 payment_method/amount/status，
Orders 表校验 Status 变为已支付
```

### 第五步：报告装饰

```
/report-decorate testcase/payment/test_make_payment_e2e.py
```

### 第六步：合规自检

```
/compliance-check
```

### 第七步：运行

```bash
pytest testcase/payment/test_make_payment_e2e.py -v
```

### 第八步：同步执行脚本

```powershell
# run_ecommerce_tests.ps1 新增分组
Invoke-PytestGroup "3. Payment E2E" @(
    "testcase/payment/test_make_payment_e2e.py",
    "-v"
)
```

---

## 19. 新增业务线的 Checklist

每新增一个业务流程，对照这个清单确保不遗漏：

```
□ 1. specs/<业务线>/ 下有 spec 文档
□ 2. /case-design 产出了用例清单并经过审查
□ 3. /spec-review 审查通过（可选）
□ 4. /mock-setup 完成（需要 Mock 时）
□ 5. testcase/<业务线>/ 下有测试代码
□ 6. /data-verify 补全了 DB 校验
□ 7. /report-decorate 补全了 Allure 注解
□ 8. /compliance-check 通过
□ 9. pytest 运行通过
□ 10. run_xxx.ps1 / .sh 已同步更新
□ 11. 数据清理策略已实现
□ 12. variables.yaml / override 已更新（如有新配置）
□ 13. CI 配置已更新（如有）
```

---

# 第五部分：日常操作

## 20. 每日工作流

### 开始工作前

```bash
# 1. 拉取最新代码
git pull

# 2. 安装可能更新的依赖
pip install -r requirements.txt

# 3. 运行 smoke 测试，确认环境正常
pytest testcase/ -m smoke -v
```

### 开发新测试时

```
1. 在 specs/ 写或更新 spec 文档
2. /case-design → 审查用例清单
3. /spec-review → 审查 spec 质量（可选）
4. /mock-setup → 搭建 Mock 服务（按需）
5. /write-tests → 审查生成的代码
6. /data-verify → 补全 DB 校验
7. /report-decorate → 补全注解
8. /compliance-check → 确认合规
9. pytest 运行 → 确认通过
10. 更新执行脚本
11. git add + commit
```

### 下班前

```bash
# 运行全量测试
pytest testcase/ -v

# 或分组运行
.\run_ecommerce_tests.ps1

# 提交代码
git add .
git commit -m "feat: 新增 xxx 测试"
git push
```

---

## 21. 测试失败排查

### 失败时的第一反应

**不要直接改代码。** 先调用 `/debug-failure` 分析根因。

### 你输入

```
/debug-failure
testcase/order/test_order_creation_e2e.py::TestOrderCreation::test_CreateOrder_AllParams
返回 AssertionError: 订单 ORD-xxx 未在数据库中找到
```

### AI 分析

AI 会检查以下几个方向：

| 检查方向 | AI 会做什么 |
|---|---|
| 断言值 | 检查失败断言的期望值和实际值 |
| 请求参数 | 检查 Allure attach 中的请求参数是否正确 |
| DB 状态 | 检查 DB 中是否有对应记录（可能延迟落库） |
| spec 对照 | 检查 spec 描述与实际接口行为是否一致 |
| 归类 | 给出根因分类（测试 bug / 系统 bug / 环境问题） |

### 常见根因与修复

| 根因 | 现象 | 修复 |
|---|---|---|
| 异步落库延迟 | DB 查询返回 None | 把直接查询改为轮询 `while time.monotonic() <= deadline` |
| 测试数据被他人修改 | 断言值不匹配 | 使用唯一测试数据（UUID） |
| Token 过期 | 401 错误 | 检查 auth_store.py 的 token 刷新逻辑 |
| 环境变更 | 接口行为改变 | 与开发确认是否有发布变更 |
| 被测系统 bug | spec 说应该 A 但实际 B | 提 bug 给开发，测试逻辑不改 |

---

## 22. 需求变更时怎么改

### 变更流程

```
需求变更
  │
  ▼ 1. 先改 spec 文档
  │    更新 specs/order/xxx.md
  │    在变更记录表中标注变更内容
  │
  ▼ 2. 重新拆分用例
  │    /case-design 重新生成用例清单
  │    对比新旧清单，确认新增/删除/修改的用例
  │
  ▼ 3. 修改测试代码
  │    根据变更内容修改 testcase/ 中的代码
  │    注意同步修改：断言、DB 校验、清理策略
  │
  ▼ 4. 重新自检
  │    /compliance-check
  │
  ▼ 5. 运行验证
       pytest 确认通过
```

### 核心原则

> **永远先改 spec，再改代码。** 不要直接改代码然后忘了更新 spec。

---

## 23. 新人入职交接清单

当新同事加入团队时，按以下顺序交接：

### Day 1：环境搭建

```
□ 安装 Python 3.9+、Claude Code
□ 克隆项目代码
□ 创建虚拟环境 + pip install -r requirements.txt
□ 配置 variables_override.yaml（找老同事拿测试环境凭据）
□ 运行 pytest testcase/order/test_smoke.py -v 确认环境正常
```

### Day 2：了解框架

```
□ 阅读 USER-GUIDE.md 第一部分（入门篇）
□ 阅读 specs/order/create-order.md 了解 spec 格式
□ 阅读 testcase/order/test_order_creation_e2e.py 了解代码规范
□ 尝试运行 /case-design 看 AI 输出什么
```

### Day 3：上手实操

```
□ 选一个未覆盖的接口
□ 按本手册第二部分的流程完整走一遍 8 步工作流
□ 让老同事 review 生成的 spec 和代码
```

---

# 附录

## A. 操作命令速查卡

打印这张卡片放在工位上：

```
┌─────────────────────────────────────────────────────────┐
│              TestSpec 日常操作速查                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  【新增测试】                                             │
│    1. 写 spec     → specs/<业务线>/<接口>.md               │
│    2. 拆分用例    → /case-design <业务线> <接口名>          │
│    3. 审查规约    → /spec-review <spec 路径>  [可选]       │
│    4. 设计数据    → /test-data <描述>        [可选]        │
│    5. 生成代码    → /write-tests <描述>                    │
│    6. 设计断言    → /assertion-design <JSON> [可选]        │
│    7. 补全校验    → /data-verify <文件路径>                 │
│    8. 装饰报告    → /report-decorate <文件路径>             │
│    9. 合规自检    → /compliance-check                      │
│   10. 运行测试    → pytest testcase/<业务线>/ -v            │
│   11. 更新脚本    → 编辑 run_xxx.ps1 / .sh                │
│                                                         │
│  【扩展命令】                                             │
│    /mock-setup    → 搭建 Mock 服务            [按需]      │
│    /contract-test → 生成契约测试              [按需]      │
│    /analyze-ci-failures → 分析 CI 失败        [按需]      │
│    /spec-diff     → 对比规约变更              [按需]      │
│                                                         │
│  【排查失败】                                             │
│    /debug-failure <失败的测试名或报错信息>                   │
│                                                         │
│  【每日检查】                                             │
│    pytest testcase/ -m smoke -v    （环境冒烟）            │
│    python scripts/check_compliance.py （合规自检）          │
│                                                         │
│  【需求变更】                                             │
│    先改 spec → 再改代码 → 重新自检                         │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## B. 新增业务流程 Checklist

```
┌─────────────────────────────────────────────────────────┐
│           新增业务流程 Checklist                            │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  准备阶段                                                │
│  □ specs/<业务线>/ 目录已创建                              │
│  □ spec 文档已编写（含参数表 + 错误码 + DB 影响）            │
│  □ spec 已经过产品/开发确认                                │
│  □ /spec-review 已执行（可选，AI 审查 spec 质量）           │
│  □ /mock-setup 已执行（需要 Mock 服务时）                   │
│                                                         │
│  用例设计                                                │
│  □ /case-design 已执行                                   │
│  □ 用例清单覆盖了正常/异常/边界/权限                       │
│  □ 优先级 P0/P1/P2 已标注                                │
│  □ 用例清单已经过审查                                      │
│                                                         │
│  代码生成                                                │
│  □ /write-tests 已执行                                   │
│  □ 清理策略已实现（autouse fixture）                       │
│  □ cleanup 注册在断言之前                                 │
│  □ 异常场景使用了 assert_status=None                      │
│  □ DB 校验使用了轮询（异步场景）                            │
│                                                         │
│  质量保障                                                │
│  □ /data-verify 已执行，DB 校验完整                       │
│  □ /report-decorate 已执行，Allure 注解完整               │
│  □ /compliance-check 通过                                │
│  □ pytest 运行全部通过                                    │
│                                                         │
│  收尾                                                    │
│  □ run_xxx.ps1 / .sh 已更新                              │
│  □ variables.yaml 已更新（如有新配置）                     │
│  □ git add + commit                                      │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

> **文档版本**：v1.2.0  
> **配套文档**：USER-GUIDE.md（完整参考手册）  
> **示例业务**：电商订单管理系统（order / payment / inventory）
