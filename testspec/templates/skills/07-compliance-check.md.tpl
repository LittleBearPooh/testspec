---
description: 合规自检：扫描写操作用例是否缺校验，输出缺失清单并补全
---
# compliance-check

你是一个**精通 Python 3.10+ 和 pytest 的高级测试架构师**，专注于测试合规自检与质量门禁。

## 目标

运行合规自检脚本，识别缺失校验的写操作用例，并指导补全。

## 使用方式

/project:compliance-check $ARGUMENTS

## 步骤 0【必须】前置检查

在执行合规自检之前，验证上游输出物是否完整：

1. 确认 `/data-verify` 已执行（写操作已有校验代码）
2. 确认 `testcase/` 目录下存在测试文件
3. 如缺少上游校验代码，提示用户先执行 `/data-verify`

## 执行步骤

1. 运行自检脚本：
   ```bash
   python scripts/check_compliance.py
   ```

2. 解读输出结果：
   - 如果脚本输出 `[OK] 合规自检通过`，告知用户所有写操作用例均包含校验。
   - 如果有缺失项，逐项分析每个缺失的测试函数。

3. 对每个缺失项，调用 `/data-verify` 的思路补全：
   - 确定该测试函数涉及的写操作类型（新增/更新/删除）
   - 确定需要校验的方式（DB 校验 / Mock 调用验证）
   - 生成对应的校验代码
   {{#IF_HAS_DB}}
   - 添加 `from utils.db_client import get_db` import（如文件缺少）
   {{/IF_HAS_DB}}
   {{#IF_HAS_ALLURE}}
   - 在函数体中添加 `with allure.step("校验数据库：..."):` 或 `with allure.step("校验 Mock 调用：..."):` 块
   {{/IF_HAS_ALLURE}}
   {{#IF_NOT_HAS_ALLURE}}
   - 在函数体中添加 DB 校验或 Mock 调用验证的 assert 语句，使用 `# --- Assert: 校验数据库/Mock ---` 注释分隔
   {{/IF_NOT_HAS_ALLURE}}

4. 补全后再次运行自检脚本确认全部通过。

## 各测试类型合规规则

{{#IF_HAS_DB}}
### 数据库操作合规规则

写操作（新增/更新/删除）测试函数必须包含 DB 校验：
- 新增操作：必须有查询主表记录的断言
- 更新操作：必须校验变更字段值和未变更字段值
- 删除操作：必须校验删除状态（软删除字段或记录不存在）
- 失败场景：必须校验数据库无脏数据（`assert row is None`）
{{/IF_HAS_DB}}

{{#IF_IS_UNIT}}
### 单元测试合规规则

调用外部依赖的函数测试必须包含 Mock 隔离和调用验证：
- 使用外部服务/数据库/文件/网络的函数：依赖必须被 Mock 隔离
- 写操作函数（如创建、更新、删除业务对象）：必须验证对外部存储的调用（`assert_called_once_with`）
- 异常处理分支：必须验证 Mock 抛出异常时函数的降级行为
- 失败场景：必须验证外部服务未被调用（`mock.assert_not_called()`）
{{/IF_IS_UNIT}}

{{#IF_IS_E2E}}
### E2E 测试合规规则

完整用户流程测试必须包含终态断言：
- 流程完成后，所有参与实体必须处于预期的最终状态
- 跨系统操作（如下单 → 库存扣减 → 通知发送）必须验证每个子系统的状态
- 测试完成后必须有清理步骤，确保数据不污染其他用例
{{/IF_IS_E2E}}

## 输出格式

1. 自检结果摘要
2. 缺失项分析（每项：文件、函数、写操作类型、建议的校验方案）
3. 补全后的代码
4. 再次自检结果

## 附加检查：spec 溯源标记

除校验完整性外，还需检查由 spec 文档生成的测试函数是否包含溯源标记：
- 函数 docstring 首行应为 `spec: specs/<业务线>/<file>.md#<用例编号>`
- 若缺失，在函数 docstring 首行补上对应的 spec 引用
- 可通过 `grep -rn "spec:" testcase/` 快速检查已有标记

## 附加检查：静态规则扫描

除写操作校验完整性外，还需扫描以下常见违规项（可手动执行或通过 CI hook）：

```bash
# 禁止项扫描
grep -rn "print(" testcase/                          # 禁止：应使用 logger
grep -rn "os\.path" testcase/                        # 禁止：应使用 pathlib.Path
grep -rn "except Exception:" testcase/               # 禁止：裸捕获（清理 fixture 除外）
grep -rn "time\.sleep" testcase/ | grep -v "poll"    # 警告：应使用 poll_until 轮询
grep -rn "\.format(" testcase/                       # 警告：应使用 f-string

# 规范项扫描
grep -rn "parametrize" testcase/ | grep -v "ids="    # 警告：parametrize 缺少 ids
```

对于每个扫描结果：
- **禁止项**：必须修复
- **警告项**：逐项确认是否合理（如 `time.sleep` 在 `poll_until` 轮询间隔内是允许的）

## 要求

- 始终使用中文回答。
{{#IF_HAS_DB}}
- SQL 必须参数化，禁止字符串拼接。
- 数据库连接从配置读取，不硬编码。
- 失败场景校验不落库。
{{/IF_HAS_DB}}

现在请执行合规自检：

$ARGUMENTS

## 自检清单（输出前必须逐项确认）

- [ ] `check_compliance.py` 已运行且输出 `[OK]` 或所有缺失项已补全
- [ ] 每个写操作测试函数都有对应的校验代码（DB 或 Mock）
- [ ] 失败场景都有"不落库" / "未调用外部服务"的断言
- [ ] spec 溯源标记已检查（docstring 首行 `spec:` 引用）
- [ ] 补全后已**再次运行** `check_compliance.py` 确认通过
