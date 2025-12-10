import asyncio
import uvloop
import logging
from hydrogram import Client, idle
from aiohttp import web
from config import Config
from plugins.web_server import routes

# 1. UVLOOP Setup (सबसे पहले इसे सेट करें)
uvloop.install()

# 2. Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class Bot(Client):
    def __init__(self):
        super().__init__(
            "PremiumBot",
            api_id=Config.API_ID,
            api_hash=Config.API_HASH,
            bot_token=Config.BOT_TOKEN,
            plugins=dict(root="plugins"),
            workers=50
        )

    async def start(self):
        await super().start()
        me = await self.get_me()
        self.username = me.username
        logger.info(f"✅ Bot Started as @{me.username}")

        # --- WEB SERVER SETUP ---
        app = web.Application()
        app.add_routes(routes)
        app['bot'] = self

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", Config.PORT)
        await site.start()
        
        logger.info(f"🚀 Web Server Running on Port {Config.PORT}")

        # बोट को रोके रखने के लिए (Idle Mode)
        await idle()

    async def stop(self, *args):
        await super().stop()
        logger.info("❌ Bot Stopped.")

if __name__ == "__main__":
    # 3. Explicit Loop Creation (यह लाइन आपका एरर फिक्स करेगी)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    bot = Bot()
    loop.run_until_complete(bot.start())
