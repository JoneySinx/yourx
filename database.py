import time
import motor.motor_asyncio
from config import Config
from datetime import datetime, timedelta

class Database:
    def __init__(self):
        # MongoDB कनेक्शन (Global Session)
        self.client = motor.motor_asyncio.AsyncIOMotorClient(Config.MONGO_URL)
        self.db = self.client[Config.DB_NAME]
        
        # Collections (फोल्डर्स)
        self.col = self.db[Config.COLLECTION_NAME] # फाइल्स के लिए
        self.users = self.db.users                 # यूजर्स के लिए
        self.payments = self.db.payments           # पेमेंट्स के लिए

    # ------------------
    # 1. USER MANAGEMENT
    # ------------------
    async def add_user(self, user_id, name):
        """नए यूजर को डेटाबेस में जोड़ें"""
        user = await self.users.find_one({"_id": user_id})
        if not user:
            await self.users.insert_one({
                "_id": user_id,
                "name": name,
                "is_premium": False,
                "premium_expiry": 0,
                "joined_date": time.time()
            })
            return True
        return False

    async def is_user_premium(self, user_id):
        """चेक करें कि यूजर प्रीमियम है या नहीं"""
        # 1. अगर एडमिन है, तो हमेशा प्रीमियम है (Forever VIP)
        if user_id in Config.ADMINS:
            return True
            
        # 2. डेटाबेस चेक करें
        user = await self.users.find_one({"_id": user_id})
        if not user:
            return False
            
        # 3. एक्सपायरी डेट चेक करें
        if user.get("premium_expiry", 0) > time.time():
            return True
            
        return False

    async def add_premium(self, user_id, days):
        """यूजर को प्रीमियम प्लान दें"""
        user = await self.users.find_one({"_id": user_id})
        current_expiry = user.get("premium_expiry", 0) if user else 0
        
        # अगर पुराना प्लान अभी एक्टिव है, तो उसमें दिन जोड़ें
        # अगर नहीं है, तो अभी (Current Time) से शुरू करें
        start_time = max(time.time(), current_expiry)
        seconds_to_add = days * 24 * 60 * 60
        new_expiry = start_time + seconds_to_add
        
        await self.users.update_one(
            {"_id": user_id},
            {"$set": {
                "is_premium": True,
                "premium_expiry": new_expiry,
                "plan_updated_date": time.time()
            }},
            upsert=True
        )
        return True

    async def remove_premium(self, user_id):
        """प्रीमियम हटाएँ (Ban या Expire होने पर)"""
        await self.users.update_one(
            {"_id": user_id},
            {"$set": {"is_premium": False, "premium_expiry": 0}}
        )

    # ------------------
    # 2. FILE MANAGEMENT (Indexing)
    # ------------------
    async def save_file(self, file_data):
        """फाइल सेव करें (Duplicate Check के साथ)"""
        # file_data dictionary होगी जिसमें name, size, file_id आदि होगा
        try:
            # unique_id चेक करें ताकि एक ही फाइल बार-बार सेव न हो
            existing = await self.col.find_one({"unique_id": file_data["unique_id"]})
            if not existing:
                await self.col.insert_one(file_data)
                return "saved"
            return "duplicate"
        except Exception as e:
            print(f"Error saving file: {e}")
            return "error"

    # ------------------
    # 3. SEARCH ENGINE (Core Logic)
    # ------------------
    async def search_files(self, query):
        """फाइल सर्च करें"""
        # हम Regex का उपयोग करेंगे जो 'Partial Match' ढूंढ सके (Case Insensitive)
        # नोट: एडवांस सॉर्टिंग हम plugins/search.py में करेंगे, यहाँ सिर्फ RAW डेटा निकालेंगे
        mongo_query = {
            "search_name": {
                "$regex": query,    # जो भी यूजर लिखे (जैसे 'avenger')
                "$options": "i"     # छोटा-बड़ा (Capital/Small) इग्नोर करें
            }
        }
        
        # टॉप 100 रिजल्ट्स लाओ (ताकि बोट हैंग न हो)
        cursor = self.col.find(mongo_query).limit(100)
        return await cursor.to_list(length=100)

    async def get_file(self, file_id):
        """ID से फाइल निकालें (Stream Link बनाने के लिए)"""
        return await self.col.find_one({"_id": file_id})

    # ------------------
    # 4. STATS (Admin Panel)
    # ------------------
    async def get_stats(self):
        users = await self.users.count_documents({})
        files = await self.col.count_documents({})
        premium_users = await self.users.count_documents({"premium_expiry": {"$gt": time.time()}})
        return users, files, premium_users

# ग्लोबल डेटाबेस ऑब्जेक्ट (ताकि हम db.add_user() को सीधे यूज़ कर सकें)
db = Database()
