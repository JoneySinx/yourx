import asyncio
from hydrogram import Client, filters
from hydrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from config import Config
from database import db
from utils.cleaner import get_search_name
from utils.render import humanbytes

INDEX_CACHE = {}

@Client.on_message(filters.forwarded & filters.private & filters.user(Config.ADMINS))
async def handle_forward(bot, message):
    if not message.forward_from_chat:
        await message.reply("❌ यह किसी चैनल का मैसेज नहीं है।")
        return

    # Cache में सेव करें
    INDEX_CACHE[message.from_user.id] = {
        "channel_id": message.forward_from_chat.id,
        "step": "confirm"
    }

    await message.reply_text(
        f"📢 **Channel Detected!**\nTitle: {message.forward_from_chat.title}\n\nIndex करना है?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Yes", callback_data="index_yes"),
             InlineKeyboardButton("❌ No", callback_data="index_cancel")]
        ]),
        quote=True
    )

@Client.on_callback_query(filters.regex("^index_"))
async def handle_buttons(bot, query):
    action = query.data.split("_")[1]
    user_id = query.from_user.id

    if action == "cancel":
        if user_id in INDEX_CACHE: del INDEX_CACHE[user_id]
        await query.edit_message_text("❌ Cancelled.")
        return

    if action == "yes":
        if user_id in INDEX_CACHE:
            INDEX_CACHE[user_id]["step"] = "waiting_skip"
            await query.edit_message_text("🔢 **Skip?**\nकितनी पुरानी फाइलें छोड़नी हैं? (जैसे 0 या 100) लिखें।")

@Client.on_message(filters.text & filters.private & filters.user(Config.ADMINS))
async def start_batch(bot, message):
    user_id = message.from_user.id
    if user_id not in INDEX_CACHE or INDEX_CACHE[user_id]["step"] != "waiting_skip":
        return

    try:
        skip_count = int(message.text)
    except:
        await message.reply("❌ सिर्फ नंबर लिखें (0).")
        return

    channel_id = INDEX_CACHE[user_id]["channel_id"]
    del INDEX_CACHE[user_id]

    status_msg = await message.reply_text(f"⏳ **Indexing...**\nSkipping First: {skip_count}")

    total = 0
    current_count = 0 
    
    try:
        # --- FIX: Loop Logic (No 'skip' parameter error) ---
        async for msg in bot.get_chat_history(channel_id):
            # 1. Skip Logic
            if current_count < skip_count:
                current_count += 1
                continue
            
            # 2. Index Logic
            if msg.document or msg.video:
                media = msg.document or msg.video
                
                # Smart Caption
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
                    if await db.save_file(file_data) == "saved":
                        total += 1

            # Update Status every 20 files
            if total % 20 == 0:
                try: await status_msg.edit_text(f"🔄 Saved: {total}")
                except: pass
                
        await status_msg.edit_text(f"✅ **Done!** Total Saved: {total}")

    except Exception as e:
        await status_msg.edit_text(f"❌ Error: {e}")
