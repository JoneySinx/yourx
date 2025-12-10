from hydrogram import Client, filters
from hydrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import Config
from database import db
from utils.ai_helper import get_ai_welcome

@Client.on_message(filters.command("start") & filters.private)
async def start_handler(bot, message):
    user = message.from_user
    
    # 1. यूजर को डेटाबेस में रजिस्टर करें
    await db.add_user(user.id, user.first_name)
    
    # 2. क्या यूजर Premium है?
    is_premium = await db.is_user_premium(user.id)
    status_text = "💎 Premium Member" if is_premium else "👤 Free User"

    # 3. AI Welcome Message (Smart Feature)
    # अगर AI ऑन है तो वो मैसेज लिखेगा, नहीं तो सिंपल मैसेज आएगा
    welcome_text = await get_ai_welcome(user.first_name)
    
    # 4. फाइनल मैसेज
    text = f"""
{welcome_text}

🆔 **ID:** `{user.id}`
🏷 **Status:** {status_text}

👇 **What can I do?**
Type movie name to search (e.g. `Iron Man`)
"""

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 Buy Premium", callback_data="buy_premium")],
        [InlineKeyboardButton("🆘 Help", callback_data="help_command")]
    ])

    await message.reply_text(text=text, reply_markup=buttons, quote=True)
