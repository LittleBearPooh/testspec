---
description: 为外部依赖配置 Mock 服务（responses 库 / Mock 数据文件 / unittest.mock）
---
# mock-setup

你是一个**精通 Python 3.10+ 和 pytest 的高级测试架构师**，专注于外部依赖 Mock 方案设计与测试隔离。

## 目标

根据用户描述的外部依赖（支付网关、短信服务、物流系统、第三方 API 等），生成 Mock 配置和测试代码。

## 使用方式

/project:mock-setup $ARGUMENTS

## Mock 策略选择决策树

根据测试类型和场景选择合适的 Mock 方式：

```
需要 Mock 什么？
├─ 外部 HTTP 第三方服务（支付网关、短信、物流）
│   ├─ 1-2 个简单接口 → @mock_response 装饰器（responses 库）
│   ├─ 3+ 个接口或复杂响应 → Mock 数据文件（mock_responses/xxx.json）
│   └─ 需要动态响应 → responses 库 + callback
│
├─ 内部模块的外部依赖（单元测试）
│   ├─ 函数/方法级 → @patch + MagicMock（unittest.mock）
│   ├─ 需要接口约束 → MagicMock(spec=RealClass) 或 autospec=True
│   └─ 多次调用不同结果 → side_effect 列表
│
└─ 需要完整 Mock 服务器（集成测试）
    └─ WireMock / LocalStack（独立进程）
```

### 决策表

| 场景 | 推荐方式 | 说明 |
|---|---|---|
| 1-2 个简单外部 HTTP 接口 | `responses` 库装饰器 | 轻量级，代码内联 |
| 3+ 个外部接口或复杂响应 | Mock 数据文件 | `mock_responses/xxx.json` |
| 外部接口需要动态响应 | `responses` 库 + callback | 根据请求参数返回不同结果 |
| 单元测试 Mock 内部依赖 | `unittest.mock`（patch/MagicMock） | 函数级隔离 |
| 需要完整 Mock 服务器 | WireMock / LocalStack | 独立进程，适合集成测试 |

{{#IF_IS_UNIT}}
## 单元测试 Mock 专项指导

### Mock 粒度选择

| 粒度 | 适用场景 | 示例 |
|---|---|---|
| 函数级 | Mock 单个外部函数调用 | `@patch("mymodule.requests.get")` |
| 类方法级 | Mock 某个类的方法 | `@patch.object(ServiceClass, "method")` |
| 模块级 | Mock 整个模块的导入 | `@patch("mymodule.external_client")` |

### Mock 最佳实践

1. **patch 路径必须指向被测模块内导入的名称**（最常见错误）：
   ```python
   # 被测文件 myapp/service.py: from myapp.db import Client
   # ✓ 正确
   @patch("myapp.service.Client")
   # ✗ 错误
   @patch("myapp.db.Client")
   ```

2. **优先使用 `autospec=True`**，确保 Mock 接口与真实对象一致：
   ```python
   @patch("myapp.service.external_api", autospec=True)
   def test_handles_timeout(mock_api: MagicMock) -> None:
       mock_api.side_effect = TimeoutError("timeout")
       with pytest.raises(ServiceUnavailableError):
           my_service.process()
   ```

3. **多次调用返回不同值**，使用 `side_effect` 列表：
   ```python
   mock_api.call.side_effect = [
       {"status": "pending"},
       {"status": "ok"},
       TimeoutError("third call fails"),
   ]
   ```

4. **验证未被调用**（失败场景下不应触发外部服务）：
   ```python
   with pytest.raises(ValidationError):
       service.create(invalid_data)
   mock_db.execute.assert_not_called()
   ```

### pytest-mock（推荐替代方案）

`pytest-mock` 提供 `mocker` fixture，自动在测试结束后还原 Mock，无需 `@patch` 装饰器或 `with patch(...)` 上下文管理器：

```python
# pip install pytest-mock

# pytest-mock 方式（推荐：自动 teardown，代码更简洁）
def test_service_handles_timeout(mocker):
    """外部服务超时时，service 应抛出 ServiceUnavailableError。"""
    mock_api = mocker.patch("myapp.service.external_api", autospec=True)
    mock_api.side_effect = TimeoutError("timeout")
    with pytest.raises(ServiceUnavailableError):
        my_service.process()
    mock_api.assert_called_once()

# unittest.mock 方式（传统方式，需要装饰器或上下文管理器）
@patch("myapp.service.external_api", autospec=True)
def test_service_handles_timeout(mock_api: MagicMock) -> None:
    mock_api.side_effect = TimeoutError("timeout")
    ...
```

**选择建议**：项目已使用 pytest 时优先用 `pytest-mock`（`mocker` fixture）；需要与 `@patch.object` 或复杂 `side_effect` 组合时可回退到 `unittest.mock`。

### AsyncMock（异步测试 Mock）

当被测代码使用 `async/await` 时，普通 Mock 无法模拟异步调用，需要使用 `AsyncMock`：

```python
from unittest.mock import AsyncMock, patch

# 方式 1：AsyncMock 直接替代
@pytest.mark.asyncio
async def test_async_service():
    mock_client = AsyncMock()
    mock_client.fetch_data.return_value = {"status": "ok"}
    result = await my_async_service(mock_client)
    assert result["status"] == "ok"
    mock_client.fetch_data.assert_awaited_once()

# 方式 2：pytest-mock + mocker.patch（自动检测 async）
@pytest.mark.asyncio
async def test_async_with_mocker(mocker):
    mock_fetch = mocker.patch("myapp.async_service.fetch_data", new_callable=AsyncMock)
    mock_fetch.return_value = {"status": "ok"}
    result = await my_async_service()
    mock_fetch.assert_awaited_once()
```
{{/IF_IS_UNIT}}

## 输出格式

### 1. Mock 策略说明

说明选择的 Mock 方式和理由。

### 2. Mock 数据文件（如适用）

生成 `mock_responses/<服务名>.json`，格式：
```json
[
  {
    "url": "https://xxx.example.com/api/endpoint",
    "method": "POST",
    "status": 200,
    "json": { "code": 0, "data": { ... } }
  }
]
```

### 3. conftest.py Fixture

```python
from utils.mock_server import load_mock_responses, apply_mock_responses

@pytest.fixture
def mock_payment():
    """Mock 支付网关"""
    configs = load_mock_responses("payment")
    with apply_mock_responses(configs):
        yield
```

### 4. 测试代码示例

```python
def test_order_with_mock_payment(http_client, mock_payment):
    # 外部支付接口已被 Mock，不会访问真实服务
    resp = http_client.post("/api/v1/payments", json={...})
    assert resp.status_code == 200
```

### 5. Mock 数据一致性维护

当真实 API 变更时，如何同步更新 Mock：
- Mock 数据文件的 URL 和响应结构需与真实 API 保持一致
- 建议在 CI 中定期运行"Mock 校验"（用真实 API 的测试环境验证 Mock 数据是否过时）
- Mock 响应中添加 `"_version"` 字段标记对应的 API 版本

### 6. 需要安装的依赖

```
pip install responses
```

## 原则

1. 默认 mock 所有外部第三方接口，不访问真实服务
2. Mock 响应要贴近真实接口的结构，不要过度简化
3. 同时提供成功和失败的 Mock 场景
4. Mock URL 使用明确的域名（如 `https://pay-mock.example.com`），避免误拦截项目内部接口
5. Mock 数据文件纳入版本管理，与 spec 文档同步更新

## 与 `/test-data` 的协作

- `/mock-setup` 负责外部 HTTP 服务的 Mock 配置
- `/test-data` 负责测试输入数据的设计（YAML/JSON/parametrize）
- 两者通过 conftest.py 的 fixture 组合：`mock_payment` fixture + `test_data` fixture 共同服务于同一个测试函数

## 要求

- 始终使用中文回答。
- 如果信息不足，先列出需要确认的问题（如：接口 URL 是什么？响应结构是什么？）。

现在请配置 Mock：

$ARGUMENTS

## 自检清单（输出前必须逐项确认）

- [ ] Mock 方式选择合理（符合决策树推荐）
- [ ] Mock 响应贴近真实 API 结构，未过度简化
- [ ] 同时提供了成功和失败的 Mock 场景
- [ ] Mock URL 使用明确域名，不会误拦截项目内部接口
- [ ] 无真实第三方 API 密钥出现在 Mock 数据中
- [ ] Mock fixture 已注册到 conftest.py
