# -*- coding: utf-8 -*-
"""被测系统的业务接口层（Page Object 的接口版）。

设计意图：用例里不出现 URL 字符串，只出现动作名。
接口地址一旦变更，只改这一个文件，几十条用例零改动。
"""
from __future__ import annotations

from common.http_client import ApiClient


class ShopApi:
    def __init__(self, client: ApiClient):
        self.c = client

    # --- 登录 ---
    def login(self, phone: str, password: str):
        return self.c.post("/api/login", json={"phone": phone, "password": password})

    # --- 商品 ---
    def list_products(self, page: int = 1, size: int = 20):
        return self.c.get("/api/products", params={"page": page, "size": size})

    def get_product(self, product_id: str):
        return self.c.get(f"/api/products/{product_id}")

    # --- 购物车 ---
    def add_cart(self, product_id: str, quantity: int):
        return self.c.post(
            "/api/cart", json={"product_id": product_id, "quantity": quantity}
        )

    # --- 订单 ---
    def create_order(self, items: list):
        return self.c.post("/api/order", json={"items": items})

    def pay(self, order_id: str):
        return self.c.post(f"/api/order/{order_id}/pay")

    def get_order(self, order_id: str):
        return self.c.get(f"/api/order/{order_id}")
