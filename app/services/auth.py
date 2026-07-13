"""认证层：R星 BearerToken 的持久化、注入与自动刷新。

机制（依据 astrbot_plugin_gta_online_helper 已验证的实现）：
- token 只活 ~5 分钟，用 `POST socialclub.rockstargames.com/connect/refreshaccess` 续期；
  刷新需带「当前 BearerToken + 一组会话 Cookie(TS*/RockStarWebSessionId/prod)」，
  新 token 从响应的 Set-Cookie 里取，并把响应返回的所有 cookie 回写（滚动续期）。
- 凭证持久化到 SQLite 的 credential 表：authorization(token) 与 refresh_cookies(dict)。

注意：调 scapi 数据端点时只带 Authorization 头、不带 Cookie（避开 CSRF），见 scapi.py。
"""
from __future__ import annotations

import re
from typing import Dict, Optional

import httpx

from app import models

SC_BASE = "https://socialclub.rockstargames.com"
REFRESH_PATH = "/connect/refreshaccess"

# 刷新必需的会话 Cookie（缺任一则无法续期）
REQUIRED_COOKIE_KEYS = (
    "TS01008f56",
    "TS011be943",
    "TS01347d69",
    "RockStarWebSessionId",
    "prod",
)

_JWT_RE = re.compile(r"[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")
_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

# 内存态（进程内缓存，写操作同时落 SQLite）
_authorization: str = ""
_refresh_cookies: Dict[str, str] = {}


class AuthError(RuntimeError):
    """凭证缺失或刷新失败。"""


def sanitize_token(token: str) -> str:
    """从字符串中抠出 JWT，去掉引号与尾部噪声（如 [MSG_ID:xxx]）。"""
    raw = (token or "").strip().strip('"').strip("'")
    if raw.lower().startswith("bearer "):
        raw = raw[7:].strip()
    m = _JWT_RE.search(raw)
    if m:
        return m.group(0)
    # 没匹配到完整 JWT：只保留合法字符，杜绝非 ASCII 导致后续 header 编码崩
    return re.sub(r"[^A-Za-z0-9._-]", "", raw)


def parse_cookie_string(cookie_string: str) -> Dict[str, str]:
    """把 `k1=v1; k2=v2` 的 Cookie 串解析为字典。"""
    out: Dict[str, str] = {}
    for item in (cookie_string or "").split(";"):
        part = item.strip()
        if not part or "=" not in part:
            continue
        k, v = part.split("=", 1)
        k, v = k.strip(), v.strip()
        if k and v:
            out[k] = v
    return out


def load_from_storage() -> None:
    """启动时从 SQLite 恢复内存态。"""
    global _authorization, _refresh_cookies
    auth = models.load_credential("authorization")
    if isinstance(auth, str) and auth.strip():
        _authorization = sanitize_token(auth)
    cookies = models.load_credential("refresh_cookies")
    if isinstance(cookies, dict):
        _refresh_cookies = {str(k): str(v) for k, v in cookies.items() if str(v).strip()}


def set_authorization(token: str) -> None:
    global _authorization
    _authorization = sanitize_token(token)
    models.save_credential("authorization", _authorization)


def set_refresh_cookies(cookies: Dict[str, str]) -> None:
    global _refresh_cookies
    _refresh_cookies = {str(k): str(v).strip() for k, v in cookies.items() if str(v).strip()}
    models.save_credential("refresh_cookies", _refresh_cookies)


def get_authorization() -> str:
    return _authorization


def get_refresh_cookies() -> Dict[str, str]:
    """返回当前缓存的刷新/会话 Cookie（含刷新后更新的 BearerToken 与 TS*）。"""
    return dict(_refresh_cookies)


def missing_refresh_keys() -> list:
    return [k for k in REQUIRED_COOKIE_KEYS if not _refresh_cookies.get(k)]


def update_from_cookie_string(cookie_string: str) -> Dict[str, str]:
    """从完整 Cookie 串注入凭证：提取 BearerToken 作 authorization，整串存为 refresh_cookies。"""
    parsed = parse_cookie_string(cookie_string)
    if "BearerToken" in parsed:
        parsed["BearerToken"] = sanitize_token(parsed["BearerToken"])
        set_authorization(parsed["BearerToken"])
    if parsed:
        merged = dict(_refresh_cookies)
        merged.update(parsed)
        set_refresh_cookies(merged)
    return parsed


def refresh_authorization(timeout: int = 10) -> str:
    """用会话 Cookie 续期 BearerToken，写回并持久化，返回新 token。"""
    current = _authorization.strip()
    if not current:
        raise AuthError("authorization 为空，无法刷新。请先注入 Cookie。")
    missing = missing_refresh_keys()
    if missing:
        raise AuthError(f"刷新 Cookie 不完整，缺少：{', '.join(missing)}")

    cookie_data = dict(_refresh_cookies)
    cookie_data["BearerToken"] = current
    cookie_data.setdefault("AutoLoginCheck", "1")

    headers = {
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
        "Referer": SC_BASE + "/",
        "Origin": SC_BASE,
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "same-origin",
        "Sec-Fetch-Site": "same-origin",
        "User-Agent": _UA,
    }

    with httpx.Client(base_url=SC_BASE, timeout=timeout, follow_redirects=True,
                      cookies=cookie_data, headers=headers) as client:
        resp = client.post(REFRESH_PATH, data={"accessToken": current})
        # refreshaccess 用当前 token 续期；如果 token 已过期，端点返回 401/403
        if resp.status_code in (401, 403):
            raise AuthError(
                f"refreshaccess 返回 {resp.status_code}，当前 BearerToken 已过期（超 5 分钟）。"
                " 请重新从浏览器抓取新鲜 cookie 覆盖到 cookie.txt，然后 setckf 注入。"
            )
        if resp.status_code >= 400:
            raise AuthError(f"refreshaccess 异常 HTTP {resp.status_code}: {resp.text[:160]}")
        # 新 token 与更新后的会话 cookie 都在 cookie jar 里
        jar = {c.name: c.value for c in client.cookies.jar}
        new_token = sanitize_token(jar.get("BearerToken", ""))
        if not new_token:
            new_token = sanitize_token(resp.cookies.get("BearerToken", "") or "")
        # 回写所有响应 cookie（滚动续期）
        if jar:
            merged = dict(_refresh_cookies)
            merged.update({k: v for k, v in jar.items() if v})
            set_refresh_cookies(merged)
        if not new_token:
            raise AuthError("refreshaccess 成功但 Set-Cookie 中未找到 BearerToken。会话可能已过期，请重新注入 Cookie。")

    set_authorization(new_token)
    return new_token
