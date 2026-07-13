"""QQ 机器人：OneBot v11 适配（NapCat / Lagrange 等 HTTP 上报）。

用法：
  1. 在 OneBot 客户端配置 HTTP 上报地址为 http://127.0.0.1:8686/onebot
  2. 群内或私聊发送「查询 <昵称>」或「查生涯 <昵称>」或「查战眼 <RID>」

返回格式化文本（中文键值对 + 统计分类）。
"""
from __future__ import annotations

import asyncio
import re
from typing import Any, Dict, Optional

import httpx

from app.services import query as query_svc
from app.services.auth import AuthError

# ── 命令匹配 ──
_CMD_RE = re.compile(r"^(?:查询|查生涯|查资料|/gta\s+career|/chazy)\s*(?P<nick>\S+)", re.I)
_BE_RE = re.compile(r"^(?:查战眼|/gta\s+be|/be|战眼)\s*(?P<target>\S+)", re.I)
_ME_RE = re.compile(r"^(?:/gta\s+me|查我|my)$", re.I)
_HELP_RE = re.compile(r"^(?:/gta\s+help|/gta\s+h|帮助|help)$", re.I)


def _format_player(result) -> str:
    p = result.profile
    s = result.stats
    lines = [f"玩家: {p.nickname}  RID: {p.rockstar_id}"]
    if p.country_code:
        lines.append(f"所在地: {p.country_code}")
    if p.primary_crew:
        lines.append(f"主帮会: {p.primary_crew.name} [{p.primary_crew.tag}]")
    if p.games:
        gs = ", ".join(f"{g.name}({g.last_seen or '?'})" for g in p.games)
        lines.append(f"游戏: {gs}")
    if p.friend_count:
        lines.append(f"好友: {p.friend_count}")
    if p.linked_accounts:
        linked = ", ".join(f"{a.service}:{a.user_name}" for a in p.linked_accounts if a.user_name)
        if linked:
            lines.append(f"绑定: {linked}")
    lines.append("")
    if s and s.categories:
        career = s.categories.get("career", {})
        keys_map = [
            ("Overall income", "总收入"),
            ("Overall expenses", "总花费"),
            ("Total players killed", "击杀玩家"),
            ("Total deaths by players", "被击杀"),
            ("Time spent in GTA Online", "在线时长"),
        ]
        for ek, cn in keys_map:
            if ek in career:
                lines.append(f"{cn}: {career[ek]}")
        skills = s.categories.get("skills", {})
        if skills:
            skill_str = " | ".join(f"{k}:{v.split('%')[0]}%" for k, v in list(skills.items())[:4] if v.strip())
            lines.append(f"技能: {skill_str}")
    if result.cached:
        lines.append("[缓存]")
    return "\n".join(lines)


async def handle_message(payload: Dict[str, Any], onebot_api_url: str = "") -> Optional[str]:
    """处理一条 OneBot 消息事件，返回要回复的文本（None 表示不回复）。

    onebot_api_url: OneBot HTTP API 地址，默认从 payload 推断或留空。
    """
    msg = str((payload.get("raw_message") or payload.get("message") or "")).strip()
    user_id = payload.get("user_id", "")
    group_id = payload.get("group_id", "")

    if not msg:
        return None

    msg = msg.strip()

    # 帮助
    if _HELP_RE.match(msg):
        return (
            "GTA 玩家查询:\n"
            "  查询 <昵称>    完整资料+生涯\n"
            "  查生涯 <昵称>   同上\n"
            "  查战眼 <RID>    战眼封禁(暂未实现)\n"
            "  /gta me         查绑定的我(需先绑定)"
        )

    # 绑定（简版，内存存一份）
    m_be = _BE_RE.match(msg)
    if m_be:
        target = m_be.group("target")
        return f"战眼查询「{target}」暂未集成（需 BattlEye UDP 服务器），RID 查询开发中。"

    m = _CMD_RE.match(msg)
    if not m:
        return None
    nickname = m.group("nick")

    try:
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, lambda: query_svc.query_player(nickname, persist=False))
    except AuthError:
        return "凭证未配置或已过期。请管理员执行 setckf 注入新鲜 cookie。"
    except Exception as e:
        return f"查询失败: {e}"

    return _format_player(result)


# ── FastAPI 集成（见 routers/onebot_router.py）──
