import asyncio
import time
from hydrogram import Client, filters, enums
from hydrogram.errors import FloodWait
from hydrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from config import Config
from database import db
from utils.cleaner import get_search_name
from utils.render import humanbytes, get_time

# इंडेक्सिंग प्रोसेस को कंट्रोल करने के लिए
INDEX_CACHE = {}
CANCEL_INDEX = {}
LOCK = asyncio.Lock()

# --- 1. Custom Iterator (The Logic You Wanted) ---
async def iter_messages(bot, chat_id, start_id, end_id):
    """
    यह फंक्शन 1-1 करके मैसेज नहीं लाता, बल्कि 200 IDs का एक लिस्ट बनाता है
    और एक बार में 200 मैसेज उठाता है। (Super Fast)
    """
    current = start_id
    while current < end_id:
        # 200 का बैच या बचा हुआ हिस्सा
        batch_size = min(200, end_id - current)
        if batch_size <= 0:
            return
            
        # IDs की लिस्ट बनाना (Example: [100, 101, 102 ... 300])
        batch_ids = list(range(current, current + batch_size))
        
        try:
            messages = await bot.get_messages(chat_id, batch_ids)
            for message in messages:
                if message:
                    yield message
        except FloodWait as e:
            await asyncio.sleep(e.value)
        except Exception as e:
            print(f"Skipped Batch {current}: {e}")
            pass
            
        current += 200

# --- 2. Handle Forward (Capture Last ID) ---
@Client.on_message(filters.forwarded & filters.private & filters.user(Config.ADMINS))
async def handle_forward(bot, message):
    if LOCK.locked():
        await message.reply("⚠️ Wait! एक प्रोसेस पहले से चल रहा है।")
        return

    # चेक करें कि क्या यह चैनल है
    if not message.forward_from_chat or message.forward_from_chat.type != enums.ChatType.CHANNEL:
        await message.reply("❌ यह चैनल का मैसेज नहीं है। कृपया चैनल से फॉरवर्ड करें।")
        return

    # डेटा निकालें
    target_chat_id = message.forward_from_chat.id
    target_chat_title = message.forward_from_chat.title
    last_msg_id = message.forward_from_message_id # यह हमारा End Point है

    # Cache में सेव करें
    INDEX_CACHE[message.from_user.id] = {
        "chat_id": target_chat_id,
        "title": target_chat_title,
        "last_id": last_msg_id,
        "step": "waiting_skip"
    }

    await message.reply_text(
        f"📢 **Channel Detected:** `{target_chat_title}`\n"
        f"🔢 **Last Message ID:** `{last_msg_id}`\n\n"
        "👇 **Skip Number बताएं:**\n"
        "इंडेक्सिंग कहाँ से शुरू करनी है? (जैसे 0 या 100)।\n"
        "कृपया नंबर लिखकर भेजें।"
    )

# --- 3. Start Indexing (After Skip Input) ---
@Client.on_message(filters.text & filters.private & filters.user(Config.ADMINS))
async def start_indexing(bot, message):
    user_id = message.from_user.id
    
    # अगर यूजर इंडेक्सिंग मोड में नहीं है तो इग्नोर करें
    if user_id not in INDEX_CACHE or INDEX_CACHE[user_id]["step"] != "waiting_skip":
        return

    try:
        skip_number = int(message.text)
    except ValueError:
        await message.reply("❌ कृपया सिर्फ नंबर भेजें (Example: 0)")
        return

    # डेटा वापस निकालें
    data = INDEX_CACHE[user_id]
    chat_id = data["chat_id"]
    chat_title = data["title"]
    last_id = data["last_id"]
    
    # Cache साफ़ करें और Cancel Flag सेट करें
    del INDEX_CACHE[user_id]
    CANCEL_INDEX[chat_id] = False

    # Status Message
    status_msg = await message.reply_text(
        f"🚀 **Indexing Started!**\n\n"
        f"📺 Channel: `{chat_title}`\n"
        f"🔢 Range: `{skip_number}` to `{last_id}`\n\n"
        "⏳ Processing...",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ CANCEL", callback_data=f"cancel_index_{chat_id}")]
        ])
    )

    # --- MAIN LOGIC ---
    async with LOCK:
        start_time = time.time()
        total_files = 0
        duplicate = 0
        errors = 0
        
        try:
            # हमारे Custom Iterator का उपयोग (Smart Way)
            async for msg in iter_messages(bot, chat_id, skip_number, last_id):
                
                # अगर Cancel बटन दबाया गया
                if CANCEL_INDEX.get(chat_id, False):
                    await status_msg.edit(f"🛑 **Indexing Cancelled!**\nSaved: {total_files}")
                    return

                # सिर्फ मीडिया फाइल्स
                if msg.document or msg.video:
                    media = msg.document or msg.video
                    
                    # Caption Logic
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
                        
                        sts = await db.save_file(file_data)
                        if sts == 'saved':
                            total_files += 1
                        elif sts == 'duplicate':
                            duplicate += 1
                        else:
                            errors += 1
                
                # हर 100 मैसेज के बाद अपडेट (ताकि FloodWait न लगे)
                if (msg.id - skip_number) % 100 == 0:
                    try:
                        time_taken = get_time(time.time() - start_time)
                        await status_msg.edit(
                            f"🔄 **Indexing...**\n"
                            f"📍 Current ID: `{msg.id}` / `{last_id}`\n"
                            f"✅ Saved: `{total_files}`\n"
                            f"♻️ Duplicates: `{duplicate}`\n"
                            f"⏱ Time: {time_taken}",
                            reply_markup=InlineKeyboardMarkup([
                                [InlineKeyboardButton("❌ CANCEL", callback_data=f"cancel_index_{chat_id}")]
                            ])
                        )
                    except Exception:
                        pass

        except Exception as e:
            await status_msg.edit(f"❌ Error: {e}")
            print(f"Indexing Error: {e}")

        # Final Message
        time_taken = get_time(time.time() - start_time)
        await status_msg.edit(
            f"✅ **Indexing Completed!**\n\n"
            f"📂 Total Saved: `{total_files}`\n"
            f"♻️ Duplicates: `{duplicate}`\n"
            f"⏱ Duration: {time_taken}"
        )

# --- 4. Cancel Button Handler ---
@Client.on_callback_query(filters.regex(r"^cancel_index_"))
async def cancel_indexing(bot, query):
    chat_id = int(query.data.split("_")[2])
    CANCEL_INDEX[chat_id] = True
    await query.answer("🛑 Cancelling Process...", show_alert=True)
