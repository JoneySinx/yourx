import time
import math
import logging
import secrets
from aiohttp import web
from hydrogram import Client, errors
from config import Config
from utils.render import humanbytes
from database import db

routes = web.RouteTableDef()

@routes.get("/", allow_head=True)
async def root_route_handler(request):
    return web.json_response({"status": "running", "maintainer": "PremiumBot"})

@routes.get("/watch/{hash}")
async def stream_handler(request):
    return await media_streamer(request, download=False)

@routes.get("/download/{hash}")
async def download_handler(request):
    return await media_streamer(request, download=True)

# --- CORE STREAMING LOGIC ---
async def media_streamer(request, download=False):
    # 1. Hash से Message ID निकालना
    secure_hash = request.match_info['hash']
    try:
        # Base64 Decode logic (stream.py का उल्टा)
        import base64
        msg_id = int(base64.urlsafe_b64decode(secure_hash + "=" * (-len(secure_hash) % 4)).decode("ascii"))
    except:
        return web.Response(text="Invalid Link", status=400)

    # 2. बोट ऑब्जेक्ट प्राप्त करना (Main.py से पास किया गया)
    bot: Client = request.app['bot']

    # 3. Bin Channel से फाइल ढूँढना
    try:
        message = await bot.get_messages(Config.BIN_CHANNEL, msg_id)
        if not message or not message.media:
            return web.Response(text="File not found in Bin Channel", status=404)
    except Exception as e:
        return web.Response(text=f"Error: {e}", status=404)

    # 4. फाइल की जानकारी
    file_media = getattr(message, message.media.value)
    file_name = file_media.file_name or "Premium_Video.mp4"
    file_size = file_media.file_size
    mime_type = getattr(file_media, "mime_type", "video/mp4")

    # 5. Headers सेट करना (Browser को बताने के लिए)
    headers = {
        "Content-Disposition": f'{("attachment" if download else "inline")}; filename="{file_name}"',
        "Content-Type": mime_type,
        "Content-Length": str(file_size),
    }

    # 6. रेंज हैंडलिंग (Video Seeking के लिए - Play/Pause/Forward)
    # यह थोड़ा एडवांस है, लेकिन वीडियो को अटकने से बचाता है
    offset = 0
    range_header = request.headers.get("Range")
    
    if range_header:
        from_bytes, until_bytes = range_header.replace("bytes=", "").split("-")
        from_bytes = int(from_bytes)
        until_bytes = int(until_bytes) if until_bytes else file_size - 1
        
        headers["Content-Range"] = f"bytes {from_bytes}-{until_bytes}/{file_size}"
        headers["Content-Length"] = str(until_bytes - from_bytes + 1)
        headers["Accept-Ranges"] = "bytes"
        offset = from_bytes
        status_code = 206 # Partial Content
    else:
        status_code = 200

    # 7. रिस्पॉन्स शुरू करना
    response = web.StreamResponse(status=status_code, headers=headers)
    await response.prepare(request)

    # 8. असली जादू: Telegram से Browser तक सीधे स्ट्रीम (No Download on Server)
    try:
        # Hydrogram का stream_media फंक्शन यूज करेंगे
        async for chunk in bot.stream_media(message, offset=offset, limit=file_size-offset):
            await response.write(chunk)
    except Exception as e:
        # अगर यूजर बीच में बंद कर दे
        pass

    return response
