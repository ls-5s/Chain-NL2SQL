# SQLite 数据库底座实现说明

## 1. 模块定位

SQLite 数据库底座是 Chain-NL2SQL P0 阶段的安全执行边界，为后续 LangGraph 提供稳定的 `DatabaseExecutor` 接口。

本模块负责：

- 提供固定的电商订单演示数据库；
- 读取数据库 Schema 并生成可检索文档；
- 在执行前校验 SQL 是否为安全的单条只读查询；
- 应用数据库、表和字段访问策略；
- 控制查询超时、连接生命周期和结果行数；
- 对敏感字段脱敏并返回统一结果结构。

本阶段不负责 LangGraph 编排、LLM 调用、FastAPI 查询流程、MySQL 适配和向量检索。

## 2. 目录与职责

```text
app/
├── api/authorization.py       # AccessPolicy：数据库、表、字段和脱敏策略
├── db/
│   ├── base.py                # DatabaseExecutor 协议和底层异常边界
│   ├── connection_manager.py  # 创建只读 SQLite 连接
│   ├── result_formatter.py    # 行数限制、字段脱敏和结果标准化
│   ├── security_policy.py     # sqlglot AST 只读和访问策略校验
│   └── sqlite_adapter.py      # SQLite 适配器和执行生命周期
└── rag/
    ├── introspector.py        # 读取 SQLite 表、字段、主键和外键
    ├── normalizer.py          # 标准化元数据模型
    └── document_builder.py    # 构造 SchemaDocument 和版本指纹

data/
├── demo.sqlite                # 固定演示数据库
└── fixtures/demo.sql          # 可重复生成数据库的 SQL fixture

scripts/init_demo_db.py        # 从 fixture 重建 demo.sqlite
tests/unit/
├── test_security_policy.py    # SQL 安全策略测试
└── test_sqlite_adapter.py     # SQLite 集成行为测试
```

## 3. 演示数据库

演示库采用电商订单模型：

```text
users
├── id
├── name
├── email
└── created_at

products
├── id
├── name
├── category
└── price

orders
├── id
├── user_id -> users.id
├── status
├── total_amount
└── created_at

order_items
├── id
├── order_id -> orders.id
├── product_id -> products.id
├── quantity
└── unit_price
```

数据库内容由 `data/fixtures/demo.sql` 固定，重建命令为：

```bash
python scripts/init_demo_db.py
```

fixture 中包含用户、商品、订单和订单明细数据，可以覆盖基础查询、聚合查询和多表 JOIN。

## 4. 查询执行流程

```text
调用方
  ↓
SQLiteAdapter.execute_readonly(sql, deadline, access_policy, parameters)
  ↓
检查 database_id 和访问策略
  ↓
sqlglot 解析单条 SQL
  ↓
只读、表名、字段名和系统表校验
  ├── 失败：抛出 DatabaseExecutionError(category="unsafe_sql")
  └── 通过
        ↓
创建 SQLite mode=ro 连接
        ↓
注册 progress handler 检查单调时钟 deadline
        ↓
使用参数绑定执行 SQL
        ↓
读取 result_row_limit + 1 行
        ↓
结果截断和敏感字段脱敏
        ↓
返回 QueryResult
        ↓
关闭游标和连接
```

每次查询都使用独立连接。查询超时、中断或出现驱动异常后，连接会被销毁，不会返回连接池继续使用。

## 5. 公共接口

```python
class DatabaseExecutor(Protocol):
    def inspect_schema(self, database_id: str) -> SchemaRetrieval: ...

    def execute_readonly(
        self,
        sql: str,
        deadline: float,
        access_policy: AccessPolicy,
        parameters: Sequence[Any] = (),
    ) -> QueryResult: ...

    def close(self) -> None: ...
```

`deadline` 是 `time.monotonic()` 时间轴上的绝对秒数，不能使用墙上时钟，以避免系统时间调整影响超时判断。

底层异常统一转换为 `DatabaseExecutionError`，只暴露稳定类别和安全消息。原始 SQLite 异常通过异常链保留在进程内部，不进入用户响应、Trace 或持久化状态。

## 6. 访问策略

`AccessPolicy` 由服务端创建，客户端不能提交或覆盖：

```python
AccessPolicy(
    allowed_database_ids=frozenset({"demo"}),
    allowed_tables=frozenset({"users", "products", "orders", "order_items"}),
    allowed_columns={
        "users": frozenset({"id", "name", "email", "created_at"}),
        "products": frozenset({"id", "name", "category", "price"}),
        "orders": frozenset({"id", "user_id", "status", "total_amount", "created_at"}),
        "order_items": frozenset({"id", "order_id", "product_id", "quantity", "unit_price"}),
    },
    masked_columns=frozenset({"users.email"}),
)
```

校验顺序为：

1. 请求的数据库 ID 必须位于 `allowed_database_ids`；
2. SQL 中的每张表必须位于 `allowed_tables`；
3. 显式字段必须位于对应表的 `allowed_columns`；
4. `sqlite_master`、`sqlite_schema` 等系统表始终拒绝；
5. 查询结果中的敏感列按 `masked_columns` 替换为 `***`。

## 7. SQL 安全规则

校验器使用 `sqlglot` SQLite 方言解析 AST，不把关键字黑名单作为唯一安全边界。

允许：

- 单条 `SELECT`；
- 只读的聚合、排序、过滤和 JOIN；
- 使用 `?` 参数占位符的查询。

拒绝：

- `INSERT`、`UPDATE`、`DELETE`；
- `DROP`、`ALTER`、`CREATE`、`TRUNCATE`；
- `PRAGMA`、`ATTACH`、存储过程或控制语句；
- 写入型 CTE、`SELECT INTO`；
- 多条 SQL 拼接；
- `--` 和 `/* ... */` 注释绕过；
- 系统表访问；
- 未授权的表或字段；
- `load_extension`、`readfile`、`writefile`、`eval` 等危险函数。

验证失败返回 `SQLValidationResult(allowed=False, reason=...)`，适配器将其转换为 `unsafe_sql` 类别，不进入数据库执行阶段。

## 8. Schema 读取与版本

`SQLiteAdapter.inspect_schema()` 通过 SQLite 元数据接口读取：

- 表名；
- 字段名、类型和可空性；
- 主键顺序；
- 外键及其目标表和字段。

每张表生成一个 `SchemaDocument`：

```text
TABLE users
COLUMNS id INTEGER NOT NULL, name TEXT NOT NULL, email TEXT NOT NULL, created_at TEXT NOT NULL
PRIMARY KEY id
FOREIGN KEYS none
```

所有文档按稳定顺序拼接后计算 SHA-256，生成 `SchemaRetrieval.schema_version`。

- Schema 未变化时版本保持不变；
- 增加、删除或修改表字段后版本发生变化；
- Graph 后续首次检索后固定该版本，修复循环不得偷偷替换 Schema 上下文。

## 9. 结果格式

查询统一返回 `QueryResult`：

```json
{
  "columns": ["name", "total_amount"],
  "rows": [["Alice", 328.0]],
  "row_count": 1,
  "truncated": false
}
```

结果处理规则：

- 实际读取 `result_row_limit + 1` 行；
- 多读取到一行时设置 `truncated=true`；
- 只返回前 `result_row_limit` 行；
- `row_count` 表示实际返回的行数；
- `users.email` 等敏感字段返回 `***`；
- 不返回原始 SQL、连接字符串、文件路径或底层异常。

## 10. 测试与验收

### SQL 安全测试

- 合法 `SELECT`、JOIN 和聚合查询通过；
- 写入、DDL、`PRAGMA`、`ATTACH` 被拒绝；
- 多语句和注释绕过被拒绝；
- CTE 写入、系统表和危险函数被拒绝；
- 未授权表和字段被拒绝。

### SQLite 行为测试

- Schema 文档包含四张业务表、主键和外键；
- Schema 变化会生成新的版本指纹；
- 查询结果符合统一结构；
- 行数限制和截断标记正确；
- `users.email` 正确脱敏；
- 参数绑定可以按 ID 查询；
- 过期 deadline 立即失败；
- 错误数据库 ID 被拒绝；
- 超时后新查询能够重新建立连接。

运行全部测试：

```bash
python -m pytest -q
```

底层测试依赖 `requirements.txt` 中的 `sqlglot`。安装依赖后，`tests/unit/test_security_policy.py` 和 `tests/unit/test_sqlite_adapter.py` 会执行完整的 AST 和 SQLite 集成测试。

## 11. 后续接入 Graph

下一阶段 Graph 只依赖 `DatabaseExecutor`，不直接访问 `sqlite3`：

```text
retrieve_schema
  → generate_sql
  → validate_sql
  → execute_sql
  → classify_error / repair_sql
  → finalize
```

Graph 节点通过 `inspect_schema()` 获取固定的 `SchemaRetrieval`，通过 `execute_readonly()` 执行已经通过安全策略的 SQL。SQLite 适配器的安全边界和结果契约不因后续接入 LangGraph 而改变。
