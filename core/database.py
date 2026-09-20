from motor.motor_asyncio import AsyncIOMotorClient
from core.config import MONGO_DETAILS, DB_NAME

client = AsyncIOMotorClient(MONGO_DETAILS)
db = client[DB_NAME]
users_collection = db.get_collection("users")
