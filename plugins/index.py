import re
from hydrogram import Client, filters
from config import Config
from database import db
from utils.cleaner import get_search_name
from utils.render import humanbytes

# सिर्फ एडमिन फाइल्स ऐड कर सकता है (Security)
@Client.on_message(filters.private & (filters.document | filters.video) & filters.user(Config.ADMINS))
async def index_files(bot, message):
    """
    जब एडमिन बोट को फाइल फॉरवर्ड करेगा, तो यह सेव हो जाएगी।
    """
    media = message.document or message.video
    
    # --- SMART CAPTION LOGIC (Your Idea) ---
    raw_text = ""

    if Config.CAPTION_MODE == "FULL":
        # तरीका 1: सब कुछ (Caption + Filename)
        raw_text = (message.caption or "") + " " + (media.file_name or "")
        
    else: # SMART Mode (Default)
        # तरीका 2: स्मार्ट सिलेक्शन (Priority Logic)
        if message.caption and len(message.caption) > 5:
            # कैप्शन की सिर्फ पहली लाइन उठाओ (अक्सर नाम यहीं होता है)
            raw_text = message.caption.split('\n')[0]
        else:
            # अगर कैप्शन नहीं है, तो फाइल नाम लो
            raw_text = media.file_name or "Unknown File"

    # --- CLEANING ---
    # अब इस raw_text को हमारे Regex Cleaner से साफ़ करो
    search_name = get_search_name(raw_text)
    
    if not search_name:
        await message.reply_text("❌ Error: Could not extract a valid name from this file.")
        return

    # --- SAVING TO DB ---
    file_data = {
        "unique_id": media.file_unique_id, # डुप्लीकेट रोकने के लिए
        "file_id": media.file_id,          # यूजर को भेजने के लिए
        "file_name": media.file_name,      # ओरिजिनल नाम (दिखाने के लिए)
        "search_name": search_name,        # सर्च करने के लिए (Cleaned)
        "file_size": humanbytes(media.file_size),
        "caption": message.caption or ""   # ओरिजिनल कैप्शन सेव रखें
    }

    status = await db.save_file(file_data)

    if status == "saved":
        await message.reply_text(
            f"✅ **Saved Successfully!**\n\n"
            f"📂 **Original:** `{media.file_name}`\n"
            f"🔍 **Search Name:** `{search_name}`\n"
            f"⚙️ **Mode:** {Config.CAPTION_MODE}"
        )
    elif status == "duplicate":
        await message.reply_text(f"⚠️ **Duplicate:** This file is already in database.")
    else:
        await message.reply_text("❌ **Error:** Database error.")
