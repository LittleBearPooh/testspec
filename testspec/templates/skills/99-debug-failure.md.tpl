---
description: 失败归类 + 根因分析 + 最小修复方案
---
# debug-failure

你是一个**精通 Python 3.10+ 和 pytest 的高级测试架构师**，专注于自动化测试失败分析与根因定位。你熟悉 pytest fixture 生命周期、xdist 并发模型、以及常见的环境/数据/配置问题模式。

## 目标

根据自动化测试失败日志、请求响应、数据结果、pytest 报错，定位失败原因并给出修复方案。

## 使用方式

/project:debug-failure $ARGUMENTS

## 常见 pytest 错误速查表

| 错误信息 | 常见原因 | 修复方案 |
|---|---|---|
| `fixture 'xxx' not found` | fixture 名称拼写错误或未在 conftest 中定义 | 检查 fixture 名称和 conftest 层级 |
| `ScopeMismatch` | function fixture 依赖了 session fixture 的有状态数据 | 调整 scope 或使用 function scope |
| `pytest.mark.xxx unknown` | marker 未在 pytest.ini 中声明 | 在 `[pytest] markers` 节中注册 |
| `RecursionError` | fixture 循环依赖（A → B → A） | 检查 fixture 依赖链，打破循环 |
| `xdist worker crash` | session fixture 写入共享文件或全局状态 | 使用 `filelock` 或 `worker_id` 隔离 |
| `ModuleNotFoundError` | import 路径错误或 `__init__.py` 缺失 | 检查 PYTHONPATH 和目录结构 |
| `PermissionError` | 日志/报告目录被其他进程占用 | 使用唯一目录名或 `filelock` |
| `ImportError: cannot import` | 循环 import 或第三方包未安装 | 检查 `requirements.txt` 并 `pip install` |
| `assert ... (comparison failed)` | 断言值不匹配，可能是异步落库未完成 | 添加 `poll_until` 轮询等待 |
| `ConnectionRefusedError` | 被测服务未启动或 base_url 配置错误 | 检查服务状态和 `variables.yaml` |
| `TimeoutError` | 请求超时或轮询超时 | 检查服务可用性，适当增加 timeout |
| `JSONDecodeError` | 响应非 JSON 格式（如 HTML 错误页） | 先检查 `resp.status_code` 和 `resp.text` |
| `SyntaxError: X \| Y` | PEP 604 联合类型语法需要 Python 3.10+ | 升级 Python 或添加 `from __future__ import annotations` |
| `TypeError: 'type' object is not subscriptable` | `list[str]` 等 PEP 585 语法需要 Python 3.9+ | 升级 Python 或添加 `from __future__ import annotations` |

## 排查决策树

遇到测试失败时，按以下顺序逐步定位根因：

```
测试失败日志
  │
  ├─ 1. 报错类型是什么？
  │   ├─ AssertionError（断言失败）
  │   │   ├─ 断言的期望值 vs 实际值是什么？
  │   │   ├─ 是否与 spec 文档描述一致？→ 不一致 = 被测系统 bug
  │   │   ├─ 是否涉及动态字段（时间/ID）？→ 是 = 断言过严，改用格式断言
  │   │   └─ 是否涉及浮点数？→ 是 = 改用 pytest.approx
  │   │
  │   ├─ ConnectionError / ConnectionRefusedError
  │   │   ├─ 被测服务是否启动？
  │   │   ├─ base_url 配置是否正确？（检查 variables.yaml）
  │   │   └─ 网络/防火墙是否阻断？
  │   │
  │   ├─ fixture 'xxx' not found / ScopeMismatch
  │   │   └─ 检查 conftest.py 层级和 fixture scope
  │   │
  │   ├─ 401 / 403（HTTP 接口适用）
  │   │   ├─ Token 是否过期？→ 刷新 Token
  │   │   └─ 账号权限是否正确？→ 检查 test_accounts 配置
  │   │
  │   └─ 其他异常 → 查上方"常见 pytest 错误速查表"
  │
  ├─ 2. 是否有 DB 校验？
  │   └─ 是 → 检查异步落库（是否用了 poll_until？）+ SQL 查询条件是否正确
  │
  ├─ 3. 是否有外部依赖？
  │   └─ 是 → 检查 Mock 配置是否正确（URL、响应结构）
  │
  └─ 4. 是否只在并发时失败？
      └─ 是 → 检查数据唯一性（UUID）+ session scope fixture 隔离
```

## 分析维度

需要判断失败属于以下哪类：

1. 测试代码问题
2. 被测服务/函数问题
3. 测试数据问题
4. 环境配置问题
5. 鉴权 token 问题（HTTP 接口适用）
6. 请求参数问题（HTTP 接口适用）
7. 响应/返回值断言过严
{{#IF_HAS_DB}}
8. 数据库校验 SQL 错误
{{/IF_HAS_DB}}
9. 数据未清理导致冲突
10. 异步操作未等待（轮询超时或缺少轮询）
11. 第三方依赖不稳定
12. 测试顺序依赖
13. 并发执行导致数据冲突
14. 环境差异导致失败
15. pytest fixture 使用错误

{{#IF_IS_UNIT}}
### 单元测试额外检查（Mock 相关）

以下检查项专用于含 Mock 的单元测试：

- Mock 配置错误（patch 路径、autospec、side_effect）
- **patch 路径错误**：`@patch("wrong.module.ClassName")` 而非 `@patch("tested_module.ClassName")`
- **autospec 不匹配**：Mock 方法签名与真实方法不符导致调用报错
- **side_effect 配置错误**：side_effect 列表耗尽导致 `StopIteration`，或 side_effect 与 return_value 同时设置冲突
- **Mock 层级错误**：patch 了错误层次的对象（如 patch 了基类而非子类中的重写方法）
- **assert_called_with 参数不匹配**：断言调用参数与实际调用参数不一致（注意 `call_args` 中的 kwargs 顺序）
{{/IF_IS_UNIT}}

## 必须检查

{{#IF_HAS_HTTP}}
1. 请求 URL 是否正确
2. 请求 method 是否正确
3. headers 是否正确
4. token 是否有效
5. Content-Type 是否正确
6. 请求 body 是否符合接口要求
7. 响应状态码
8. 响应业务码
9. 响应 message
{{/IF_HAS_HTTP}}
{{#IF_HAS_DB}}
10. 数据库是否真实落库
11. SQL 查询条件是否正确
{{/IF_HAS_DB}}
12. 测试数据是否唯一
13. 测试后是否清理数据
14. 是否适合并行执行

{{#IF_IS_UNIT}}
### 单元测试额外检查

15. Mock 是否正确隔离了所有外部依赖（数据库、网络、文件系统）
16. patch 路径是否指向**被测模块内导入的名称**（最常见错误）：
    - 正确示例：被测文件 `myapp/service.py` 中 `from myapp.db import Client`，则 patch 路径为 `myapp.service.Client`
    - 错误示例：`myapp.db.Client`（除非直接测试 db 模块）
17. return_value 是否在调用前设置好（不能在被测函数执行后才设置）
18. `with patch(...)` 作用域是否正确覆盖了被测函数的调用点
{{/IF_IS_UNIT}}

## 输出格式

1. 失败归类
2. 关键证据
3. 根因分析
4. 最小修复方案
5. 推荐修改代码
6. 建议重新执行命令
7. 后续稳定性优化

现在请分析自动化测试失败：

$ARGUMENTS

## 自检清单（输出前必须逐项确认）

- [ ] 已按排查决策树逐层定位根因，未跳过步骤
- [ ] 失败归类明确（测试代码 / 被测系统 / 数据 / 环境 / 配置 五选一）
- [ ] 关键证据已列出（断言值、请求参数、DB 状态、spec 对照）
- [ ] 最小修复方案只改必要的代码，未做无关重构
- [ ] 提供了修复后的重新执行命令
- [ ] 如果根因指向 spec 文档缺陷，建议了同步更新 spec
