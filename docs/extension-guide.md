# TestSpec 扩展指南

本文档说明如何为 TestSpec 框架添加新的测试类型、自定义技能和工具桩。

---

## 添加新的测试类型

TestSpec 内置 4 种测试类型（api / unit / integ / e2e）。如果你的项目需要新类型（如 `performance`、`security`），按以下步骤扩展：

### 1. 在 constants.py 中注册新类型

在 `testspec/constants.py` 的 `TEST_TYPES` 注册表中添加新条目：

```python
TEST_TYPES.register("5", ("perf", "性能测试（负载/压力/基准）"))
```

### 2. 在 context.py 中构建对应标志

在 `testspec/context.py` 中：

1. 在 `ProjectContext` TypedDict 中添加布尔标志键：

```python
IS_PERF: bool
```

2. 在 `_build_test_type_ctx()` 中填充该标志：

```python
"IS_PERF": "perf" in types,
```

### 3. 在模板中添加条件块

在需要差异化的模板文件中，添加新的条件块：

```markdown
{{#IF_IS_PERF}}
## 性能测试专属规则
- 每个测试函数必须设置 `@pytest.mark.performance` 标记
- 响应时间断言使用 `assert elapsed < threshold`
- 并发测试使用 `pytest-xdist` 的 `--numprocesses` 参数
{{/IF_IS_PERF}}
```

### 4. 更新步骤 5（数据验证）的泛化逻辑

在 `05-data-verify.md.tpl` 中添加性能测试的验证方案：

```markdown
{{#IF_IS_PERF}}
## 性能指标验证方案
- 响应时间：P50 / P95 / P99 延迟
- 吞吐量：RPS（Requests Per Second）
- 错误率：在高并发下的失败比例
- 资源占用：CPU / 内存 / 网络带宽
{{/IF_IS_PERF}}
```

### 5. 更新合规检查脚本

在 `check_compliance.py.tpl` 中添加对应的扫描规则。

---

## 自定义技能

### 添加新技能

1. 在 `templates/skills/` 下创建新模板文件 `NN-skill-name.md.tpl`
2. 在 `testspec/catalogs.py` 的 `SKILL_FILES` 元组中注册
3. 在 `00-test-workflow.md.tpl` 的步骤表中添加引用

### 修改现有技能

直接编辑对应的 `.tpl` 文件。注意保持：
- `description:` frontmatter 行（Claude Code 需要）
- `$ARGUMENTS` 占位符（接收用户输入）
- 中文书写规范

### 调整步骤顺序

在 `00-test-workflow.md.tpl` 中修改步骤表即可。步骤编号是逻辑顺序，不是文件名前缀。

---

## 自定义工具桩

### 替换 HTTP 客户端

如果你的项目不使用 `requests`，替换 `templates/utils/http_client.py.tpl`：

- 保持 `HttpClient` 类名和 `request()` 方法签名
- 保持 `_SENTINEL` / `assert_status` 模式
- 保持 `_last_response` 存储（供 conftest 在失败时 attach）
- 保持上下文管理器支持

### 添加新工具模块

1. 在 `templates/utils/` 下创建 `your_module.py.tpl`
2. 在 `UtilsSection.render() in testspec/sections.py` 中添加渲染调用
3. 在 `CLAUDE.md.tpl` 中添加使用说明章节

### 添加新的数据库驱动

在 `templates/utils/db_client.py.tpl` 中添加条件块：

```python
{{#IF_DB_ORACLE}}
import oracledb
from dbutils.pooled_db import PooledDB
# pool uses oracledb.connect(), service_name parameter
{{/IF_DB_ORACLE}}
```

同时在 `testspec/constants.py` 的 `DB_TYPES` 注册表中注册（`DB_TYPES.register(...)`），并在 `testspec/catalogs.py` 的 `DB_PORT_MAP` 和 `DB_DRIVER_MAP` 中添加对应条目。

---

## 自定义执行脚本

### 调整分组策略

编辑 `templates/execution/run_tests.ps1.tpl`（或 `.sh.tpl`）：
- 修改 `Invoke-PytestGroup` 的参数
- 添加新的固定分组（如 "性能测试"、"安全扫描"）
- 调整并行度参数（`-n` 值）

### 添加 CI/CD 集成

在脚本末尾添加：

```powershell
# CI 模式：生成 JUnit XML 供 CI 系统解析
if ($env:CI -eq "true") {
    python -m pytest testcase/ --junit-xml=junit-results.xml -q
}
```

---

## 自定义合规规则

编辑 `templates/scripts/check_compliance.py.tpl`：

- `WRITE_KEYWORDS`：写操作关键词集合（可按项目语言调整）
- `SCAN_DIRS`：扫描目录（默认 `testcase/`）
- 添加项目特定的检查规则（如"所有 E2E 测试必须有清理 fixture"）

---

## 贡献与反馈

欢迎贡献改进。常见扩展需求：

| 扩展方向 | 修改文件 | 难度 |
|---|---|---|
| 新测试类型 | testspec/constants.py + testspec/context.py + 多个 .tpl | 中 |
| 新技能命令 | templates/skills/ 新增 + catalogs.py SKILL_FILES + workflow 更新 | 低 |
| 新数据库驱动 | templates/utils/db_client.py.tpl + constants.py + catalogs.py | 低 |
| 新报告工具 | templates/skills/06-report-decorate.md.tpl + conftest | 中 |
| 新编程语言 | 工具桩全部重写 + constants.py + context.py | 高 |

---

## 模板引擎参考

TestSpec 使用简易模板引擎，支持以下语法：

| 语法 | 说明 | 示例 |
|---|---|---|
| `{{KEY}}` | 占位符替换 | `{{PROJECT_NAME}}` → `my-project` |
| `{{#IF_KEY}}...{{/IF_KEY}}` | 条件包含（KEY 为真时保留） | `{{#IF_HAS_DB}}...{{/IF_HAS_DB}}` |
| `{{#IF_NOT_KEY}}...{{/IF_NOT_KEY}}` | 条件排除（KEY 为假时保留） | `{{#IF_NOT_HAS_ALLURE}}...{{/IF_NOT_HAS_ALLURE}}` |
| `{{#FOR var IN LIST_KEY}}...{{var}}...{{/FOR}}` | 循环遍历列表 | `{{#FOR biz IN BUSINESS_LINES_RAW}}...{{biz}}...{{/FOR}}` |

条件块和 FOR 循环支持嵌套（最多 `_MAX_ITERATIONS=10` 层，不同 key）。
实现位于 `testspec/renderer.py` 的 `render_template()` 函数。

#### 残留占位符检测

渲染完成后，引擎会自动扫描输出中残留的 `{{KEY}}` 占位符：

- **默认行为**（`strict=False`）：残留占位符触发 `UserWarning`，但不影响输出
- **严格模式**（`strict=True`）：残留占位符抛出 `TemplateError`

过滤规则：双下划线开头的键（如 `{{__ESCAPED__}}`）和全小写键（如 `{{param}}`，通常是 Python f-string 变量）不会触发检测。TestSpec 上下文键约定为全大写 UPPER_CASE。

```python
from testspec.renderer import render_template

# 默认模式：残留占位符触发警告
render_template("{{PROJECT_NAME}} {{UNKNOWN}}", {"PROJECT_NAME": "my-proj"})
# → "my-proj {{UNKNOWN}}"  (附带 UserWarning)

# 严格模式：残留占位符抛出异常
render_template("{{PROJECT_NAME}}", {"PROJECT_NAME": "my-proj"}, strict=True)
# → "my-proj"  (无异常)
```
