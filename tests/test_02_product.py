# -*- coding: utf-8 -*-
"""商品查询接口用例 —— 正常业务 + 异常资源 + 结构校验 + 性能基线。"""
import pytest

from common.assert_util import assert_code, assert_elapsed, assert_schema, assert_status
from config.setting import CONF

PRODUCT_SCHEMA = {
    "type": "object",
    "required": ["product_id", "name", "price", "stock"],
    "properties": {
        "product_id": {"type": "string"},
        "name": {"type": "string", "minLength": 1},
        "price": {"type": "number", "minimum": 0},
        "stock": {"type": "integer", "minimum": 0},
    },
}

LIST_SCHEMA = {
    "type": "object",
    "required": ["total", "page", "size", "items"],
    "properties": {
        "total": {"type": "integer", "minimum": 0},
        "page": {"type": "integer", "minimum": 1},
        "size": {"type": "integer", "minimum": 1},
        "items": {"type": "array"},
    },
}

pytestmark = pytest.mark.product


class TestProduct:
    def test_detail_success(self, user_a):
        """PROD-01 正向：查询存在商品，字段完整且价格精度正确"""
        resp = user_a.get_product("P002")
        assert_status(resp, 200)
        assert_code(resp, 0)
        data = resp.json()["data"]
        assert_schema(data, PRODUCT_SCHEMA)
        assert data["price"] == 1299.00
        # 价格精度：接口直接返回 1299 而不是 1299.0 时，前端会显示成 1299 元丢两位小数
        assert isinstance(data["price"], float), "价格应为浮点，避免前端精度展示问题"

    def test_detail_not_found_returns_404(self, user_a):
        """PROD-02 反向：不存在的商品应返回 404（D-001 回归点）"""
        resp = user_a.get_product("NOT_EXIST_999")
        assert resp.status_code == 404, (
            f"期望 404 实际 {resp.status_code}，响应体={resp.text[:200]}；"
            "不存在资源返回 200+null 违反 REST 语义，前端无法区分'查到了空值'与'不存在'"
        )

    def test_list_default_page(self, user_a):
        """PROD-03 正向：默认分页返回结构正确"""
        resp = user_a.list_products()
        assert_status(resp, 200)
        data = resp.json()["data"]
        assert_schema(data, LIST_SCHEMA)
        assert data["page"] == 1
        assert len(data["items"]) <= data["size"]

    @pytest.mark.parametrize(
        "page,size,desc",
        [(1, 100, "size上边界100合法"), (1, 101, "size=101超上限应拦截"),
         (0, 20, "page=0非法"), (-1, 20, "page=-1非法"), (1, 0, "size=0非法")],
    )
    def test_list_page_boundary(self, user_a, page, size, desc):
        """PROD-04~08 分页边界值：page>=1, 1<=size<=100"""
        resp = user_a.list_products(page=page, size=size)
        if size <= 100 and page >= 1 and size >= 1:
            assert resp.status_code == 200, f"[{desc}] 合法参数被拒"
        else:
            assert resp.status_code in (400, 422), (
                f"[{desc}] 非法分页参数未被拦截，实际{resp.status_code}"
            )

    def test_list_performance_sla(self, user_a):
        """PROD-09 性能：商品列表响应需 < 500ms"""
        user_a.list_products()
        assert_elapsed(user_a.c, CONF.SLA_LIST_MS, "GET /api/products")
