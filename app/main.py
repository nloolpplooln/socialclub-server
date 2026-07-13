"""SocialClub Query —— 自建 GTA 玩家数据查询 API。

启动: uvicorn app.main:app --reload
"""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

from app.adapters import onebot as onebot_handler
from app.db import init_db
from app.routers import onebot_router, query as query_router
from app.services import auth

logger = logging.getLogger("socialclub")

REFRESH_INTERVAL_MINUTES = 3  # token 5 分钟过期，3 分钟续一次留足缓冲


async def _auto_refresh_loop():
    """后台定时续期 BearerToken。首次立即续期，之后每 3 分钟续一次。"""
    loop = asyncio.get_running_loop()
    # 首次立刻续期
    try:
        await loop.run_in_executor(None, auth.refresh_authorization, 10)
        logger.info("auto-refresh: 首次续期成功")
    except auth.AuthError as e:
        logger.warning("auto-refresh: 首次续期失败 — %s", e)
    except Exception as e:
        logger.error("auto-refresh: 首次异常 — %s", e)

    while True:
        await asyncio.sleep(REFRESH_INTERVAL_MINUTES * 60)
        try:
            await loop.run_in_executor(None, auth.refresh_authorization, 10)
            logger.info("auto-refresh: 续期成功")
        except auth.AuthError as e:
            logger.warning("auto-refresh: 续期失败 — %s", e)
        except Exception as e:
            logger.error("auto-refresh: 异常 — %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    auth.load_from_storage()
    has_auth = bool(auth.get_authorization())
    has_cookies = not auth.missing_refresh_keys()
    if has_auth and has_cookies:
        logger.info("凭证已加载，启动后台续期（每%d分钟）", REFRESH_INTERVAL_MINUTES)
        task = asyncio.create_task(_auto_refresh_loop())
    else:
        task = None
        logger.warning("凭证不完整（auth=%s cookies=%s），未启动续期。请访问 /setup 注入。", has_auth, has_cookies)
    yield
    if task:
        task.cancel()


import json
from fastapi.responses import Response

class UTF8JSONResponse(Response):
    media_type = "application/json"
    def render(self, content) -> bytes:
        return json.dumps(content, ensure_ascii=False).encode("utf-8")

app = FastAPI(title="SocialClub Query", version="0.1.0", lifespan=lifespan, default_response_class=UTF8JSONResponse)
app.include_router(query_router.router)
app.include_router(onebot_router.router)
app.mount("/ui", StaticFiles(directory="static", html=True), name="static")


@app.post("/bot")
async def bot_webhook(request: Request):
    """OneBot 裸端点（绕过路由器，直接处理）。"""
    try:
        payload = await request.json()
    except Exception as e:
        return {"reply": "", "error": f"json parse: {e}"}
    pt = payload.get("post_type", "")
    if pt not in ("message", "message_sent"):
        return {"reply": f"skip post_type={pt}"}
    try:
        reply = await onebot_handler.handle_message(payload)
        return {"reply": reply or "(None)"}
    except Exception as e:
        return {"reply": "", "error": str(e)}


@app.get("/")
def root():
    return {"service": "SocialClub Query", "docs": "/docs", "setup": "/setup", "ui": "/ui"}


@app.get("/setup")
def setup_page():
    """初次配置页面：粘贴 Cookie 即可注入。"""
    from fastapi.responses import FileResponse
    import os
    path = os.path.join(os.path.dirname(__file__), "..", "static", "setup.html")
    return FileResponse(path)


@app.get("/health")
def health():
    """健康检查：返回 token 状态。"""
    tok = auth.get_authorization()
    missing = auth.missing_refresh_keys()
    return {
        "has_token": bool(tok),
        "token_preview": (tok[:16] + "...") if tok else None,
        "refresh_ready": not missing,
        "missing_keys": missing,
    }

