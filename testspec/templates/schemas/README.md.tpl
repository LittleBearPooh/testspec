# API 契约 Schema

存放 JSON Schema 文件，供 `utils/contract_checker.py` 和
`/contract-test` 技能使用。

## 用法

```python
from utils.contract_checker import validate_response
validate_response(resp.json(), schema="order-detail")
```

## 文件命名

使用 kebab-case，与接口 spec id 保持一致。
例如：`order-create.yaml`、`payment-detail.yaml`
