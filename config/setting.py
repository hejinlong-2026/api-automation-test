# -*- coding: utf-8 -*-
"""全局配置。通过环境变量覆盖，便于 CI 与本地切换。"""
import os


class Config:
    BASE_URL: str = os.getenv("SHOP_BASE_URL", "http://127.0.0.1:8080")
    TIMEOUT: int = int(os.getenv("SHOP_TIMEOUT", "10"))

    USER_A: dict = {"phone": "13800000001", "password": "test123456"}
    USER_B: dict = {"phone": "13800000002", "password": "test123456"}

    # 性能基线（毫秒）
    SLA_LOGIN_MS: int = int(os.getenv("SLA_LOGIN_MS", "800"))
    SLA_LIST_MS: int = int(os.getenv("SLA_LIST_MS", "500"))


CONF = Config()
