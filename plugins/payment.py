from hydrogram import Client, filters
from hydrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from hydrogram.errors import MessageNotModified  # Import this error
from config import Config
from database import db

# --- 1. SHOW PLANS ---
@Client.on_message(filters.command("plan") | filters.command("buy"))
@Client.on_callback_query(filters.regex("^buy_premium"))
async def show_plans(bot, update):
    # मैसेज और कॉलबैक दोनों हैंडल करने के लिए
    if isinstance(update, filters.Message):
        message = update
    else:
        message = update.message

    text = f"""
💎 **Premium Plans** 💎

Unlock High-Speed Streaming & Unlimited Downloads!

UPI ID: `{Config.UPI_ID}`
Name: **{Config.UPI_NAME}**

👇 **Select a Plan:**
"""
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("📅 Monthly - ₹49", callback_data="pay_info_30_49")],
        [InlineKeyboardButton("📅 Yearly - ₹499", callback_data="pay_info_365_499")],
        [InlineKeyboardButton("❌ Close", callback_data="delete_msg")]
    ])
    
    try:
        if isinstance(update, filters.Message):
            await message.reply_text(text, reply_markup=buttons)
        else:
            await message.edit_text(text, reply_markup=buttons)
    except MessageNotModified:
        pass  # Ignore if message is not modified

# --- 2. PAYMENT INSTRUCTION ---
@Client.on_callback_query(filters.regex(r"^pay_info_"))
async def pay_info_handler(bot, query):
    # FIX: पहले यहाँ 3 वेरिएबल थे, अब हमने 4 कर दिए हैं
    # Data: pay_info_30_49 -> ['pay', 'info', '30', '49']
    try:
        data_parts = query.data.split("_")
        if len(data_parts) == 4:
             _, _, days, amount = data_parts
        else:
             # Handle incorrect format or log error
             print(f"Invalid callback data format: {query.data}")
             return

        text = f"""
💳 **Payment Steps**

1️⃣ Pay **₹{amount}** to UPI: `{Config.UPI_ID}`
2️⃣ Take a **Screenshot** of success.
3️⃣ Send the screenshot **HERE** in this chat.

⏳ **Plan:** {days} Days
"""
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Back", callback_data="buy_premium")]
        ]))
    except MessageNotModified:
        pass

# ... (rest of the file remains same)
