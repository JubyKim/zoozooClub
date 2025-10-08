# app.py
import os
import uvicorn
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, status, HTTPException
from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings, TurnContext
from botbuilder.schema import Activity

from config import get_config
from src.bot.activity_handler import MyBot

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("kyobo-dts-bot")

# 전역 인스턴스
bot_instance = None
adapter_instance = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 생명주기 관리"""
    global bot_instance, adapter_instance

    # 설정 로드
    config = get_config()
    app_id = getattr(config, "APP_ID", "") or os.getenv("MICROSOFT_APP_ID", "")
    app_password = getattr(config, "APP_PASSWORD", "") or os.getenv("MICROSOFT_APP_PASSWORD", "")
    port = int(getattr(config, "PORT", os.getenv("PORT", 3978)))

    if not app_id or not app_password:
        logger.info(
            "[Startup] MICROSOFT_APP_ID / PASSWORD 미설정: Bot Framework Emulator 로컬/테스트 모드로 동작합니다."
        )
        logger.info("          실제 Teams 연결 시에는 App ID/Password 가 반드시 필요합니다.")

    settings = BotFrameworkAdapterSettings(app_id, app_password)
    adapter_instance = BotFrameworkAdapter(settings)

    async def on_error(context: TurnContext, error: Exception):
        logger.error(f"[OnTurnError] {error}", exc_info=True)
        try:
            await context.send_activity("죄송합니다, 봇 처리 중 오류가 발생했습니다.")
        except Exception:
            # 응답 보낼 수 없는 상황은 조용히 패스
            pass

    adapter_instance.on_turn_error = on_error
    bot_instance = MyBot()

    logger.info("[Startup] Bot application started successfully")
    logger.info(f"[Startup] Listening on 0.0.0.0:{port} (/api/messages)")

    # 앱 상태 공유(필요시)
    app.state.port = port

    try:
        yield
    finally:
        # 종료 훅
        if bot_instance and hasattr(bot_instance, "cleanup"):
            try:
                await bot_instance.cleanup()
                logger.info("[Shutdown] Bot cleanup complete")
            except Exception as e:
                logger.warning(f"[Shutdown] cleanup 중 예외: {e}")
        logger.info("[Shutdown] Bot application shutdown complete")


# FastAPI 앱 초기화
app = FastAPI(
    title="교보DTS 온보딩 멘토 AI Bot",
    description="Microsoft Teams 온보딩 챗봇",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/")
async def root():
    return {
        "service": "kyobo-dts-bot",
        "status": "running",
        "message": "POST /api/messages 로 Bot Framework 액티비티를 전송하세요.",
    }


@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {"status": "healthy", "service": "kyobo-dts-bot"}


@app.post("/api/messages")
async def messages(request: Request):
    """Bot Framework 메시지 처리 엔드포인트 (POST만 허용)"""
    if not adapter_instance or not bot_instance:
        raise HTTPException(status_code=503, detail="Bot not initialized")

    # Content-Type 검증
    content_type = request.headers.get("Content-Type", "")
    if "application/json" not in content_type:
        # Emulator/채널에서 JSON이 아닌 형식으로 올 경우를 방지
        raise HTTPException(status_code=415, detail="Content-Type must be application/json")

    try:
        body = await request.json()
        activity = Activity().deserialize(body)
        auth_header = request.headers.get("Authorization", "")

        await adapter_instance.process_activity(activity, auth_header, bot_instance.on_turn)
        # Bot Framework 표준: 202 Accepted
        return Response(status_code=status.HTTP_202_ACCEPTED)

    except Exception as e:
        logger.error(f"[messages] processing error: {e}", exc_info=True)
        # 요청 본문 문제면 400, 그 외에는 500으로 내보내도 됨
        raise HTTPException(status_code=400, detail="Invalid request payload")


if __name__ == "__main__":
    # get_config() 또는 환경변수에서 포트/호스트 로드
    try:
        _cfg = get_config()
        _port = int(getattr(_cfg, "PORT", os.getenv("PORT", 3978)))
    except Exception:
        _port = int(os.getenv("PORT", 3978))

    # 외부 접속 가능하도록 host="0.0.0.0"
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=_port,
        reload=False,          # 서버에서 reload는 보통 비활성화
        log_level="info",
        access_log=True,
    )
