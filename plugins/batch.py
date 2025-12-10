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

    channel_id = message.forward_from_chat.id
    channel_title = message.forward_from_chat.title
    
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
        if user_id in INDEX_CACHE:
            INDEX_CACHE[user_id]["step"] = "waiting_skip"
            await query.edit_message_text(
                "🔢 **Skip Messages?**\n\n"
                "शुरू की कितनी फाइलें छोड़नी हैं? (जैसे 100)\n"
                "अगर सब इंडेक्स करना है तो **0** लिखें।"
            )

@Client.on_message(filters.text & filters.private & filters.user(Config.ADMINS))
async def start_batch_indexing(bot, message):
    user_id = message.from_user.id
    if user_id not in INDEX_CACHE or INDEX_CACHE[user_id]["step"] != "waiting_skip":
        return

    try:
        skip_count = int(message.text)
    except ValueError:
        await message.reply("❌ नंबर लिखें (Example: 0)")
        return

    channel_id = INDEX_CACHE[user_id]["channel_id"]
    del INDEX_CACHE[user_id]

    status_msg = await message.reply_text(f"⏳ **Indexing Started!**\nSkipping: {skip_count}\n🚀 Working...")

    total = 0
    errors = 0
    duplicate = 0
    
    try:
        # FIX: 'skip' की जगह 'offset' का उपयोग करें
        async for msg in bot.get_chat_history(chat_id=channel_id, offset=skip_count):
            if msg.document or msg.video:
                media = msg.document or msg.video
                
                # Smart Caption Logic
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

            if total % 20 == 0:
                try:
                    await status_msg.edit_text(f"🔄 Indexing...\n✅ Saved: {total}\n♻️ Duplicates: {duplicate}")
                except:
                    pass

        await status_msg.edit_text(f"✅ **Done!**\nTotal Saved: {total}\nDuplicates: {duplicate}")

    except Exception as e:
        await status_msg.edit_text(f"❌ Error: {e}")
