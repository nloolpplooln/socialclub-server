"""自建采集的命令行入口。

用法（用 .venv314 跑）：
  # 1) 注入并持久化凭证（完整 Cookie 串，含 BearerToken/TS*/RockStarWebSessionId/prod）
  python -m app.cli setck "BearerToken=...; TS01008f56=...; ..."
  # 2) 查看凭证状态（脱敏）
  python -m app.cli show
  # 3) 手动刷新 token（验证续期链路）
  python -m app.cli refresh
  # 4) 取某玩家的 scapi 原始资料
  python -m app.cli profile <nickname>
  # 5) 探明 scapi 能拿到哪些数据（打印 getprofile 全文 + 试探其它端点）
  python -m app.cli probe <nickname>
"""
from __future__ import annotations

import json
import sys

# 避免 Windows GBK 控制台编码报错
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:
    pass

from app import models
from app.db import init_db
from app.services import auth, scapi


def _mask(tok: str) -> str:
    return f"{tok[:10]}...({len(tok)})" if tok and len(tok) > 10 else "<empty>"


def cmd_setck(cookie: str) -> int:
    parsed = auth.update_from_cookie_string(cookie)
    if not parsed:
        print("✗ Cookie 解析为空，检查格式：k1=v1; k2=v2")
        return 1
    missing = auth.missing_refresh_keys()
    print(f"✓ 已注入并持久化。字段：{sorted(parsed.keys())}")
    print(f"  authorization = {_mask(auth.get_authorization())}")
    if missing:
        print(f"  ⚠ 刷新所需字段缺失：{missing}（缺了将无法自动续期）")
    else:
        print("  ✓ 刷新所需 Cookie 齐全，可自动续期")
    return 0


def cmd_setckf(path: str) -> int:
    """从文件读取整段 Cookie 并注入（避免命令行转录超长 token 出错）。"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            cookie = f.read().strip()
    except OSError as e:
        print(f"✗ 读取文件失败：{e}")
        return 1
    if not cookie:
        print("✗ 文件为空。")
        return 1
    return cmd_setck(cookie)


def cmd_show() -> int:
    auth.load_from_storage()
    cookies = models.load_credential("refresh_cookies") or {}
    print(f"authorization = {_mask(auth.get_authorization())}")
    print(f"refresh cookies keys = {sorted(cookies.keys())}")
    print(f"缺失刷新字段 = {auth.missing_refresh_keys()}")
    return 0


def cmd_refresh() -> int:
    auth.load_from_storage()
    try:
        tok = auth.refresh_authorization()
        print(f"✓ 刷新成功，新 token = {_mask(tok)}")
        return 0
    except auth.AuthError as e:
        print(f"✗ 刷新失败：{e}")
        return 1


def cmd_profile(nickname: str) -> int:
    auth.load_from_storage()
    try:
        data = scapi.get_profile(nickname)
    except (auth.AuthError, scapi.ScapiError) as e:
        print(f"✗ 查询失败：{e}")
        return 1
    print(json.dumps(data, ensure_ascii=False, indent=2)[:4000])
    return 0


def cmd_probe(nickname: str) -> int:
    """打印 getprofile 全文，帮助确认 scapi 实际能拿到哪些字段。"""
    auth.load_from_storage()
    try:
        data = scapi.get_profile(nickname)
    except (auth.AuthError, scapi.ScapiError) as e:
        print(f"✗ getprofile 失败：{e}")
        return 1
    print("==== getprofile 顶层键 ====")
    print(list(data.keys()))
    print("\n==== 完整 JSON（截断 6000 字符）====")
    print(json.dumps(data, ensure_ascii=False, indent=2)[:6000])
    return 0


def cmd_stats(nickname: str) -> int:
    """等级/金钱/深度统计（StatsAjax + overviewAjax）。"""
    from app.services import webstats
    auth.load_from_storage()
    if not auth.get_authorization():
        print("✗ 未注入凭证，请先: python -m app.cli setckf cookie.txt")
        return 1
    try:
        ov = webstats.fetch_gtav_overview(nickname)
        print(f"=== {nickname} 等级 & 金钱 ===")
        for k, v in ov.items():
            print(f"  {k}: {v}")
    except Exception as e:
        print(f"  overviewAjax 失败: {e}")
    try:
        stats = webstats.fetch_gtav_stats(nickname)
        print(f"\n=== {nickname} 深度统计 ===")
        for cat, items in stats.items():
            print(f"  [{cat}] {len(items)}项")
            for k, v in list(items.items())[:5]:
                print(f"    {k}: {v}")
            if len(items) > 5:
                print(f"    ... 共{len(items)}项")
    except Exception as e:
        print(f"  StatsAjax 失败: {e}")
    return 0


def cmd_query(nickname: str) -> int:
    """综合查询：SCAPI 资料 + 等级金钱。"""
    auth.load_from_storage()
    if not auth.get_authorization():
        print("✗ 未注入凭证，请先: python -m app.cli setckf cookie.txt")
        return 1
    try:
        data = scapi.get_profile(nickname)
        acc = data["accounts"][0]
        ra = acc["rockstarAccount"]
        print(f"=== {nickname} 资料 (SCAPI) ===")
        print(f"  昵称: {ra['name']}")
        print(f"  RID: {ra['rockstarId']}")
        print(f"  所在地: {ra['countryCode']}")
        print(f"  好友: {ra['friendCount']}")
        clan = ra.get("primaryClan")
        if clan:
            print(f"  帮会: {clan.get('Name','?')} [{clan.get('Tag','?')}]")
        for g in ra.get("gamesOwned", []):
            print(f"  游戏: {g['name']} (最近:{g.get('lastSeen','?')})")
    except Exception as e:
        print(f"  SCAPI 失败: {e}")
        return 1
    return cmd_stats(nickname)


def main(argv: list) -> int:
    init_db()
    if not argv:
        print(__doc__)
        return 64
    cmd, rest = argv[0], argv[1:]
    if cmd == "setck":
        if not rest:
            print("用法: python -m app.cli setck \"<完整Cookie串>\"")
            return 64
        return cmd_setck(" ".join(rest))
    if cmd == "setckf":
        if not rest:
            print("用法: python -m app.cli setckf <cookie文件路径>")
            return 64
        return cmd_setckf(rest[0])
    if cmd == "show":
        return cmd_show()
    if cmd == "refresh":
        return cmd_refresh()
    if cmd in ("profile", "probe"):
        if not rest:
            print(f"用法: python -m app.cli {cmd} <nickname>")
            return 64
        return cmd_profile(rest[0]) if cmd == "profile" else cmd_probe(rest[0])
    if cmd == "stats":
        if not rest:
            print("用法: python -m app.cli stats <nickname>")
            return 64
        return cmd_stats(rest[0])
    if cmd == "query":
        if not rest:
            print("用法: python -m app.cli query <nickname>")
            return 64
        return cmd_query(rest[0])
    print(f"未知命令：{cmd}")
    print(__doc__)
    return 64


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
