# -*- coding: utf-8 -*-
"""数据驱动用例：用例数据与代码分离，新增场景只改 yaml。

面试点：为什么数据驱动重要？
 运营规则一改（如分页上限从 100 变 50），只需改 yaml，不用改代码、不用重新 review 逻辑。
"""
import pytest
import yaml

from common.assert_util import assert_code, assert_status

with open("data/cart_cases.yaml", encoding="utf-8") as f:
    CASES = yaml.safe_load(f)["cases"]


def _ids():
    return [c["id"] + "_" + c["desc"] for c in CASES]


@pytest.mark.cart
@pytest.mark.parametrize("case", CASES, ids=_ids())
def test_add_cart_data_driven(user_a, case):
    resp = user_a.add_cart(case["product_id"], case["quantity"])
    assert resp.status_code == case["expect_status"], (
        f"[{case['id']}] {case['desc']} | 期望{case['expect_status']} 实际{resp.status_code} "
        f"| body={resp.text[:200]}"
    )
    if case.get("expect_msg"):
        assert case["expect_msg"] in str(resp.json().get("message", "")), resp.text


@pytest.mark.cart
def test_add_cart_twice_accumulate(user_a):
    """CART-06 业务规则：同一商品重复加购，数量应累加而非覆盖"""
    user_a.add_cart("P001", 2)
    resp = user_a.add_cart("P001", 3)
    assert_code(resp, 0)
    assert resp.json()["data"]["quantity"] >= 5, (
        f"重复加购未累加，实际={resp.json()['data']['quantity']}"
    )
