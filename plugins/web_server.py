import time
import base64
import re
from aiohttp import web
from hydrogram import Client
from config import Config

routes = web.RouteTableDef()

@routes.get("/", allow_head=True)
async def root_route_handler(request):
    return web.json_response({"status": "running"})

@routes.get("/watch/{hash}")
async def stream_handler(request):
    return await media_streamer(request, download=False)

@routes.get("/download/{hash}")
async def download_handler(request):
    return await media_streamer(request, download=True)

async def media_streamer(request, download=False):
    secure_hash = request.match_info['hash']
    
    try:
        # Hash Decode Fix
        secure_hash = secure_hash + "=" * (-len(secure_hash) % 4)
        msg_id = int(base64.urlsafe_b64decode(secure_hash).decode("ascii"))
    except:
        return web.Response(text="Invalid Link", status=400)

    bot: Client = request.app['bot']
    try:
        message = await bot.get_messages(Config.BIN_CHANNEL, msg_id)
        if not message or not message.media:
            return web.Response(text="File Missing", status=404)
    except:
        return web.Response(text="File Error", status=404)

    file_media = getattr(message, message.media.value)
    original_name = file_media.file_name or "Video.mp4"
    
    # FIX: फाइल नाम से स्पेशल कैरेक्टर (|, :, <, >) हटाना जरूरी है
    file_name = re.sub(r'[\\/*?:"<>|]', "", original_name)
    
    file_size = file_media.file_size
    mime_type = getattr(file_media, "mime_type", "video/mp4")

    # Headers for Streaming
    headers = {
        "Content-Disposition": f'inline; filename="{file_name}"',
        "Content-Type": mime_type,
        "Accept-Ranges": "bytes",
        "Content-Length": str(file_size)
    }

    # Range Handling (Seeking)
    offset = 0
    length = file_size
    status_code = 200

    range_header = request.headers.get("Range")
    if range_header:
        try:
            start_str, end_str = range_header.replace("bytes=", "").split("-")
            start = int(start_str)
            end = int(end_str) if end_str else file_size - 1
            
            offset = start
            length = end - start + 1
            status_code = 206
            
            headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
            headers["Content-Length"] = str(length)
        except ValueError:
            pass

    response = web.StreamResponse(status=status_code, headers=headers)
    await response.prepare(request)

    try:
        async for chunk in bot.stream_media(message, offset=offset, limit=length):
            await response.write(chunk)
    except:
        pass

    return response
