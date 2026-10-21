# -*- coding: utf-8 -*-
"""HTTP 客户端封装：日志、耗时统计、统一异常。

面试点：为什么不让用例直接 requests.get？
 1) 失败时能直接看到请求/响应体，而不是只有一行 assert
 2) 耗时统一记录，性能断言才有数据来源
 3) base_url / 超时 / header 集中管理，换环境只改一处
"""
from __future__ import annotations

import logging
import time

import requests

from config.setting import CONF

log = logging.getLogger("shop.api")


class ApiClient:
    def __init__(self, base_url: str = None, token: str = None):
        self.base_url = (base_url or CONF.BASE_URL).rstrip("/")
        self.timeout = CONF.TIMEOUT
        self.session = requests.Session()
        # 本机被测服务不走系统代理，否则会 502
        self.session.trust_env = False
        self.last_elapsed_ms: float = 0.0
        if token:
            self.set_token(token)

    def set_token(self, token: str) -> None:
        self.session.headers.update({"Authorization": f"Bearer {token}"})

    def request(self, method: str, path: str, **kwargs) -> requests.Response:
        url = f"{self.base_url}{path}"
        kwargs.setdefault("timeout", self.timeout)
        begin = time.perf_counter()
        try:
            resp = self.session.request(method.upper(), url, **kwargs)
        except requests.RequestException as e:
            elapsed = (time.perf_counter() - begin) * 1000
            log.error("[%s %s] 请求异常 %.0fms: %s", method, url, elapsed, e)
            raise
        self.last_elapsed_ms = (time.perf_counter() - begin) * 1000
        log.info(
            "[%s %s] -> %s %.0fms\n  req=%s\n  resp=%s",
            method.upper(),
            url,
            resp.status_code,
            self.last_elapsed_ms,
            kwargs.get("json") or kwargs.get("params") or "-",
            resp.text[:500],
        )
        return resp

    # ---- 语义化快捷方法 ----
    def get(self, path, **kw):
        return self.request("GET", path, **kw)

    def post(self, path, **kw):
        return self.request("POST", path, **kw)

    def put(self, path, **kw):
        return self.request("PUT", path, **kw)

    def delete(self, path, **kw):
        return self.request("DELETE", path, **kw)
