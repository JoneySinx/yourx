import re
from hydrogram import Client, filters
from config import Config
from database import db
from utils.cleaner import get_search_name
from utils.render import humanbytes

# FIX: सिर्फ तभी सेव करें जब 'batch' कमांड चल रहा हो या एडमिन 'save' मोड में हो
# अभी के लिए हम ऑटो-सेव बंद कर रहे हैं। फाइल सेव करने के लिए एडमिन को /index कमांड के साथ रिप्लाई करना होगा या Batch Mode यूज़ करना होगा।

# 1. Manual Indexing (Reply with /index)
@Client.on_message(filters.command("index") & filters.private & filters.user(Config.ADMINS) & filters.reply)
async def manual_index(bot, message):
    reply = message.reply_to_message
    if not (reply.document or reply.video):
        await message.reply("❌ यह वीडियो या फाइल नहीं है।")
        return
        
    media = reply.document or reply.video
    
    # --- Indexing Logic ---
    raw_text = (reply.caption or "") + " " + (media.file_name or "")
    search_name = get_search_name(raw_text)
    
    file_data = {
        "unique_id": media.file_unique_id,
        "file_id": media.file_id,
        "file_name": media.file_name,
        "search_name": search_name,
        "file_size": humanbytes(media.file_size),
        "caption": reply.caption or ""
    }
    
    status = await db.save_file(file_data)
    await message.reply(f"✅ Status: **{status}**\nName: `{search_name}`")

# नोट: पुराना ऑटो-सेव फंक्शन हटा दिया गया है ताकि PM में कचरा जमा न हो।
