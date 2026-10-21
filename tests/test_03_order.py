# -*- coding: utf-8 -*-
"""下单主流程用例 —— 状态机、幂等、越权、金额计算。"""
import pytest

from common.assert_util import assert_code, assert_msg_contains, assert_status

pytestmark = pytest.mark.order


class TestOrderFlow:
    def test_create_order_success(self, user_a):
        """ORDER-01 正向：单品下单成功，返回 order_id 与金额"""
        resp = user_a.create_order([{"product_id": "P001", "quantity": 3}])
        assert_status(resp, 200)
        assert_code(resp, 0)
        data = resp.json()["data"]
        assert data["order_id"].startswith("O")
        assert data["status"] == "CREATED"
        # P001 单价 0.01 * 3 = 0.03，小数不能变成 0.030000000000000002
        assert data["amount"] == 0.03, f"金额计算错误，实际={data['amount']}"

    def test_create_order_multi_items(self, user_a):
        """ORDER-02 正向：多商品下单，金额累加正确"""
        resp = user_a.create_order(
            [{"product_id": "P001", "quantity": 2}, {"product_id": "P002", "quantity": 1}]
        )
        assert_code(resp, 0)
        assert resp.json()["data"]["amount"] == 1299.02, resp.text

    def test_pay_then_query(self, user_a, order_flow):
        """ORDER-03 状态流转：CREATED -> PAID，查询结果一致"""
        order_id, _ = order_flow
        pay_resp = user_a.pay(order_id)
        assert_code(pay_resp, 0)
        assert pay_resp.json()["data"]["status"] == "PAID"

        query = user_a.get_order(order_id)
        assert query.json()["data"]["status"] == "PAID", "支付后查询状态未更新，状态机不一致"

    def test_pay_twice_should_conflict(self, user_a, order_flow):
        """ORDER-04 幂等：重复支付应返回 409 或标识幂等（缺陷 D-005 验证点）"""
        order_id, _ = order_flow
        user_a.pay(order_id)
        second = user_a.pay(order_id)
        assert second.status_code == 409 or second.json()["data"].get("idempotent") is True, (
            f"重复支付被静默接受，实际={second.status_code} {second.text[:200]}；"
            "线上风险：用户连点两次支付按钮，可能重复扣款，前端也无法提示'已支付'"
        )

    def test_query_other_users_order(self, user_b, order_flow):
        """ORDER-05 越权：B 用户查 A 的订单必须失败"""
        order_id, _ = order_flow
        resp = user_b.get_order(order_id)
        assert resp.status_code == 404, f"存在水平越权，B 查到了 A 的订单：{resp.text[:200]}"

    def test_pay_other_users_order(self, user_b, order_flow):
        """ORDER-06 越权：B 用户支付 A 的订单必须失败"""
        order_id, _ = order_flow
        resp = user_b.pay(order_id)
        assert resp.status_code == 404, f"存在越权支付风险：{resp.text[:200]}"

    def test_create_order_out_of_stock(self, user_a):
        """ORDER-07 反向：库存为0的商品下单失败，且提示明确"""
        resp = user_a.create_order([{"product_id": "P003", "quantity": 1}])
        assert resp.status_code == 400
        assert_msg_contains(resp, "库存")

    def test_create_order_quantity_over_stock(self, user_a):
        """ORDER-08 边界：购买量=库存+1 失败；=库存 成功（边界两侧都测）"""
        p = user_a.get_product("P002").json()["data"]
        stock = p["stock"]
        bad = user_a.create_order([{"product_id": "P002", "quantity": stock + 1}])
        assert bad.status_code == 400, f"超库存未拦截：{bad.text[:150]}"
        good = user_a.create_order([{"product_id": "P002", "quantity": stock}])
        assert_code(good, 0)

    def test_create_order_negative_quantity(self, user_a):
        """ORDER-09 反向：负数数量应拦截（否则会变成加库存/负金额）"""
        resp = user_a.create_order([{"product_id": "P001", "quantity": -5}])
        assert resp.status_code == 400, (
            f"负数数量未拦截，可能被用来'加库存'或刷负金额订单：{resp.text[:200]}"
        )

    def test_create_order_empty_items(self, user_a):
        """ORDER-10 反向：空商品列表应拦截"""
        resp = user_a.create_order([])
        assert resp.status_code == 400

    def test_create_order_not_exist_product(self, user_a):
        """ORDER-11 反向：下单不存在的商品应 404"""
        resp = user_a.create_order([{"product_id": "NOT_EXIST", "quantity": 1}])
        assert resp.status_code == 404
