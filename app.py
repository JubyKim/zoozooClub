#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Kyobo DTS Teams Bot (Final Version)
====================================
FastAPI + BotBuilder SDK + Nginx reverse proxy
"""

import os
import logging
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from botbuilder.core import (
    BotFrameworkAdapterSettings,
    BotFrameworkAdapter,
    TurnContext,
)
from botbuilder.schema import Activity
from dotenv import load_dotenv

# =========================
#  환경 변수 로드에요잉
# =========================
load_dotenv()

MICROSOFT_APP_ID = os.getenv("MICROSOFT_APP_ID", "")
MICROSOFT_APP_PASSWORD = os.getenv("MICROSOFT_APP_PASSWORD", "")
MICROSOFT_APP_TYPE = os.getenv("MicrosoftAppType", "SingleTenant")
MICROSOFT_TENANT_ID = os.getenv("MicrosoftAppTenantId", "")

# =========================
#  로깅 설정
# =========================
logging.basicConfig(
    format="%(asctime)s - kyobo-dts-bot - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("kyobo-dts-bot")

logger.info("[Startup] MICROSOFT_APP_ID: %s", MICROSOFT_APP_ID or "(not set)")
logger.info("[Startup] APP_TYPE=%s TENANT_ID=%s", MICROSOFT_APP_TYPE, MICROSOFT_TENANT_ID)

# =========================
#  어댑터 & 봇 설정
# =========================
if MICROSOFT_APP_ID and MICROSOFT_APP_PASSWORD:
    # 기존
    # adapter_settings = BotFrameworkAdapterSettings(MICROSOFT_APP_ID, MICROSOFT_APP_PASSWORD)
    # adapter = BotFrameworkAdapter(adapter_settings)

    # 교체 (SingleTenant 대응)
    from botbuilder.core import BotFrameworkAdapterSettings, BotFrameworkAdapter

    SINGLE = (os.getenv("MicrosoftAppType", "SingleTenant").lower() == "singletenant")
    TENANT = os.getenv("MicrosoftAppTenantId", "")

    if MICROSOFT_APP_ID and MICROSOFT_APP_PASSWORD:
        adapter_settings = BotFrameworkAdapterSettings(
            MICROSOFT_APP_ID,
            MICROSOFT_APP_PASSWORD,
            channel_auth_tenant = MICROSOFT_TENANT_ID if MICROSOFT_APP_TYPE.lower() == "singletenant" and MICROSOFT_TENANT_ID else None
        )
        adapter = BotFrameworkAdapter(adapter_settings)
    else:
        adapter = BotFrameworkAdapter(BotFrameworkAdapterSettings("", ""))

else:
    logger.warning("MICROSOFT_APP_ID or MICROSOFT_APP_PASSWORD not set — running in local/emulator mode.")
    adapter = BotFrameworkAdapter(BotFrameworkAdapterSettings("", ""))

# 전역 에러 핸들러
async def on_error(context: TurnContext, error: Exception):
    logger.error(f"on_turn_error: {error}", exc_info=True)
    await context.send_activity("⚠️ 봇 실행 중 오류가 발생했습니다. 로그를 확인하세요.")

adapter.on_turn_error = on_error


# =========================
#  봇 로직 (간단 예제)
# =========================
class KyoboDTSBot:
    async def on_turn(self, turn_context: TurnContext):
        if turn_context.activity.type == "message":
            text = turn_context.activity.text.strip().lower()
            logger.info(f"[User Message] {text}")
            if text in ["hi", "hello", "안녕", "ㅎㅇ"]:
                await turn_context.send_activity("안녕하세요, 교보DTS 봇입니다 😊")
            elif "시간" in text:
                import datetime
                now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                await turn_context.send_activity(f"현재 서버 시각은 {now} 입니다.")
            elif "help" in text or "도움" in text:
                await turn_context.send_activity("명령어 목록:\n- 안녕\n- 시간\n- help")
            else:
                await turn_context.send_activity(f"'{text}' 명령은 아직 지원되지 않습니다.")
        else:
            logger.info(f"[System Event] {turn_context.activity.type}")

bot = KyoboDTSBot()


# =========================
#  FastAPI 서버
# =========================
app = FastAPI()

@app.get("/")
async def root():
    """Health check"""
    return {"status": "ok", "app_id": MICROSOFT_APP_ID or "local"}


@app.post("/api/messages")
async def messages(req: Request) -> Response:
    """봇 메시지 처리 엔드포인트"""
    try:
        body = await req.json()
        activity = Activity().deserialize(body)
        auth_header = req.headers.get("Authorization", "")
        logger.info(f"[Activity] from={activity.from_property.id if activity.from_property else 'unknown'} "
                    f"type={activity.type}")
        await adapter.process_activity(activity, auth_header, bot.on_turn)
        return Response(status_code=201)
    except Exception as e:
        logger.error("Error in /api/messages", exc_info=True)
        return JSONResponse(status_code=500, content={"error": str(e)})


# =========================
#  서버 실행
# =========================
if __name__ == "__main__":
    import uvicorn

    logger.info("Uvicorn starting on http://0.0.0.0:3978")
    uvicorn.run("app:app", host="0.0.0.0", port=3978, reload=False)
