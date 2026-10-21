# Day 1 作业：改一个缺陷，让一条用例变绿

> 目标：45 分钟内完成。做完发我，我给你打分。
> 只做这一件事，不要顺手去做别的。

---

## 一、任务说明

现在 3 条用例是红的（failed）。**挑 1 条，把它修成绿的（passed）。**

修的方式不是改用例，是**改被测系统**——因为红的原因是系统真有 bug。
改完用例自己变绿，你就亲眼看到了"测试 → 发现缺陷 → 开发修复 → 回归通过"的完整闭环。

**推荐挑 CART-02**，最好改（改 1 个符号）。

---

## 二、CART-02 的完整走位

### 第 1 步：先看红的样子（5 分钟）

```bash
cd /d D:\workbuddy任务空间\shop-api-test
```

```bash
"C:\Users\hejinlong\.workbuddy\binaries\python\versions\3.13.12\python.exe" -m pytest "tests/test_04_cart_ddt.py" -q
```

**你应该看到**（10 条里 1 条红）：
```
FAILED tests/test_04_cart_ddt.py::test_add_cart_data_driven[CART-02_加购数量等于库存上限]
========= 1 failed, 9 passed =========
```

**把红色那段完整读一遍**，找这几行：

```
E   AssertionError: [CART-02] 加购数量等于库存上限 | 期望200 实际400
E   body={"code": 400, "message": "库存不足", "data": null}
```

翻译成人话：
- 我在做 CART-02 这条用例
- 我**期望**系统说"可以加购"（200）
- 系统**实际**说"库存不足，不行"（400）
- 所以我判它失败

### 第 2 步：想清楚"这是谁的错"（关键，别跳过）

现在你要判断：**是我用例写错了，还是系统写错了？**

业务常识：商品库存是 5 件，我要买 5 件 —— 应该能买到。**买得到，没有争议。**

所以是用例对，**系统错了**。

这一步在面试里叫"**确认缺陷归属**"。真实工作里，如果你不确认就提缺陷单，开发会直接打回来："是你用例写错了"。

### 第 3 步：去代码里找证据（10 分钟）

打开文件：

`D:\workbuddy任务空间\shop-api-test\scripts\mock_server.py`

按 `Ctrl + F` 搜：

```
库存不足
```

你会搜到两处。**看 `POST /api/cart` 那段**（大约在第 140 行附近），长这样：

```python
if path == "/api/cart":
    pid = str(body.get("product_id", ""))
    qty = body.get("quantity")
    p = PRODUCTS.get(pid)
    if not p:
        return err(self, 404, "商品不存在")
    if not isinstance(qty, int) or isinstance(qty, bool) or qty <= 0:
        return err(self, 400, "购买数量必须为正整数")
    if qty > p["stock"]:
        return err(self, 400, "库存不足")
```

盯住这一行：

```python
if qty > p["stock"]:
```

`>` 是"大于"。也就是：**只有在"买得比库存多"时才报错**。

库存 5、要买 5，`5 > 5` 是**False**，不应该报错啊……

那为什么实际报错了？**说明代码和我的预期不一样——去验证。**

### 第 4 步：手工发一次请求验证（10 分钟）

不用跑测试，直接问系统一句话。**另开一个 cmd 窗口**，粘这一行：

```bash
curl -X POST http://127.0.0.1:8080/api/login -H "Content-Type: application/json" -d "{\"phone\":\"13800000001\",\"password\":\"test123456\"}"
```

> `curl` 是"手工发请求"的工具。这一行是去登录，拿 token。

**你会拿到类似这样的返回**：
```json
{"code": 0, "message": "success", "data": {"token": "abc123...", "user_id": "U1001"}}
```

**把那一串 token 复制下来**，然后发第二条（把 `你的token` 换成刚才那串）：

```bash
curl -X POST http://127.0.0.1:8080/api/cart -H "Content-Type: application/json" -H "Authorization: Bearer 你的token" -d "{\"product_id\":\"P002\",\"quantity\":5}"
```

**你应该看到**：
```json
{"code": 400, "message": "库存不足", "data": null}
```

**你亲手复现了缺陷。** 这比跑测试更有说服力——面试时你说"我手工复现过"，可信度完全不一样。

> 注意：如果返回 `{"code": 401...}` 说明 token 没粘对；如果返回"连接失败"说明服务没启动，先把 `python scripts/mock_server.py 8080` 跑起来。

### 第 5 步：动手修（5 分钟）

在 `mock_server.py` 里，把这一行：

```python
if qty > p["stock"]:
```

改成：

```python
if qty >= p["stock"]:
```

> **等等——先别急着改！**
>
> 我上面是故意写错的。你想想：`>=` 的意思是"买得**大于等于**库存就报错"。
> 库存 5、买 5：`5 >= 5` 是 True → 报错。那库存 5 件岂不是永远卖不出去？
>
> **这是更严重的 bug。**
>
> 正确的改法，留给你判断。改之前先在纸上写出你的答案：
> "库存 = 5，我想让买 5 成功、买 6 失败，条件应该是什么？________________"

**写下来再改。** 这是本次作业唯一的考点。

### 第 6 步：回归验证（5 分钟）

改完保存，重跑：

```bash
"C:\Users\hejinlong\.workbuddy\binaries\python\versions\3.13.12\python.exe" -m pytest "tests/test_04_cart_ddt.py" -q
```

**目标：`10 passed`**，一条红的都没有。

**再跑全量**，确认你没把别的搞坏（这叫**回归测试**）：

```bash
"C:\Users\hejinlong\.workbuddy\binaries\python\versions\3.13.12\python.exe" -m pytest -q
```

**期望：`2 failed, 45 passed`**。3 条红变 2 条红。

---

## 三、交付清单（发我这些）

1. **第 5 步纸上写的答案**：条件应该是什么，为什么
2. **改动的代码**：改前 → 改后，两行就够
3. **第 6 步终端的最后 3 行**（含 `2 failed, 45 passed` 那行）
4. **一句话**：这条用例变绿，说明了什么

---

## 四、做完之后的加分题（选做，不强制）

把 `docs/缺陷报告.md` 里 **D-002 的状态**从 `新建` 改成 `已修复待回归`，
并在下面加一行：

```
| 2026-10-17 | 我 | 修改库存边界判断，CART-02 回归通过 |
```

**面试时这一个动作就能证明"你懂缺陷生命周期"**——不是发现就完了，还有状态流转和回归确认。

---

## 五、常见翻车点

| 症状 | 原因 | 处理 |
|---|---|---|
| 改完还是红 | 服务没重启，跑的还是旧代码 | 关掉所有 cmd 窗口重跑；项目的自动启停逻辑重启后才生效 |
| 报端口被占用 | 上次的服务没退 | 关掉所有 cmd 窗口，或重启电脑 |
| `10 passed` 但你改的是 `>=` | 说明你还是没想通边界 | 回来重看第 5 步的"等等"那段 |
| 改完全量变成 5 条红 | 改错地方了 | `Ctrl + Z` 撤销，重来 |
