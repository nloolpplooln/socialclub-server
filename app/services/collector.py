"""[已废弃] 网页抓取采集层 —— 保留仅作参考。

实测证明 Social Club 网页路径（/member/...）未登录会 302→AuthCheck，带登录态也会
跳转到 OAuth 授权页，无法程序化。数据采集已改走 scapi（见 app/services/scapi.py）
+ token 自动刷新（app/services/auth.py）。本文件不再使用。

--- 原说明 ---
采集层：带 R星 登录 Cookie 请求 Social Club 页面。
只负责「把带登录态的原始 HTML 抓回来」，解析交给 parser。
包含超时、重试、代理、登录失效检测。
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, List, Optional

import httpx

from app.config import get_settings
from app.services import parser

BASE = "https://socialclub.rockstargames.com"

# 候选页面路径（不同页面藏不同数据，按需扩展）。{nick} 处替换昵称。
MEMBER_PATHS: List[str] = [
    "/member/{nick}/games/gtav/career",
    "/member/{nick}",
]

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


class AuthExpiredError(RuntimeError):
    """登录 Cookie 失效（被 R星 挡在 AuthCheck）。"""


class CollectError(RuntimeError):
    """网络/HTTP 层面采集失败。"""


@dataclass
class FetchResult:
    url: str
    final_url: str
    status_code: int
    html: str


def _headers() -> Dict[str, str]:
    s = get_settings()
    if not s.rsc_cookie:
        raise AuthExpiredError("未配置 RSC_COOKIE，请先在 .env 填入登录后的 Cookie")
    headers = {
        "User-Agent": _UA,
        "Cookie": s.rsc_cookie,
        "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": BASE + "/",
    }
    if s.rsc_request_verification_token:
        headers["RequestVerificationToken"] = s.rsc_request_verification_token
    return headers


def fetch(path: str) -> FetchResult:
    """请求单个路径，带重试。返回 FetchResult；登录失效抛 AuthExpiredError。"""
    s = get_settings()
    url = BASE + path
    proxy = s.http_proxy or None
    last_exc: Optional[Exception] = None

    for attempt in range(s.http_retries + 1):
        try:
            with httpx.Client(
                timeout=s.http_timeout,
                follow_redirects=True,
                proxy=proxy,
                headers=_headers(),
            ) as client:
                resp = client.get(url)
                final_url = str(resp.url)
                if parser.is_auth_blocked(resp.text, final_url) or resp.status_code in (401, 403):
                    raise AuthExpiredError(f"登录态失效或无权限：{final_url}")
                return FetchResult(url=url, final_url=final_url, status_code=resp.status_code, html=resp.text)
        except AuthExpiredError:
            raise
        except httpx.HTTPError as exc:
            last_exc = exc
            if attempt < s.http_retries:
                time.sleep(1.0 * (attempt + 1))
    raise CollectError(f"采集失败 {url}: {last_exc}")


def collect_player_raw(nickname: str) -> FetchResult:
    """依次尝试候选路径，返回第一个成功抓到、且能解析出嵌入 JSON 的页面。"""
    errors = []
    for tpl in MEMBER_PATHS:
        path = tpl.format(nick=nickname)
        try:
            res = fetch(path)
        except CollectError as exc:
            errors.append(str(exc))
            continue
        if parser.extract_embedded_json(res.html):
            return res
        errors.append(f"{path}: 页面无可解析 JSON")
    raise CollectError("所有候选路径均未取得数据：" + " | ".join(errors))
