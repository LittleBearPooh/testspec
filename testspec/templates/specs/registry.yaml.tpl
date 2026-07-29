# {{PROJECT_NAME_TITLE}} — Spec 注册表
#
# 本文件是 TestSpec 框架的机器可读规格索引。
# 所有 spec 文档必须在此注册，才能被工具链（validate / coverage / generate / diff）识别。
#
# 维护规则：
#   1. 每新增一个 specs/<业务线>/<file>.md，必须在此文件中添加对应条目
#   2. spec 文件变更时，同步更新此文件中的参数/响应/规则定义
#   3. 运行 python scripts/validate_specs.py 校验本文件的完整性
#   4. 运行 python scripts/check_coverage.py 查看 spec → test 覆盖率
#
# TestSpec 版本: {{TESTSPEC_VERSION}}

version: "2.1"

# =====================================================================
# 规格定义
# =====================================================================
# 每个 spec 条目包含：
#   id            — 唯一标识（kebab-case），用于追溯和关联
#   file          — spec 文档路径（相对于项目根目录）
#   api           — 接口定义（method + path）
#   auth          — 认证方式（bearer / api_key / basic / none / inherit）
#   parameters    — 请求参数列表（含 in 字段：path/query/body/header）
#   responses     — 响应定义（正常 + 异常）
#   response_schema — 响应 JSON Schema 文件名（schemas/ 目录下）
#   db_effects    — 数据库影响（写操作 INSERT/UPDATE/DELETE/UPSERT，读操作 SELECT）
#   sla_ms        — 响应时间 SLA（毫秒），用于性能断言
#   business_rules — 业务规则（可选，但推荐）
#
#   --- 以下字段用于运维和分组 ---
#   environment   — 限定运行环境（如 staging / prod），不设置则所有环境可运行
#   tags          — 自定义标签列表，用于过滤和分组（如 [smoke, critical-path]）
#   priority      — 优先级（P0 / P1 / P2），影响测试执行顺序和报告分组
#   enabled       — 是否启用（默认 true），设为 false 临时禁用 spec 而不删除
#   dependencies  — 前置依赖 spec id 列表（如需要先创建用户才能测试订单）
#   related_specs — 关联 spec id 列表（用于端到端追溯和影响分析）
#   headers       — 非 auth 必需请求头（如 X-Tenant-ID）
#
#   --- 以下字段用于状态机和并发测试设计 ---
#   state_transitions — 状态机转换规则（适用于有状态资源）
#     initial_state: 初始状态值（字符串）
#     allowed: 合法转换列表，格式 "from → to"
#     forbidden: 非法转换列表，格式 "from → to"（必须被系统拒绝）
#   rate_limiting — 限流/并发测试配置
#     requests_per_second: 接口正常限流阈值（整数）
#     burst_limit: 突发请求上限（整数）
#     concurrent_users: 并发用户数（整数，用于并发竞态用例设计）

specs:

  # ----- 示例：创建订单 -----
  # 请删除或修改此示例，替换为你的真实 spec

  - id: "order-create"
    file: "specs/order/create-order.md"
    api:
      method: POST
      path: /api/v1/orders
    auth: bearer
    sla_ms: 500
    priority: P0
    enabled: true
    tags: [smoke, critical-path, order]
    headers:
      X-Tenant-ID: "default"
    parameters:
      - name: product_id
        in: body
        type: string
        required: true
        description: "商品 ID，必须存在于商品表中"
      - name: quantity
        in: body
        type: integer
        required: true
        constraints:
          min: 1
          max: 999
        description: "购买数量"
      - name: shipping_address
        in: body
        type: string
        required: true
        constraints:
          maxLength: 200
        description: "收货地址"
      - name: remark
        in: body
        type: string
        required: false
        constraints:
          maxLength: 100
        description: "订单备注"
    responses:
      "201":
        code: 0
        description: "下单成功"
        fields:
          - name: order_id
            type: string
            nullable: false
          - name: status
            type: string
            nullable: false
          - name: total_amount
            type: number
            nullable: false
          - name: created_at
            type: string
            format: iso-datetime
            nullable: false
      "400":
        codes: [1001, 1002]
        descriptions:
          1001: "缺少必填参数"
          1002: "参数值非法"
      "404":
        codes: [2001]
        descriptions:
          2001: "商品不存在"
      "422":
        codes: [3001]
        descriptions:
          3001: "库存不足"
      "401":
        codes: [4001]
        descriptions:
          4001: "未登录"
      "403":
        codes: [4002]
        descriptions:
          4002: "无下单权限"
    response_schema: "order-create"
    db_effects:
      - table: Orders
        operation: INSERT
        key_fields: [Status, ProductId, Quantity, CreatedBy, CreatedAt]
      - table: OrderItems
        operation: INSERT
        key_fields: [OrderId, ProductId, Quantity, UnitPrice]
      - table: Inventory
        operation: UPDATE
        key_fields: [Stock]
    business_rules:
      # type 枚举说明:
      #   idempotency   — 重复请求行为一致
      #   precondition  — 操作的前置条件
      #   invariant     — 始终成立的不变量
      #   transition    — 状态机状态转换规则（如 SHIPPED → CANCELLED 不允许）
      #   authorization — 权限/角色约束
      - id: BR-001
        description: "1 分钟内不能重复提交相同商品的订单"
        type: idempotency
      - id: BR-002
        description: "库存不足时不创建订单，不扣库存"
        type: precondition
    related_specs: ["order-cancel", "payment-create"]
    state_transitions:
      initial_state: "pending"
      allowed:
        - "pending → paid"
        - "pending → cancelled"
      forbidden:
        - "shipped → pending"
        - "cancelled → paid"
        - "cancelled → shipped"

  # ----- 在此添加更多 spec -----
  # - id: "order-cancel"
  #   file: "specs/order/cancel-order.md"
  #   api:
  #     method: PUT
  #     path: /api/v1/orders/{order_id}/cancel
  #   auth: bearer
  #   sla_ms: 300
  #   parameters:
  #     - name: order_id
  #       in: path
  #       type: string
  #       required: true
  #     - name: reason
  #       in: body
  #       type: string
  #       required: true
  #       constraints:
  #         maxLength: 200
  #   responses:
  #     "200":
  #       code: 0
  #       description: "取消成功"
  #       fields: [order_id, status, cancelled_at]
  #     "404":
  #       codes: [2001]
  #     "422":
  #       codes: [3001, 3002]
  #   response_schema: "order-cancel"
  #   db_effects:
  #     - table: Orders
  #       operation: UPDATE
  #       key_fields: [Status, CancelledAt, CancelReason]
  #     - table: Inventory
  #       operation: UPDATE
  #       key_fields: [Stock]

  # ----- 示例：查询订单（GET，含 SELECT db_effect）-----
  # - id: "order-detail"
  #   file: "specs/order/order-detail.md"
  #   api:
  #     method: GET
  #     path: /api/v1/orders/{order_id}
  #   auth: bearer
  #   sla_ms: 200
  #   parameters:
  #     - name: order_id
  #       in: path
  #       type: string
  #       required: true
  #   responses:
  #     "200":
  #       code: 0
  #       description: "查询成功"
  #       fields: [order_id, status, total_amount, items, created_at]
  #     "404":
  #       codes: [2001]
  #       descriptions:
  #         2001: "订单不存在"
  #   response_schema: "order-detail"
  #   db_effects:
  #     - table: Orders
  #       operation: SELECT
  #       key_fields: [OrderId, Status, TotalAmount, CreatedAt]
