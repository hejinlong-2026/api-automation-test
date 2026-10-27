# -*- coding: utf-8 -*-
"""极简电商后端 —— 只用于接口测试练习，故意保留若干真实缺陷。

只用标准库实现，无需安装任何第三方包。
启动：python scripts/mock_server.py  （默认 8080 端口）
"""
from __future__ import annotations

import json
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

_lock = threading.Lock()

USERS = {
    "13800000001": {"password": "test123456", "nickname": "张三", "user_id": "U1001"},
    "13800000002": {"password": "test123456", "nickname": "李四", "user_id": "U1002"},
}
TOKENS: dict[str, str] = {}
PRODUCTS = {
    "P001": {"product_id": "P001", "name": "机械键盘", "price": 0.01, "stock": 100},
    "P002": {"product_id": "P002", "name": "显示器", "price": 1299.0, "stock": 5},
    "P003": {"product_id": "P003", "name": "鼠标垫", "price": 19.9, "stock": 0},
}
CARTS: dict[str, dict[str, int]] = {}
ORDERS: dict[str, dict] = {}
# 记录初始库存，供 /api/__reset 恢复（测试数据隔离用）
INITIAL_STOCK = {pid: p["stock"] for pid, p in PRODUCTS.items()}


def reply(handler, code: int, payload: dict):
    raw = json.dumps(payload, ensure_ascii=False).encode()
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(raw)))
    handler.end_headers()
    handler.wfile.write(raw)


def ok(handler, data=None, code=0, msg="success"):
    reply(handler, 200, {"code": code, "message": msg, "data": data})


def err(handler, code: int, msg: str):
    reply(handler, code, {"code": code, "message": msg, "data": None})


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):  # 静音
        pass

    # ---------- 工具 ----------
    def _body(self) -> dict:
        n = int(self.headers.get("Content-Length") or 0)
        if not n:
            return {}
        try:
            return json.loads(self.rfile.read(n) or b"{}")
        except json.JSONDecodeError:
            return {}

    def _phone(self):
        auth = self.headers.get("Authorization") or ""
        if not auth.startswith("Bearer "):
            return None
        return TOKENS.get(auth[7:])

    def _path(self):
        u = urlparse(self.path)
        return u.path.rstrip("/") or "/", parse_qs(u.query)

    # ---------- 路由 ----------
    def do_GET(self):
        path, q = self._path()
        if path == "/health":
            return ok(self, {"status": "UP"})

        if path == "/api/products":
            try:
                page = int(q.get("page", ["1"])[0])
                size = int(q.get("size", ["20"])[0])
            except ValueError:
                return err(self, 422, "分页参数必须为整数")
            if page < 1:
                return err(self, 422, "page 必须 >= 1")
            if size < 1 or size > 100:
                return err(self, 422, "size 取值 1~100")
            items = list(PRODUCTS.values())
            start = (page - 1) * size
            return ok(self, {"total": len(items), "page": page, "size": size,
                             "items": items[start:start + size]})

        if path.startswith("/api/products/"):
            pid = path.split("/")[-1]
            p = PRODUCTS.get(pid)
            if not p:
                # D-001 已修复：资源不存在统一返回 404
                return err(self, 404, "商品不存在")
            return ok(self, p)

        if not self._phone():
            return err(self, 401, "未登录或 token 无效")

        if path.startswith("/api/order/"):
            oid = path.split("/")[-1]
            o = ORDERS.get(oid)
            if not o or o["owner"] != self._phone():
                return err(self, 404, "订单不存在")
            return ok(self, {"order_id": o["order_id"], "status": o["status"],
                             "amount": o["amount"], "items": o["items"]})

        return err(self, 404, "接口不存在")

    def do_POST(self):
        path, _ = self._path()
        body = self._body()

        if path == "/api/__reset":
            """测试专用：恢复库存、清空订单和购物车（保留 token，避免登录夹具失效）。

            存在的意义：用例之间不能共享被消耗的数据（如库存），
            否则用例执行顺序一变，结果就变 —— 这叫"用例隔离"。
            """
            with _lock:
                for pid, n in INITIAL_STOCK.items():
                    PRODUCTS[pid]["stock"] = n
                CARTS.clear()
                ORDERS.clear()
            return ok(self, {"reset": True})

        if path == "/api/login":
            phone = str(body.get("phone", ""))
            pwd = str(body.get("password", ""))
            u = USERS.get(phone)
            if not u or u["password"] != pwd:
                return err(self, 401, "手机号或密码错误")
            token = uuid.uuid4().hex
            TOKENS[token] = phone
            return ok(self, {"token": token, "user_id": u["user_id"], "nickname": u["nickname"]})

        phone = self._phone()
        if not phone:
            return err(self, 401, "未登录或 token 无效")

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
            with _lock:
                cart = CARTS.setdefault(phone, {})
                cart[pid] = cart.get(pid, 0) + qty
                cur = cart[pid]
            return ok(self, {"product_id": pid, "quantity": cur})

        if path == "/api/order":
            items = body.get("items")
            if not items:
                return err(self, 400, "订单不能为空")
            total = 0.0
            with _lock:
                for it in items:
                    p = PRODUCTS.get(it.get("product_id"))
                    qty = it.get("quantity")
                    if not p:
                        return err(self, 404, f"商品 {it.get('product_id')} 不存在")
                    if not isinstance(qty, int) or isinstance(qty, bool) or qty <= 0:
                        return err(self, 400, "购买数量必须为正整数")
                    if p["stock"] < qty:
                        return err(self, 400, f"商品 {p['name']} 库存不足")
                    total += p["price"] * qty
                for it in items:
                    PRODUCTS[it["product_id"]]["stock"] -= it["quantity"]

            oid = "O" + uuid.uuid4().hex[:12].upper()
            ORDERS[oid] = {"order_id": oid, "owner": phone, "status": "CREATED",
                           "items": items, "amount": round(total, 2), "paid": False}
            return ok(self, {"order_id": oid, "amount": round(total, 2), "status": "CREATED"})

        if path.startswith("/api/order/") and path.endswith("/pay"):
            oid = path.split("/")[-2]
            o = ORDERS.get(oid)
            if not o or o["owner"] != phone:
                return err(self, 404, "订单不存在")
            if o["status"] == "PAID":
                # D-003 幂等校验：已支付订单再次支付返回 409，避免重复扣款
                return err(self, 409, "订单已支付，请勿重复支付")
            o["status"] = "PAID"
            o["paid"] = True
            return ok(self, {"order_id": oid, "status": "PAID"})

        return err(self, 404, "接口不存在")


def main(port: int = 8080):
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    srv.daemon_threads = True
    print(f"MiniShop API 已启动 -> http://127.0.0.1:{port}")
    srv.serve_forever()


if __name__ == "__main__":
    import sys

    main(int(sys.argv[1]) if len(sys.argv) > 1 else 8080)
