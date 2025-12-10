import base64
from hydrogram import Client, filters
from hydrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from config import Config
from database import db
from utils.render import humanbytes

# --- 1. VIEW FILE HANDLER (File Details) ---
@Client.on_callback_query(filters.regex(r"^view_"))
async def view_file_handler(bot, query: CallbackQuery):
    """
    जब यूजर सर्च लिस्ट में किसी फाइल पर क्लिक करता है।
    Data: view_{file_id}
    """
    _, file_id = query.data.split("_", 1)
    
    # डेटाबेस से फाइल लाओ
    file = await db.get_file(file_id)
    if not file:
        await query.answer("❌ File not found or deleted.", show_alert=True)
        return

    # कैप्शन तैयार करना (VIP Style)
    caption = Config.FILE_CAPTION.format(
        file_name=file['file_name'],
        file_size=file['file_size'],
        date="Recently Added"
    )

    # बटन: सिर्फ "Generate Link" (सर्वर लोड बचाने के लिए)
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 Generate Download & Stream Link", callback_data=f"gen_{file['_id']}")],
        [InlineKeyboardButton("⬅️ Back to Search", callback_data="delete_msg")]
    ])

    # पुराने मैसेज को एडिट करो (फोटो/थंबनेल के बिना, सिर्फ टेक्स्ट)
    await query.edit_message_text(
        text=caption,
        reply_markup=buttons,
        disable_web_page_preview=True
    )

# --- 2. GENERATE LINK HANDLER (The Magic) ---
@Client.on_callback_query(filters.regex(r"^gen_"))
async def generate_link_handler(bot, query: CallbackQuery):
    """
    जब यूजर 'Generate Link' दबाता है।
    यह फाइल को Bin Channel में भेजकर लिंक बनाता है।
    """
    _, file_id = query.data.split("_", 1)
    
    file = await db.get_file(file_id)
    if not file:
        await query.answer("File missing.", show_alert=True)
        return

    # यूजर को इंतज़ार करवाओ
    await query.answer("🔄 Generating Secure Link...", show_alert=False)

    try:
        # A. फाइल को चुपके से Bin Channel में भेजो (Log Channel)
        # नोट: हमें db से 'file_id' मिली है, इसे Bin Channel में भेजना है
        log_msg = await bot.send_cached_media(
            chat_id=Config.BIN_CHANNEL,
            file_id=file['file_id'],
            caption=f"Requested by: {query.from_user.mention} [{query.from_user.id}]"
        )
        
        # B. Unique Hash बनाना (Message ID को Encrypt करना)
        # हम Bin Channel की Message ID को कोड में बदल देंगे
        stream_hash = encode_string(f"{log_msg.id}")
        
        # C. लिंक्स तैयार करना
        stream_link = f"{Config.URL}watch/{stream_hash}"
        download_link = f"{Config.URL}download/{stream_hash}"

        # D. फाइनल बटन दिखाना
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🚀 Fast Download", url=download_link)],
            [InlineKeyboardButton("▶️ Stream Online", url=stream_link)],
            [InlineKeyboardButton("📂 Save to Playlist", callback_data="save_playlist")] # Optional
        ])
        
        await query.edit_message_reply_markup(reply_markup=buttons)
        
    except Exception as e:
        print(f"Link Gen Error: {e}")
        await query.answer("❌ Error generating link. Contact Admin.", show_alert=True)

# --- HELPER: Encoding Logic (URL Safe) ---
def encode_string(string):
    """Message ID को URL Safe String में बदलता है"""
    string_bytes = string.encode("ascii")
    base64_bytes = base64.urlsafe_b64encode(string_bytes)
    return base64_bytes.decode("ascii").rstrip("=")

@Client.on_callback_query(filters.regex("^delete_msg"))
async def delete_msg(bot, query):
    await query.message.delete()
