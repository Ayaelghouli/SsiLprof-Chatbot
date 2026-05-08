from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os

load_dotenv()
MONGO_DETAILS = os.getenv("MONGO_URI", "mongodb://localhost:27017")

client = AsyncIOMotorClient(MONGO_DETAILS)


database = client.ssi_lprof_db


user_collection = database.get_collection("users")


async def test_connection():
    try:
        await client.admin.command('ping')
        print(" Connection à MongoDB réussie !")
    except Exception as e:
        print(f" Erreur de connexion: {e}")