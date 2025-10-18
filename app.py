import os, logging
from aiohttp import web
from botbuilder.core import BotFrameworkAdapterSettings, BotFrameworkAdapter, TurnContext, ActivityHandler
from botbuilder.schema import Activity, ActivityTypes

APP_ID       = os.getenv("MicrosoftAppId", "")
APP_PASSWORD = os.getenv("MicrosoftAppPassword", "")
APP_TYPE     = os.getenv("MicrosoftAppType", "")
APP_TENANT   = os.getenv("MicrosoftAppTenantId", "")
PORT         = int(os.getenv("PORT", "3978"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s - kyobo-dts-bot - %(levelname)s - %(message)s")
log = logging.getLogger("kyobo-dts-bot")
mask = lambda s: (s[:4] + "..." + s[-4:]) if s else "-"
log.info(f"[Startup] AppId={mask(APP_ID)} Type={APP_TYPE or '-'} Tenant={APP_TENANT or '-'} Port={PORT}")

# Adapter 설정 + OAuth 스코프 명시(아주 중요)
settings = BotFrameworkAdapterSettings(APP_ID, APP_PASSWORD)
# 공용 Azure Bot Service용 표준 스코프
settings.oauth_scope = "https://api.botframework.com/.default"
adapter = BotFrameworkAdapter(settings)

async def on_error(ctx: TurnContext, err: Exception):
    log.exception("on_turn_error: %s", err)
    try:
        await ctx.send_activity("죄송해요. 내부 오류가 발생했어요.")
    except Exception:
        pass
adapter.on_turn_error = on_error

class EchoBot(ActivityHandler):
    async def on_message_activity(self, turn_context: TurnContext):
        await turn_context.send_activity(f"echo: {turn_context.activity.text or ''}")
    async def on_members_added_activity(self, members_added, turn_context: TurnContext):
        await turn_context.send_activity("안녕하세요! 메시지를 보내면 그대로 돌려드려요 :)")

bot = EchoBot()

routes = web.RouteTableDef()
@routes.get("/healthz")
async def healthz(_): return web.Response(text="ok")

@routes.post("/api/messages")
async def messages(request: web.Request):
    auth_header = request.headers.get("Authorization", "")
    body = await request.json()
    activity = Activity().deserialize(body)
    try:
        await adapter.process_activity(activity, auth_header, bot.on_turn)
        return web.Response(status=200)
    except PermissionError as e:
        log.warning("Unauthorized: %s", e)
        return web.Response(status=401, text="unauthorized")
    except Exception as e:
        log.exception("Error handling /api/messages: %s", e)
        return web.Response(status=500, text="internal-error")

app = web.Application()
app.add_routes(routes)

if __name__ == "__main__":
    log.info("Listening on 0.0.0.0:%s", PORT)
    web.run_app(app, host="0.0.0.0", port=PORT)
