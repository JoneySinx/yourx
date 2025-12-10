from hydrogram import Client, filters
from hydrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from config import Config
from database import db

# --- 1. SEARCH HANDLER (TEXT INPUT) ---
@Client.on_message(filters.text & filters.private)
async def search_handler(bot, message):
    """
    जब यूजर कोई टेक्स्ट (मूवी का नाम) भेजेगा, यह फंक्शन चलेगा।
    """
    user_id = message.from_user.id
    query = message.text.strip()
    
    # कमांड्स को इग्नोर करें (जैसे /start, /help)
    if query.startswith("/"):
        return

    # A. प्रीमियम चेक (Security)
    if not await db.is_user_premium(user_id):
        await message.reply_text(
            "🔒 **Premium Only!**\n\n"
            "Search feature is only for Premium members.\n"
            "Please buy a plan to access 90,000+ Files.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💎 Buy Premium", callback_data="buy_premium")]
            ])
        )
        return

    # B. डेटाबेस सर्च (Hybrid Regex)
    m = await message.reply_text("🔍 **Searching...**")
    files = await db.search_files(query)

    if not files:
        # अगर कोई फाइल नहीं मिली (Request Feature)
        await m.edit_text(
            f"❌ **No Results Found for:** `{query}`\n\n"
            "Check spelling or request this movie.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📝 Request to Admin", callback_data=f"request_{query}")]
            ])
        )
        return

    # C. रिजल्ट दिखाना (Pagination Logic)
    # पहली बार पेज 0 (शुरुआती 10 फाइलें) दिखाएंगे
    await send_search_results(m, files, query, offset=0)


# --- 2. PAGINATION HANDLER (NEXT/PREV BUTTONS) ---
@Client.on_callback_query(filters.regex(r"^spage_"))
async def search_pagination_handler(bot, query: CallbackQuery):
    """
    जब यूजर Next/Back बटन दबाएगा
    Data Format: spage_{offset}_{query}
    """
    _, offset, search_query = query.data.split("_", 2)
    offset = int(offset)
    
    # दोबारा सर्च करें (ताकि लिस्ट मिले)
    files = await db.search_files(search_query)
    
    if not files:
        await query.answer("Expired Search. Please search again.", show_alert=True)
        return

    # पेज अपडेट करें
    await send_search_results(query.message, files, search_query, offset)


# --- 3. HELPER FUNCTION (BUTTON MAKER) ---
async def send_search_results(message, files, query, offset):
    """
    फाइलों की लिस्ट को सुंदर बटनों में बदलकर भेजता है (10 Per Page)
    """
    # 10 फाइलें काटें (Slicing)
    results = files[offset : offset + 10]
    total_results = len(files)
    
    buttons = []
    
    # हर फाइल के लिए एक बटन (File Name + Size)
    for file in results:
        # बटन दबाने पर 'view_file_{id}' कॉल होगा (जो हम stream.py में हैंडल करेंगे)
        btn_text = f"📂 {file['file_name']} [{file['file_size']}]"
        buttons.append([InlineKeyboardButton(btn_text, callback_data=f"view_{file['_id']}")])

    # नेविगेशन बटन (Previous / Next)
    nav_buttons = []
    if offset >= 10:
        nav_buttons.append(InlineKeyboardButton("⬅️ Back", callback_data=f"spage_{offset-10}_{query}"))
    
    nav_buttons.append(InlineKeyboardButton(f"📄 {int(offset/10)+1}/{int(total_results/10)+1}", callback_data="pages"))

    if offset + 10 < total_results:
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"spage_{offset+10}_{query}"))

    buttons.append(nav_buttons)

    # टेक्स्ट मैसेज
    text = f"🔍 **Search Results for:** `{query}`\n" \
           f"📊 **Found:** {total_results} Files\n\n" \
           f"👇 **Click on a file to Generate Link:**"

    await message.edit_text(text=text, reply_markup=InlineKeyboardMarkup(buttons))
