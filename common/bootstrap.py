# -*- coding: utf-8 -*-
"""把被测服务作为子进程拉起（供无界面/CI 场景一键跑通用）。

在 conftest 里以 session 级 autouse 夹具调用，测试结束自动关闭。
"""
import os
import socket
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = int(os.getenv("SHOP_PORT", "8080"))


def port_open(host="127.0.0.1", port=PORT, timeout=0.5) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        return s.connect_ex((host, port)) == 0


def start_server(port=PORT, wait_seconds=15):
    """返回 (process 或 None)。已在运行则复用，返回 None。"""
    if port_open(port=port):
        print(f"[bootstrap] 端口 {port} 已在监听，复用现有服务")
        return None

    env = dict(os.environ)
    for k in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "all_proxy"):
        env.pop(k, None)

    proc = subprocess.Popen(
        [sys.executable, os.path.join(ROOT, "scripts", "mock_server.py"), str(port)],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    deadline = time.time() + wait_seconds
    while time.time() < deadline:
        if port_open(port=port):
            print(f"[bootstrap] 被测服务已启动 pid={proc.pid} port={port}")
            return proc
        time.sleep(0.3)
    proc.terminate()
    raise RuntimeError(f"被测服务启动失败，{wait_seconds}s 内未监听 {port} 端口")
