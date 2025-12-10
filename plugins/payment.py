from hydrogram import Client, filters
from hydrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
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
    
    if isinstance(update, filters.Message):
        await message.reply_text(text, reply_markup=buttons)
    else:
        await message.edit_text(text, reply_markup=buttons)

# --- 2. PAYMENT INSTRUCTION ---
@Client.on_callback_query(filters.regex(r"^pay_info_"))
async def pay_info_handler(bot, query):
    _, days, amount = query.data.split("_")
    
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

# --- 3. SCREENSHOT HANDLER ---
@Client.on_message(filters.photo & filters.private)
async def screenshot_handler(bot, message):
    # अगर एडमिन फोटो भेजे तो इग्नोर (क्योंकि एडमिन फाइल इंडेक्स करता है)
    if message.from_user.id in Config.ADMINS:
        return

    # यूजर से पूछें कि क्या यह पेमेंट है?
    await message.reply_text(
        "📸 **Screenshot Received!**\n\nIs this for Premium Payment?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Yes, Send to Admin", callback_data=f"confirm_pay_{message.id}")],
            [InlineKeyboardButton("❌ No, Delete", callback_data="delete_msg")]
        ]),
        quote=True
    )

# --- 4. CONFIRM & SEND TO LOG CHANNEL ---
@Client.on_callback_query(filters.regex(r"^confirm_pay_"))
async def confirm_payment(bot, query):
    _, msg_id = query.data.split("_", 2)
    msg_id = int(msg_id)
    user = query.from_user
    
    # यूजर को इंतज़ार करवाओ
    await query.edit_message_text("⏳ Sending to Admin for verification...")
    
    # 1. फोटो को Log Channel में भेजो
    try:
        # असली मैसेज (फोटो) को कॉपी करें
        await bot.copy_message(
            chat_id=Config.LOG_CHANNEL,
            from_chat_id=user.id,
            message_id=msg_id,
            caption=f"🔔 **New Payment!**\n\n👤: {user.mention} (`{user.id}`)\n📅 Date: Today",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Approve (30 Days)", callback_data=f"pay_approve_{user.id}_30"),
                    InlineKeyboardButton("✅ Approve (1 Year)", callback_data=f"pay_approve_{user.id}_365")
                ],
                [InlineKeyboardButton("❌ Reject", callback_data=f"pay_reject_{user.id}")]
            ])
        )
        await query.edit_message_text("✅ **Sent!**\nYou will be notified once approved (approx 10-15 mins).")
        
    except Exception as e:
        await query.edit_message_text(f"❌ Error sending to admin: {e}")
