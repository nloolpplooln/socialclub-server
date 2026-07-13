"""对外数据结构：把 scapi + StatsAjax 两张数据源映射为干净的 Player 结果。"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class Game(BaseModel):
    name: str
    platform: Optional[str] = None
    last_seen: Optional[str] = None


class LinkedAccount(BaseModel):
    service: str
    user_name: Optional[str] = None
    user_id: Optional[str] = None


class Crew(BaseModel):
    id: int
    name: Optional[str] = None
    tag: Optional[str] = None
    motto: Optional[str] = None
    member_count: Optional[int] = None
    is_primary: bool = False
    created_at: Optional[str] = None


class PlayerProfile(BaseModel):
    """基础资料（来自 scapi getprofile）。"""
    nickname: Optional[str] = None
    rockstar_id: Optional[int] = None
    avatar_url: Optional[str] = None
    country_code: Optional[str] = None
    friend_count: Optional[int] = None
    primary_crew: Optional[Crew] = None
    crews: List[Crew] = []
    games: List[Game] = []
    linked_accounts: List[LinkedAccount] = []


class PlayerStats(BaseModel):
    """深度生涯数据（来自 StatsAjax，200+ 项按分类分组）。"""
    categories: Dict[str, Dict[str, str]] = {}


class OverviewData(BaseModel):
    """等级/金钱概览（来自 overviewAjax）。"""
    rank: Optional[str] = None
    rp: Optional[str] = None
    cash: Optional[str] = None
    bank: Optional[str] = None
    play_time: Optional[str] = None
    crew_name: Optional[str] = None


class PlayerResult(BaseModel):
    """一次查询的完整结果。"""
    profile: Optional[PlayerProfile] = None
    overview: Optional[OverviewData] = None
    stats: Optional[PlayerStats] = None
    cached: bool = False
    updated_at: Optional[int] = None  # unix 秒


class ApiResponse(BaseModel):
    """统一返回体（对齐空桑 {code, message, body} 风格）。"""
    code: int = 200
    message: str = "ok"
    body: Any = None
