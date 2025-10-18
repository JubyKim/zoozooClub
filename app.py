
import os
import logging
from aiohttp import web
from botbuilder.core import BotFrameworkAdapterSettings, BotFrameworkAdapter, TurnContext, ActivityHandler
from botbuilder.schema import Activity, ActivityTypes

APP_ID       = os.getenv("MicrosoftAppId", "")
APP_PASSWORD = os.getenv("MicrosoftAppPassword", "")
APP_TYPE     = os.getenv("MicrosoftAppType", "")
APP_TENANT   = os.getenv("MicrosoftAppTenantId", "")
PORT         = int(os.getenv("PORT", "3978"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - kyobo-dts-bot - %(levelname)s - %(message)s"
)
log = logging.getLogger("kyobo-dts-bot")
log.info(f"[Startup] AppType={APP_TYPE} Tenant={APP_TENANT} Listening on 0.0.0.0:{PORT}")

settings = BotFrameworkAdapterSettings(APP_ID, APP_PASSWORD)
if APP_TYPE and APP_TENANT:
    settings.channel_service = None
    settings.caller_id = None
adapter = BotFrameworkAdapter(settings)

async def on_error(context: TurnContext, error: Exception):
    log.exception("on_turn_error: %s", error)
    try:
        await context.send_activity("죄송해요. 내부 오류가 났어요.")
    except Exception:
        pass
adapter.on_turn_error = on_error

class EchoBot(ActivityHandler):
    async def on_message_activity(self, turn_context: TurnContext):
        text = turn_context.activity.text or ""
        await turn_context.send_activity(f"echo: {text}")

    async def on_members_added_activity(self, members_added, turn_context: TurnContext):
        await turn_context.send_activity("안녕하세요! 메시지를 보내보세요. 제가 똑같이 돌려드릴게요 :)")

bot = EchoBot()

routes = web.RouteTableDef()

@routes.get("/healthz")
async def healthz(_):
    return web.Response(text="ok")

@routes.post("/api/messages")
async def messages(request: web.Request):
    try:
        auth_header = request.headers.get("Authorization", "")
        body = await request.json()
        activity = Activity().deserialize(body)
        await adapter.process_activity(activity, auth_header, bot.on_turn)
        return web.Response(status=200)
    except PermissionError as e:
        log.warning("Unauthorized: %s", e)
        return web.Response(status=401, text="unauthorized")
    except Exception as e:
        log.exception("Error handling request: %s", e)
        return web.Response(status=500, text="internal-error")

app = web.Application()
app.add_routes(routes)

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=PORT)

