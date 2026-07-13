"""OneBot v11 HTTP 上报接收端点。"""
from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Request

from app.adapters import onebot

router = APIRouter(prefix="/onebot", tags=["onebot"])


@router.post("")
async def onebot_event(request: Request):
    """接收 OneBot HTTP 上报事件，返回回复文本。

    配置：在 NapCat / Lagrange 中将 HTTP 上报地址设为
      http://<host>:8686/onebot
    """
    try:
        payload: Dict[str, Any] = await request.json()
    except Exception:
        return {"reply": ""}

    post_type = payload.get("post_type", "")
    if post_type not in ("message", "message_sent"):
        return {"reply": ""}

    reply = await onebot.handle_message(payload)
    return {"reply": reply or ""}
