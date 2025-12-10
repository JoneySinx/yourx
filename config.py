import os
from os import environ
from dotenv import load_dotenv

# लोड .env (लोकल टेस्टिंग के लिए)
load_dotenv()

# --- Helper Function (True/False सेटिंग्स के लिए) ---
def is_enabled(value, default):
    if value.lower() in ["true", "yes", "1", "enable", "y"]:
        return True
    return False

class Config:
    # 1. Telegram Credentials
    API_ID = int(environ.get("API_ID", "0"))
    API_HASH = environ.get("API_HASH", "")
    BOT_TOKEN = environ.get("BOT_TOKEN", "")

    # 2. Database (MongoDB)
    MONGO_URL = environ.get("MONGO_URL", "")
    DB_NAME = environ.get("DATABASE_NAME", "Premium_Bot_DB")
    COLLECTION_NAME = environ.get('COLLECTION_NAME', 'Files')

    # 3. Channels & Admins
    ADMINS = [int(x) for x in environ.get("ADMINS", "").split()]
    BIN_CHANNEL = int(environ.get("BIN_CHANNEL", "0"))  # फाइल स्टोर करने के लिए
    LOG_CHANNEL = int(environ.get("LOG_CHANNEL", "0"))  # पेमेंट लॉग्स के लिए

    # 4. Links (Support & Updates)
    SUPPORT_LINK = environ.get('SUPPORT_LINK', 'https://t.me/YourSupport')
    UPDATES_LINK = environ.get('UPDATES_LINK', 'https://t.me/YourChannel')

    # 5. Bot Settings (Behavior)
    # फाइल को 10 मिनट (600 sec) बाद डिलीट करें (VIP सुरक्षा)
    DELETE_TIME = int(environ.get('DELETE_TIME', 600)) 
    CACHE_TIME = int(environ.get('CACHE_TIME', 300))
    TIME_ZONE = environ.get('TIME_ZONE', 'Asia/Kolkata')
    
    # फाइल फॉरवर्ड करना ब्लॉक करें (Security)
    PROTECT_CONTENT = is_enabled(environ.get('PROTECT_CONTENT', "True"), True)
    
    # "Did you mean?" स्पेलिंग चेक
    SPELL_CHECK = is_enabled(environ.get("SPELL_CHECK", "True"), True)
    
    # Caption Filter Mode ("FULL" or "SMART")
    CAPTION_MODE = environ.get("CAPTION_MODE", "SMART") 

    # 6. Extraction Settings (Regex के लिए जरूरी)
    # इन भाषाओं और क्वालिटी को हम फाइल नाम से अलग करेंगे
    LANGUAGES = [lang.lower() for lang in environ.get('LANGUAGES', 'hindi english telugu tamil kannada malayalam marathi punjabi bengali dual audio multi audio').split()]
    QUALITY = [qual.lower() for qual in environ.get('QUALITY', '360p 480p 720p 1080p 1440p 2160p 4k 8k hd fhd camrip web-dl bluray').split()]

    # 7. Web Streamer Settings
    # Koyeb या VPS का URL (स्ट्रीमिंग के लिए)
    URL = environ.get("URL", "http://localhost:8080/") 
    PORT = int(environ.get("PORT", 8080))

    # 8. Premium & Payment
    UPI_ID = environ.get("UPI_ID", "")
    UPI_NAME = environ.get("UPI_NAME", "Admin")

    # 9. AI & Smart Features (Optional)
    # अगर API Key है तो AI Welcome ऑन होगा
    GROQ_API_KEY = environ.get("GROQ_API_KEY", None) 
    
    # स्टार्ट कमांड पर रिएक्शन (Cosmetic)
    REACTIONS = [r for r in environ.get('REACTIONS', '🔥 😍 ⚡ 🤝 😇 🫡 🌚 🏆').split()]

    # 10. Custom Messages (Templates)
    # फाइल के नीचे दिखने वाला कैप्शन
    FILE_CAPTION = environ.get("FILE_CAPTION", """
🎬 **{file_name}**
━━━━━━━━━━━━━━━━━━
⚙️ **Size:** {file_size}
🗓 **Date:** {date}
━━━━━━━━━━━━━━━━━━
💎 **Powered by:** Premium Bot
    """)
