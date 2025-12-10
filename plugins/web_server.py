import time
import math
import logging
import base64
from aiohttp import web
from hydrogram import Client, errors
from config import Config
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

async def media_streamer(request, download=False):
    secure_hash = request.match_info['hash']
    
    # 1. Hash Decode Fix (Padding Error Handle)
    try:
        secure_hash = secure_hash + "=" * (-len(secure_hash) % 4)
        msg_id = int(base64.urlsafe_b64decode(secure_hash).decode("ascii"))
    except Exception as e:
        return web.Response(text=f"Invalid Link Hash: {e}", status=400)

    # 2. Bot Instance Get
    bot: Client = request.app['bot']

    # 3. Get File from BIN Channel
    try:
        message = await bot.get_messages(Config.BIN_CHANNEL, msg_id)
        if not message or not message.media:
            return web.Response(text="File not found in Bin Channel (Deleted?)", status=404)
    except Exception as e:
        return web.Response(text=f"Error fetching file: {e}", status=404)

    # 4. File Details
    file_media = getattr(message, message.media.value)
    file_name = file_media.file_name or "Premium_Video.mp4"
    file_size = file_media.file_size
    mime_type = getattr(file_media, "mime_type", "video/mp4")

    # 5. Range Handling (Important for Video Player Seeking)
    headers = {
        "Content-Disposition": f'{("attachment" if download else "inline")}; filename="{file_name}"',
        "Content-Type": mime_type,
        "Accept-Ranges": "bytes",
    }

    offset = 0
    length = file_size
    status_code = 200

    range_header = request.headers.get("Range")
    if range_header:
        try:
            start_str, end_str = range_header.replace("bytes=", "").split("-")
            start = int(start_str)
            # अगर end नहीं दिया है तो फाइल का अंत
            end = int(end_str) if end_str else file_size - 1
            
            offset = start
            length = end - start + 1
            status_code = 206
            
            headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
            headers["Content-Length"] = str(length)
        except ValueError:
            pass
    else:
        headers["Content-Length"] = str(file_size)

    # 6. Stream Response
    response = web.StreamResponse(status=status_code, headers=headers)
    await response.prepare(request)

    try:
        # Hydrogram Streaming Generator
        async for chunk in bot.stream_media(message, offset=offset, limit=length):
            await response.write(chunk)
    except Exception:
        pass

    return response
