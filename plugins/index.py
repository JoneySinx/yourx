import re
from hydrogram import Client, filters
from hydrogram.enums import ChatType
from config import Config
from database import db
from utils.cleaner import get_search_name
from utils.render import humanbytes

# Filter: Private (Admin Only) OR Channel (New Posts)
@Client.on_message((filters.private | filters.channel) & (filters.document | filters.video))
async def index_files(bot, message):
    """
    1. Private: जब एडमिन फाइल भेजे।
    2. Channel: जब चैनल में नई पोस्ट आए (Auto Index).
    """

    # --- 1. SECURITY CHECKS ---
    
    # अगर यह Bin Channel या Log Channel है, तो इग्नोर करें (Loop से बचने के लिए)
    if message.chat.id == Config.BIN_CHANNEL or message.chat.id == Config.LOG_CHANNEL:
        return

    # अगर प्राइवेट मैसेज है, तो चेक करें कि भेजने वाला Admin है या नहीं
    if message.chat.type == ChatType.PRIVATE:
        if message.from_user.id not in Config.ADMINS:
            return  # अगर एडमिन नहीं है, तो कुछ मत करो

    # --- 2. DATA EXTRACTION ---
    media = message.document or message.video
    
    # --- SMART CAPTION LOGIC ---
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

    # --- 3. CLEANING ---
    # अब इस raw_text को हमारे Regex Cleaner से साफ़ करो
    search_name = get_search_name(raw_text)
    
    if not search_name:
        if message.chat.type == ChatType.PRIVATE:
            await message.reply_text("❌ Error: Could not extract a valid name from this file.")
        return

    # --- 4. SAVING TO DB ---
    file_data = {
        "unique_id": media.file_unique_id, # डुप्लीकेट रोकने के लिए
        "file_id": media.file_id,          # यूजर को भेजने के लिए
        "file_name": media.file_name or search_name, # ओरिजिनल नाम
        "search_name": search_name,        # सर्च करने के लिए (Cleaned)
        "file_size": humanbytes(media.file_size),
        "caption": message.caption or ""   # ओरिजिनल कैप्शन सेव रखें
    }

    status = await db.save_file(file_data)

    # --- 5. FEEDBACK (REPLY) ---
    
    # अगर प्राइवेट मैसेज है, तो रिप्लाई करो
    if message.chat.type == ChatType.PRIVATE:
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
            
    # अगर चैनल है, तो सिर्फ रिएक्शन दो (ताकि चैनल स्पैम न हो)
    else:
        if status == "saved":
            try:
                await message.react("🔥") # सेव होने पर आग का रिएक्शन
            except:
                pass
