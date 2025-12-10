import time
import asyncio
from hydrogram import Client, filters
from hydrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from config import Config
from database import db

# --- 1. STATS (Live Dashboard) ---
@Client.on_message(filters.command("stats") & filters.user(Config.ADMINS))
async def stats_handler(bot, message):
    msg = await message.reply_text("🔄 Fetching Stats...")
    
    users, files, premium_users = await db.get_stats()
    
    text = f"""
📊 **System Statistics**

👤 **Total Users:** `{users}`
💎 **Premium Users:** `{premium_users}`
📂 **Total Files:** `{files}`
    """
    await msg.edit_text(text)

# --- 2. BROADCAST (Message to All) ---
@Client.on_message(filters.command("broadcast") & filters.user(Config.ADMINS) & filters.reply)
async def broadcast_handler(bot, message):
    await message.reply_text("🚀 Broadcast Started...")
    
    all_users = db.users.find({})
    count = 0
    success = 0
    blocked = 0
    
    async for user in all_users:
        try:
            await message.reply_to_message.copy(chat_id=user['_id'])
            success += 1
        except Exception:
            blocked += 1
        
        count += 1
        if count % 20 == 0:
            await asyncio.sleep(1) # Flood Wait से बचने के लिए

    await message.reply_text(f"✅ **Broadcast Complete!**\n\nSent: {success}\nBlocked: {blocked}")

# --- 3. MANUAL PREMIUM ADD (Command) ---
@Client.on_message(filters.command("add_premium") & filters.user(Config.ADMINS))
async def manual_add_premium(bot, message):
    # Format: /add_premium user_id days
    try:
        _, user_id, days = message.text.split()
        user_id = int(user_id)
        days = int(days)
        
        await db.add_premium(user_id, days)
        await message.reply_text(f"✅ User `{user_id}` is now Premium for {days} days.")
        
        # यूजर को भी बता दो
        try:
            await bot.send_message(user_id, f"💎 **Premium Activated!**\n\nAdmin has added {days} days of Premium to your account.")
        except:
            pass
            
    except:
        await message.reply_text("❌ Usage: `/add_premium 123456789 30`")

# --- 4. PAYMENT APPROVAL SYSTEM (Buttons Logic) ---
@Client.on_callback_query(filters.regex(r"^pay_"))
async def payment_approval_handler(bot, query: CallbackQuery):
    # Data Format: pay_action_userid_days
    data = query.data.split("_")
    action = data[1] # approve / reject
    user_id = int(data[2])
    
    if action == "approve":
        days = int(data[3])
        # 1. DB में अपडेट करें
        await db.add_premium(user_id, days)
        
        # 2. एडमिन मैसेज एडिट करें
        await query.edit_message_caption(
            caption=f"✅ **Approved by {query.from_user.mention}**\nUser: `{user_id}`\nPlan: {days} Days"
        )
        
        # 3. यूजर को खुशखबरी दें
        try:
            await bot.send_message(
                user_id,
                f"🎉 **Payment Accepted!**\n\nYour Premium Plan ({days} Days) has been activated.\nEnjoy high-speed streaming!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔍 Search Movie", switch_inline_query="")]])
            )
        except:
            pass
            
    elif action == "reject":
        await query.edit_message_caption(
            caption=f"❌ **Rejected by {query.from_user.mention}**\nUser: `{user_id}`"
        )
        try:
            await bot.send_message(user_id, "❌ **Payment Rejected.**\nPlease contact admin with valid proof.")
        except:
            pass
