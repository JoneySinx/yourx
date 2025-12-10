import asyncio
from hydrogram import Client, filters
from hydrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from config import Config
from database import db
from utils.cleaner import get_search_name
from utils.render import humanbytes

# टेम्परेरी मेमोरी (ताकि बोट याद रखे कि कौन सा चैनल इंडेक्स करना है)
INDEX_CACHE = {}

# --- STEP 1: जब आप चैनल से मैसेज फॉरवर्ड करें ---
@Client.on_message(filters.forwarded & filters.private & filters.user(Config.ADMINS))
async def handle_forward(bot, message):
    # चेक करें कि क्या यह चैनल से फॉरवर्ड किया गया है
    if not message.forward_from_chat:
        await message.reply("❌ यह किसी चैनल का मैसेज नहीं है।")
        return

    channel_id = message.forward_from_chat.id
    channel_title = message.forward_from_chat.title
    
    # चैनल ID को मेमोरी में सेव करें
    INDEX_CACHE[message.from_user.id] = {
        "channel_id": channel_id,
        "step": "confirm"
    }

    text = f"""
📢 **Channel Detected!**

**Title:** {channel_title}
**ID:** `{channel_id}`

क्या आप इस चैनल की सभी फाइलों को इंडेक्स करना चाहते हैं?
"""
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Yes, Index It", callback_data="index_yes")],
        [InlineKeyboardButton("❌ No, Cancel", callback_data="index_cancel")]
    ])

    await message.reply_text(text, reply_markup=buttons, quote=True)

# --- STEP 2: YES बटन दबाने पर (SKIP पूछना) ---
@Client.on_callback_query(filters.regex("^index_"))
async def handle_index_buttons(bot, query):
    action = query.data.split("_")[1]
    user_id = query.from_user.id

    if action == "cancel":
        if user_id in INDEX_CACHE:
            del INDEX_CACHE[user_id]
        await query.edit_message_text("❌ Process Cancelled.")
        return

    if action == "yes":
        # स्टेप अपडेट करें
        if user_id in INDEX_CACHE:
            INDEX_CACHE[user_id]["step"] = "waiting_skip"
            
            await query.edit_message_text(
                "🔢 **Skip Messages?**\n\n"
                "अगर आप शुरू की कुछ फाइलों को छोड़ना चाहते हैं, तो नंबर लिखें (जैसे 100)।\n"
                "अगर शुरू से सब कुछ इंडेक्स करना है, तो **0** लिखें।\n\n"
                "👇 **अपना जवाब नीचे लिखें:**"
            )

# --- STEP 3: नंबर (0) भेजने पर इंडेक्सिंग स्टार्ट ---
@Client.on_message(filters.text & filters.private & filters.user(Config.ADMINS))
async def start_batch_indexing(bot, message):
    user_id = message.from_user.id
    
    # चेक करें कि क्या हम यूजर के जवाब का इंतज़ार कर रहे हैं
    if user_id not in INDEX_CACHE or INDEX_CACHE[user_id]["step"] != "waiting_skip":
        return

    # यूजर का इनपुट (Skip Number)
    try:
        skip_count = int(message.text)
    except ValueError:
        await message.reply("❌ कृपया सिर्फ नंबर भेजें (Example: 0)")
        return

    channel_id = INDEX_CACHE[user_id]["channel_id"]
    del INDEX_CACHE[user_id] # मेमोरी क्लियर करें

    status_msg = await message.reply_text(
        f"⏳ **Indexing Started!**\n\n"
        f"Channel: `{channel_id}`\n"
        f"Skipping: {skip_count}\n\n"
        "🚀 बोट बैकग्राउंड में काम कर रहा है..."
    )

    # --- MAIN LOOP (Indexing Logic) ---
    total = 0
    errors = 0
    duplicate = 0
    
    try:
        # चैनल की हिस्ट्री निकालें (Hydrogram Magic)
        async for msg in bot.get_chat_history(chat_id=channel_id, skip=skip_count):
            
            # सिर्फ वीडियो या डाक्यूमेंट्स उठाएं
            if msg.document or msg.video:
                media = msg.document or msg.video
                
                # --- SMART CAPTION LOGIC (जो हमने index.py में लगाया था) ---
                raw_text = ""
                if Config.CAPTION_MODE == "FULL":
                    raw_text = (msg.caption or "") + " " + (media.file_name or "")
                else:
                    if msg.caption and len(msg.caption) > 5:
                        raw_text = msg.caption.split('\n')[0]
                    else:
                        raw_text = media.file_name or "Unknown"

                search_name = get_search_name(raw_text)
                
                if search_name:
                    file_data = {
                        "unique_id": media.file_unique_id,
                        "file_id": media.file_id,
                        "file_name": media.file_name,
                        "search_name": search_name,
                        "file_size": humanbytes(media.file_size),
                        "caption": msg.caption or ""
                    }
                    
                    status = await db.save_file(file_data)
                    if status == "saved":
                        total += 1
                    elif status == "duplicate":
                        duplicate += 1
                else:
                    errors += 1

            # हर 20 फाइल के बाद मैसेज एडिट करें (ताकि पता चले बोट जिंदा है)
            if total % 20 == 0:
                try:
                    await status_msg.edit_text(
                        f"🔄 **Indexing in Progress...**\n\n"
                        f"✅ Saved: {total}\n"
                        f"♻️ Duplicates: {duplicate}\n"
                        f"⚠️ Errors: {errors}"
                    )
                except:
                    pass

        await status_msg.edit_text(
            f"✅ **Indexing Completed!**\n\n"
            f"📂 Total Saved: {total}\n"
            f"♻️ Duplicates Skipped: {duplicate}\n"
            f"⚠️ Errors: {errors}"
        )

    except Exception as e:
        await status_msg.edit_text(f"❌ Error: {e}")
