# -*- coding: utf-8 -*-
"""断言封装。目的：失败信息能直接贴进缺陷单，而不是 "AssertionError"。

对比：
  assert r.status_code == 200
  -> AssertionError

  assert_code(r, 200)
  -> 状态码不符 | 期望=200 实际=500 | body={"code":500,"message":"库存不足"}
"""
from __future__ import annotations

import json


def _brief(resp) -> str:
    try:
        return json.dumps(resp.json(), ensure_ascii=False)[:300]
    except Exception:
        return (resp.text or "")[:300]


def assert_status(resp, expected: int):
    assert resp.status_code == expected, (
        f"HTTP 状态码不符 | 期望={expected} 实际={resp.status_code} | body={_brief(resp)}"
    )


def assert_code(resp, expected: int):
    """业务码断言。企业接口普遍用 body.code 表达业务结果，HTTP 恒为 200。"""
    body = resp.json()
    assert body.get("code") == expected, (
        f"业务码不符 | 期望={expected} 实际={body.get('code')} "
        f"msg={body.get('message')} | body={_brief(resp)}"
    )


def assert_msg_contains(resp, keyword: str):
    msg = str(resp.json().get("message", ""))
    assert keyword in msg, f"错误提示不符 | 期望包含'{keyword}' 实际='{msg}'"


def assert_json_key(resp, key: str):
    body = resp.json()
    assert key in body, f"响应缺少字段 {key} | 实际字段={list(body.keys())}"


def assert_field(resp, key: str, expected):
    body = resp.json()
    data = body.get("data", body)
    actual = data.get(key) if isinstance(data, dict) else None
    assert actual == expected, f"字段 {key} 不符 | 期望={expected!r} 实际={actual!r}"


def assert_schema(instance, schema: dict):
    """用 jsonschema 校验结构，比逐字段 assert 更能发现字段缺失/类型漂移。"""
    import jsonschema

    try:
        jsonschema.validate(instance=instance, schema=schema)
    except jsonschema.ValidationError as e:
        raise AssertionError(f"JSON Schema 校验失败 | 路径={list(e.path)} 原因={e.message}")


def assert_elapsed(client, limit_ms: int, api_name: str = ""):
    """性能断言。单个接口超基线即失败 —— 这是"功能测试"和"质量保障"的分界线。"""
    actual = client.last_elapsed_ms
    assert actual <= limit_ms, (
        f"响应超时基线 | 接口={api_name} 基线={limit_ms}ms 实际={actual:.0f}ms"
    )
