import os
from config import Config
from groq import AsyncGroq

# AI क्लाइंट सेटअप (अगर की मौजूद है)
groq_client = None
if Config.GROQ_API_KEY:
    try:
        groq_client = AsyncGroq(api_key=Config.GROQ_API_KEY)
    except Exception as e:
        print(f"AI Error: {e}")

async def get_ai_welcome(user_name):
    """
    Groq AI का उपयोग करके यूनिक वेलकम मैसेज बनाना।
    """
    # अगर AI बंद है या की नहीं है, तो सिंपल मैसेज भेजो
    if not groq_client:
        return f"Hello {user_name}, Welcome to our Premium Group! 💎"

    try:
        # AI को प्रॉम्प्ट देना (Prompt Engineering)
        prompt = (
            f"You are a witty and friendly bot assistant. "
            f"A user named '{user_name}' has just joined the telegram group. "
            f"Write a very short (max 15 words), funny, and welcoming message for them in Hinglish (Hindi + English mix). "
            f"Use emojis."
        )

        chat_completion = await groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a cool bot."},
                {"role": "user", "content": prompt}
            ],
            model="llama3-8b-8192", # Groq का सबसे तेज़ फ्री मॉडल
            temperature=0.7,
            max_tokens=50
        )
        return chat_completion.choices[0].message.content
    except Exception:
        # अगर API फेल हो जाए, तो बैकअप मैसेज
        return f"Hey {user_name}, Welcome to the party! 🎉"
