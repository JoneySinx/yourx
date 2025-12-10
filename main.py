import logging
import logging.config
from hydrogram import Client, idle
from aiohttp import web
from config import Config
from utils.render import start_server  # यह हम बाद में बनाएंगे, अभी एरर न आए इसलिए नीचे डमी है

# 1. Logging Setup (ताकि पता चले बोट क्या कर रहा है)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 2. Web Server Routes (Koyeb Health Check के लिए)
async def web_server():
    async def handle_home(request):
        return web.Response(text="Premium Bot is Running! 🚀")

    app = web.Application()
    app.router.add_get('/', handle_home)
    return app

class Bot(Client):
    def __init__(self):
        super().__init__(
            "PremiumBot",
            api_id=Config.API_ID,
            api_hash=Config.API_HASH,
            bot_token=Config.BOT_TOKEN,
            plugins=dict(root="plugins"), # यह लाइन plugins फोल्डर को लोड करती है
            workers=50,
            sleep_threshold=10
        )

    async def start(self):
        # पहले बोट स्टार्ट करो
        await super().start()
        me = await self.get_me()
        self.username = me.username
        logger.info(f"✅ Bot Started as @{me.username}")
        logger.info("✅ Admin Panel & Premium System Loaded.")

        # अब वेब सर्वर स्टार्ट करो (Streaming & Health Check)
        app = web.AppRunner(await web_server())
        await app.setup()
        site = web.TCPSite(app, "0.0.0.0", Config.PORT)
        await site.start()
        logger.info(f"🚀 Web Server running on Port {Config.PORT}")

    async def stop(self, *args):
        await super().stop()
        logger.info("❌ Bot Stopped.")

# 3. Execution (Single Loop)
if __name__ == "__main__":
    bot = Bot()
    bot.run()
