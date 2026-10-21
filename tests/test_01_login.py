# -*- coding: utf-8 -*-
"""登录接口用例 —— 等价类 + 边界值 + 鉴权。

用例设计说明见 docs/测试用例清单.md 的 LOGIN-xx 编号。
"""
import pytest

from common.assert_util import assert_code, assert_field, assert_json_key

pytestmark = pytest.mark.login


class TestLogin:
    def test_login_success(self, anon_client):
        """LOGIN-01 正向：正确手机号+密码，返回 token"""
        from api.shop_api import ShopApi

        resp = ShopApi(anon_client).login("13800000001", "test123456")
        assert resp.status_code == 200
        assert_code(resp, 0)
        body = resp.json()["data"]
        assert body["token"], "token 不应为空"
        assert len(body["token"]) == 32, f"token 应为32位，实际={len(body['token'])}"

    def test_login_wrong_password(self, anon_client):
        """LOGIN-02 反向：密码错误 -> 401 + 明确提示"""
        from api.shop_api import ShopApi

        resp = ShopApi(anon_client).login("13800000001", "wrong_pwd")
        assert resp.status_code == 401
        assert "密码" in resp.json()["message"]

    def test_login_unknown_phone(self, anon_client):
        """LOGIN-03 反向：未注册手机号 -> 401

        安全设计点：不能提示"该手机号未注册"，否则可被用来枚举用户。
        """
        from api.shop_api import ShopApi

        resp = ShopApi(anon_client).login("13900000000", "test123456")
        assert resp.status_code == 401
        msg = resp.json()["message"]
        assert "未注册" not in msg, f"存在用户枚举风险：{msg}"
        assert "密码" in msg or "账号" in msg

    @pytest.mark.parametrize(
        "phone,pwd,desc",
        [
            ("", "test123456", "手机号为空"),
            ("13800000001", "", "密码为空"),
            ("1380000000", "test123456", "手机号10位（下边界外）"),
            ("138000000011", "test123456", "手机号12位（上边界外）"),
            ("1380000000a", "test123456", "手机号含字母"),
            ("13800000001", "t" * 129, "密码超长129位"),
            (" 13800000001", "test123456", "手机号前导空格"),
        ],
    )
    def test_login_invalid_params(self, anon_client, phone, pwd, desc):
        """LOGIN-04~10 参数异常：必须拦截，不能 500"""
        from api.shop_api import ShopApi

        resp = ShopApi(anon_client).login(phone, pwd)
        assert resp.status_code != 500, f"[{desc}] 服务端500，参数校验缺失"
        assert resp.status_code in (400, 401, 422), f"[{desc}] 期望4xx，实际{resp.status_code}"

    def test_token_reusable(self, anon_client, token_a):
        """LOGIN-11 逻辑：同一 token 可多次调用业务接口"""
        from api.shop_api import ShopApi

        client = anon_client
        client.set_token(token_a)
        api = ShopApi(client)
        r1 = api.list_products()
        r2 = api.list_products()
        assert r1.status_code == r2.status_code == 200

    def test_request_without_token(self):
        """LOGIN-12 鉴权：未带 token 访问购物车 -> 401"""
        from api.shop_api import ShopApi
        from common.http_client import ApiClient

        # 必须新建独立 client：session 级夹具的 header 会被前面用例污染，
        # 这类"用例间状态泄漏"是自动化最常见也最难查的坑
        clean = ApiClient()
        resp = ShopApi(clean).add_cart("P001", 1)
        assert resp.status_code == 401, f"未登录竟可加购，实际={resp.text[:150]}"

    def test_request_with_forged_token(self):
        """LOGIN-13 鉴权：伪造 token -> 401"""
        from api.shop_api import ShopApi
        from common.http_client import ApiClient

        clean = ApiClient()
        clean.set_token("deadbeef" * 4)
        resp = ShopApi(clean).add_cart("P001", 1)
        assert resp.status_code == 401, f"伪造 token 竟通过鉴权：{resp.text[:150]}"
