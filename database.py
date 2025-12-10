import time
import motor.motor_asyncio
from bson.objectid import ObjectId  # <--- IMPORT ADDED
from config import Config

class Database:
    def __init__(self):
        self.client = motor.motor_asyncio.AsyncIOMotorClient(Config.MONGO_URL)
        self.db = self.client[Config.DB_NAME]
        
        self.col = self.db[Config.COLLECTION_NAME]
        self.users = self.db.users
        self.payments = self.db.payments

    # --- USER MANAGEMENT ---
    async def add_user(self, user_id, name):
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
        if user_id in Config.ADMINS:
            return True
        user = await self.users.find_one({"_id": user_id})
        if not user:
            return False
        if user.get("premium_expiry", 0) > time.time():
            return True
        return False

    async def add_premium(self, user_id, days):
        user = await self.users.find_one({"_id": user_id})
        current_expiry = user.get("premium_expiry", 0) if user else 0
        start_time = max(time.time(), current_expiry)
        new_expiry = start_time + (days * 24 * 60 * 60)
        
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
        await self.users.update_one(
            {"_id": user_id},
            {"$set": {"is_premium": False, "premium_expiry": 0}}
        )

    # --- FILE MANAGEMENT ---
    async def save_file(self, file_data):
        try:
            existing = await self.col.find_one({"unique_id": file_data["unique_id"]})
            if not existing:
                await self.col.insert_one(file_data)
                return "saved"
            return "duplicate"
        except Exception as e:
            print(f"Error saving file: {e}")
            return "error"

    async def search_files(self, query):
        mongo_query = {"search_name": {"$regex": query, "$options": "i"}}
        cursor = self.col.find(mongo_query).limit(100)
        return await cursor.to_list(length=100)

    # --- FIX IS HERE ---
    async def get_file(self, file_id):
        try:
            return await self.col.find_one({"_id": ObjectId(file_id)})
        except:
            return None

    async def get_stats(self):
        users = await self.users.count_documents({})
        files = await self.col.count_documents({})
        premium_users = await self.users.count_documents({"premium_expiry": {"$gt": time.time()}})
        return users, files, premium_users

db = Database()
