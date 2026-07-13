"""集中配置：从环境变量 / .env 读取。真实 Cookie 只存在本地 .env，不入库。"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Rockstar 登录态
    rsc_cookie: str = ""
    rsc_request_verification_token: str = ""

    # 采集
    cache_ttl_seconds: int = 14400
    http_timeout: int = 60
    http_retries: int = 2
    http_proxy: str = ""

    # 限速
    post_rate_per_hour: int = 10
    query_rate_per_10min: int = 60

    # 存储
    db_path: str = "socialclub.db"


@lru_cache
def get_settings() -> Settings:
    return Settings()
