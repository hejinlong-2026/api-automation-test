# MiniShop 电商接口自动化测试项目

基于 pytest 的接口自动化测试框架，覆盖**登录 → 商品 → 购物车 → 下单 → 支付 → 查询**完整交易链路。

- 43 条用例，自动化覆盖 100%
- 发现 3 个真实缺陷（含 1 个资损级：重复支付无幂等）
- 支持数据驱动、JSON Schema 校验、性能基线断言、HTML 报告

## 一、技术栈

| 层面 | 选型 | 用途 |
|---|---|---|
| 测试框架 | pytest 9 | 用例组织、夹具、参数化、标记 |
| 请求层 | requests | HTTP 调用 |
| 数据驱动 | YAML | 用例数据与代码分离 |
| 结构校验 | jsonschema | 响应字段类型/必填校验 |
| 报告 | pytest-html | 可归档的 HTML 报告 |
| UI | Selenium 4 | 登录页冒烟 |
| 被测服务 | Python 标准库 http.server | 自带 mock 服务，零依赖启动 |

## 二、目录结构

```
shop-api-test/
├── api/                    # 业务接口层（Page Object 的接口版）
│   └── shop_api.py         # 只在这里出现 URL
├── common/
│   ├── http_client.py      # 请求封装：日志/耗时/会话
│   ├── assert_util.py      # 断言封装：失败信息可直接进缺陷单
│   └── bootstrap.py        # 被测服务自动拉起
├── config/setting.py       # 环境配置、账号、性能基线
├── data/cart_cases.yaml    # 数据驱动用例集
├── tests/
│   ├── conftest.py         # 夹具：token、登录态、下单
│   ├── test_01_login.py    # 13 条
│   ├── test_02_product.py  # 9 条
│   ├── test_03_order.py    # 11 条
│   ├── test_04_cart_ddt.py # 10 条（yaml 驱动）
│   └── test_05_ui_login.py # 3 条（Selenium）
├── scripts/mock_server.py  # 被测服务（内置 3 个缺陷）
├── docs/                   # 用例清单 / 缺陷报告 / 测试总结
└── reports/                # HTML 报告输出
```

## 三、快速开始

```bash
pip install -r requirements.txt

# 直接跑（夹具会自动拉起被测服务）
pytest tests/test_01_login.py tests/test_02_product.py tests/test_03_order.py tests/test_04_cart_ddt.py -v

# 生成 HTML 报告
pytest --html=reports/report.html --self-contained-html

# 只跑订单模块
pytest -m order -v

# 单独启动被测服务（调试接口用）
python scripts/mock_server.py 8080
```

预期结果：**39 passed, 3 failed**。3 条失败对应 3 个真实缺陷，详见 `docs/缺陷报告.md`。

## 四、框架设计要点

### 1. 分层：用例不碰 URL

```python
# 差：URL 散落在几十个用例里，接口一改全崩
resp = requests.get("http://127.0.0.1:8080/api/products/P001")

# 好：用例只描述业务动作
resp = user_a.get_product("P001")
```

### 2. 断言带上下文

```python
# 差：失败只有 AssertionError
assert resp.status_code == 404

# 好：失败直接可提缺陷
assert_status(resp, 404)
# -> 状态码不符 | 期望=404 实际=200 | body={"code":0,"data":null}
```

### 3. 数据驱动

新增购物车场景只改 `data/cart_cases.yaml`，不动代码：

```yaml
- id: CART-03
  desc: 加购数量超库存
  product_id: P002
  quantity: 6
  expect_status: 400
```

### 4. 数据隔离

- `token_a` 为 session 级：整个会话只登录一次，省时间
- `order_flow` 为 function 级：每个用例独立订单，互不影响
- 需要“无 token”场景时**新建独立 client**，不复用被污染的 session

### 5. 测试环境自管理

`bootstrap_server` 夹具负责起停被测服务；CI 上不需要人工预启动，
也不会因为“服务没开”产生一堆假失败。

## 五、覆盖的业务场景

| 类别 | 场景 |
|---|---|
| 正向 | 登录、商品详情/列表、加购、下单、支付、订单查询 |
| 异常 | 密码错误、未注册、商品不存在、库存不足、订单不存在 |
| 边界值 | 手机号 10/11/12 位、密码 129 位、分页 size 0/100/101、page 0/-1、数量 0/-1/库存/库存+1 |
| 安全 | 无 token、伪造 token、水平越权（A 单 B 查/B 支付） |
| 状态机 | CREATED → PAID、重复支付幂等 |
| 数据正确性 | 金额精度 0.01×3=0.03、多品累加、重复加购累加 |
| 性能基线 | 商品列表 < 500ms |

## 六、发现的缺陷

| 编号 | 标题 | 严重度 |
|---|---|---|
| D-001 | 不存在商品返回 200 + null 而非 404 | S3 |
| D-002 | 购买量等于库存时误判库存不足（`>` 写成 `>=`） | S2 |
| D-003 | 重复支付静默返回成功，无幂等控制 | **S1（资损）** |

## 七、后续计划

- [ ] 接入 Allure 报告，按模块/严重度分组展示
- [ ] 增加数据库断言（库存、订单状态落库一致性）
- [ ] 用 locust 做并发抢购，验证超卖
- [ ] 接入 GitHub Actions，push 触发回归
- [ ] 配置分离 staging 环境，支持一键切换
