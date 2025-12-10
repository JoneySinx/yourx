import asyncio
import uvloop
import logging
from hydrogram import Client, idle
from aiohttp import web
from config import Config
from plugins.web_server import routes

# Logging Setup
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

        # Web Server Setup
        app = web.Application()
        app.add_routes(routes)
        app['bot'] = self

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", Config.PORT)
        await site.start()
        
        logger.info(f"🚀 Web Server Running on Port {Config.PORT}")
        await idle()

    async def stop(self, *args):
        await super().stop()
        logger.info("❌ Bot Stopped.")

if __name__ == "__main__":
    # --- FINAL FIX IS HERE ---
    # 1. uvloop पालिसी सेट करें
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    
    # 2. नया लूप खुद बनाएं (get_event_loop हटा दिया)
    loop = asyncio.new_event_loop()
    
    # 3. इस लूप को सेट करें
    asyncio.set_event_loop(loop)
    
    # 4. अब बोट चलाएं
    bot = Bot()
    loop.run_until_complete(bot.start())
