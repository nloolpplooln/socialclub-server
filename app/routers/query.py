"""REST API: /api/player ?nickname=  + /api/player/profile  + /api/player/stats"""
from __future__ import annotations

from fastapi import APIRouter, Query

from app.schemas import ApiResponse
from app.services import query as query_svc
from app.services.auth import AuthError
from app.services.scapi import ScapiError
from app.services.webstats import WebStatsError

router = APIRouter(prefix="/api", tags=["player"])


@router.post("/setup")
def setup_cookie(payload: dict):
    """一键配置：POST {"cookie": "完整Cookie字符串"}"""
    cookie = (payload or {}).get("cookie", "").strip()
    if not cookie:
        return ApiResponse(code=400, message="请提供 cookie 字段").model_dump()
    from app.services import auth
    try:
        parsed = auth.update_from_cookie_string(cookie)
        missing = auth.missing_refresh_keys()
        return ApiResponse(code=200, message="ok", body={
            "keys": sorted(parsed.keys()),
            "missing_refresh_keys": missing,
            "token_preview": auth.get_authorization()[:20] + "...",
        }).model_dump()
    except Exception as e:
        return ApiResponse(code=500, message=str(e)).model_dump()


def _ok(body, cached: bool = False, msg: str = "ok") -> dict:
    return ApiResponse(code=200, message=msg, body=body).model_dump()


def _err(code: int, msg: str) -> dict:
    return ApiResponse(code=code, message=msg).model_dump()


@router.get("/player")
def get_player(nickname: str = Query(..., description="玩家昵称"), force: bool = Query(False, description="强制刷新,跳过缓存")):
    """完整查询：基础资料 + 深度生涯统计。"""
    try:
        result = query_svc.query_player(nickname, persist=not force)
    except AuthError as e:
        return _err(401, str(e))
    except ScapiError as e:
        code = 404 if "不存" in str(e) else 502
        return _err(code, str(e))
    except WebStatsError as e:
        return _err(502, str(e))
    except Exception as e:
        return _err(500, str(e))
    # 异常检测（含奖章）
    from app.services.judgement import check as judge_check
    player_data = {
        "profile": result.profile.model_dump() if result.profile else {},
        "overview": result.overview.model_dump() if result.overview else {},
        "stats": result.stats.model_dump() if result.stats else {},
    }
    awards_data = None
    try:
        awards_data = query_svc.query_awards(nickname, persist=not force)
    except Exception:
        pass
    judge_findings = judge_check(player_data, awards_data)
    body = {
        "nickname": result.profile.nickname if result.profile else nickname,
        "profile": player_data["profile"] or None,
        "overview": player_data["overview"] or None,
        "stats": player_data["stats"] or None,
        "cached": result.cached,
        "updated_at": result.updated_at,
        "judgements": [{"level": lv, "message": msg} for lv, msg in judge_findings],
    }
    return _ok(body, cached=result.cached, msg="cached" if result.cached else "fresh")


@router.get("/player/profile")
def get_profile_only(nickname: str = Query(..., description="玩家昵称")):
    """仅基础资料（更快）。"""
    try:
        result = query_svc.query_player(nickname)
    except AuthError as e:
        return _err(401, str(e))
    except ScapiError as e:
        code = 404 if "不存" in str(e) else 502
        return _err(code, str(e))
    except WebStatsError as e:
        return _err(502, str(e))
    return _ok(result.profile.model_dump() if result.profile else None, cached=result.cached)


@router.get("/player/stats")
def get_stats_only(nickname: str = Query(..., description="玩家昵称")):
    """仅深度生涯统计。"""
    try:
        result = query_svc.query_player(nickname)
    except AuthError as e:
        return _err(401, str(e))
    except ScapiError as e:
        code = 404 if "不存" in str(e) else 502
        return _err(code, str(e))
    except WebStatsError as e:
        return _err(502, str(e))
    return _ok(result.stats.model_dump() if result.stats else None, cached=result.cached)


@router.get("/player/awards")
def get_awards(nickname: str = Query(..., description="玩家昵称"),
               category: str = Query("", description="奖章分类"),
               force: bool = Query(False, description="强制刷新,跳过缓存")):
    """查询奖章完成情况。4 小时内走缓存，传 force=true 跳过。"""
    try:
        awards = query_svc.query_awards(nickname, category=category, persist=not force)
        # 同时获取玩家数据做异常检测
        from app.services.judgement import check as judge_check
        player = query_svc.query_player(nickname, persist=not force)
        player_data = {
            "profile": player.profile.model_dump() if player.profile else {},
            "overview": player.overview.model_dump() if player.overview else {},
            "stats": player.stats.model_dump() if player.stats else {},
        }
        judge_findings = judge_check(player_data, awards)
        return _ok({
            "nickname": nickname,
            "awards": awards,
            "judgements": [{"level": lv, "message": msg} for lv, msg in judge_findings],
        })
    except AuthError as e:
        return _err(401, str(e))
    except WebStatsError as e:
        return _err(502, str(e))
    except ScapiError as e:
        return _err(404 if "不存" in str(e) else 502, str(e))
    except Exception as e:
        return _err(500, str(e))
