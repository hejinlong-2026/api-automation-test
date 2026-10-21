# -*- coding: utf-8 -*-
"""pytest 全局夹具。

面试点：用例之间不能有数据依赖。
登录态用 session 级夹具复用（省时间），业务数据用 function 级夹具（保隔离）。
"""
from __future__ import annotations

import logging

import pytest

from api.shop_api import ShopApi
from common.bootstrap import start_server
from common.http_client import ApiClient
from config.setting import CONF

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
)


def pytest_addoption(parser):
    parser.addoption(
        "--env", action="store", default="local", help="运行环境：local/staging"
    )


@pytest.fixture(scope="session", autouse=True)
def bootstrap_server():
    """会话开始时确保被测服务可用，结束后回收进程。

    面试点：这就是"测试环境管理"。CI 上不能要求人工先启服务，
    否则流水线必然挂在一个和代码无关的原因上。
    """
    proc = start_server()
    yield
    if proc:
        proc.terminate()
        logging.info("被测服务已停止 pid=%s", proc.pid)


@pytest.fixture(autouse=True)
def reset_state_per_test():
    """每条用例跑之前，把被测服务的数据恢复到初始状态。

    面试点：用例隔离。没有它，"前面用例买光了库存"会让后面的用例
    因为执行顺序不同而结果不同 —— 这是自动化最隐蔽的坑。
    """
    client = ApiClient()
    client.post("/api/__reset")
    yield


@pytest.fixture(scope="session")
def anon_client():
    """未登录客户端，用于鉴权类反例。"""
    return ApiClient()


@pytest.fixture(scope="session")
def token_a(anon_client):
    """用户A 的 token，整个会话只登录一次。"""
    api = ShopApi(anon_client)
    resp = api.login(**CONF.USER_A)
    assert resp.status_code == 200, f"登录失败，检查被测服务是否启动: {resp.text}"
    data = resp.json()["data"]
    assert data["token"], "登录成功但未返回 token"
    logging.info("用户A 登录成功 user_id=%s", data["user_id"])
    return data["token"]


@pytest.fixture(scope="session")
def token_b(anon_client):
    api = ShopApi(anon_client)
    data = api.login(**CONF.USER_B).json()["data"]
    return data["token"]


@pytest.fixture()
def user_a(token_a):
    """已登录的 ShopApi 实例（用户A）。"""
    client = ApiClient(token=token_a)
    return ShopApi(client)


@pytest.fixture()
def user_b(token_b):
    """已登录的 ShopApi 实例（用户B）—— 越权测试用。"""
    client = ApiClient(token=token_b)
    return ShopApi(client)


@pytest.fixture()
def order_flow(user_a):
    """下单夹具：返回 (order_id, 下单响应)，供支付/查询用例复用。"""
    resp = user_a.create_order([{"product_id": "P001", "quantity": 2}])
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["code"] == 0, f"下单失败: {body}"
    return body["data"]["order_id"], body
