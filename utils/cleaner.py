import re

def get_search_name(text):
    """
    फाइल नाम से कचरा हटाकर सर्च के लिए Clean Name बनाता है।
    Example: "[MKV] Avengers_Endgame_2019_720p_@Channel.mkv" -> "avengers endgame 2019"
    """
    if not text:
        return ""

    # 1. पहले एक्सटेंशन (.mkv, .mp4) हटाओ
    text = text.rsplit('.', 1)[0]

    # 2. सामान्य कचरा (Junk Words) हटाओ
    junk_words = [
        "mkv", "mp4", "avi", "hevc", "x264", "x265", "10bit", "dual audio",
        "hindi", "eng", "english", "sub", "esub", "web-dl", "bluray",
        "camrip", "pre-dvd", "download", "link", "telegram", "channel"
    ]
    
    # Regex बनाकर जंक वर्ड्स को हटाना (Case Insensitive)
    for word in junk_words:
        text = re.sub(r'\b' + word + r'\b', '', text, flags=re.IGNORECASE)

    # 3. सिम्बल्स हटाओ ( brackets [], (), {}, @, _, . )
    # सिर्फ a-z, 0-9 और स्पेस को रहने दो
    text = re.sub(r'[^\w\s]', ' ', text) # Remove symbols
    text = re.sub(r'_', ' ', text)       # Underscore to space

    # 4. एक्स्ट्रा स्पेस हटाकर साफ़ करो
    text = re.sub(r'\s+', ' ', text).strip()

    return text.lower()
