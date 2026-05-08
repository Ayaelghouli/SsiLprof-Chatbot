import os
import hashlib
import bcrypt
import secrets
import json
from typing import Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, EmailStr

from src.inference.bot_engine import bot_engine
from src.profiling.profile_engine import StudentProfile
from src.scoring.scoring_engine import recommend_schools
from database import user_collection

with open("data/data_complet.json", "r", encoding="utf-8") as f:
    knowledge_base = json.load(f)
SCHOOLS = knowledge_base.get("ecoles", [])

app = FastAPI(title="Ssi Lprof API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="../frontend"), name="static")


# in-memory sessions — session_id is a random token, not the email
user_sessions: Dict[str, StudentProfile] = {}


# models
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class ChatMessage(BaseModel):
    message: str
    session_id: str

class ResetRequest(BaseModel):
    session_id: str


# password helpers — bcrypt with salt, much safer than plain sha256
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    if not hashed.startswith("$2b$"):
        return hashlib.sha256(password.encode()).hexdigest() == hashed
    return bcrypt.checkpw(password.encode(), hashed.encode())


@app.get("/")
async def read_index():
    return FileResponse("../frontend/index.html")


@app.post("/signup")
async def register(user: UserRegister):
    existing = await user_collection.find_one({"email": user.email})
    if existing:
        raise HTTPException(status_code=400, detail="Cet email est déjà utilisé.")

    await user_collection.insert_one({
        "email":        user.email,
        "password":     hash_password(user.password),
        "full_name":    user.full_name,
        "chat_history": []
    })
    return {"message": "Compte créé avec succès."}


@app.post("/login")
async def login(data: UserLogin):
    user = await user_collection.find_one({"email": data.email})
    if not user or not verify_password(data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect.")

    # generate a random session token — never expose the email as session_id
    session_id = secrets.token_hex(32)
    user_sessions[session_id] = StudentProfile()

    return {
        "message":    "Login successful",
        "user":       user["full_name"],
        "session_id": session_id
    }


@app.post("/chat")
async def chat(chat_msg: ChatMessage):
    if chat_msg.session_id not in user_sessions:
        raise HTTPException(status_code=401, detail="Session invalide ou expirée.")

    profile = user_sessions[chat_msg.session_id]
    result  = bot_engine(chat_msg.message, profile)

    # save to MongoDB using session_id to find the right user
    await user_collection.update_one(
        {"session_id": chat_msg.session_id},
        {
            "$set":  {"profile": profile.data},
            "$push": {"chat_history": {
                "user": chat_msg.message,
                "bot":  result["reply"]
            }}
        }
    )

    return result


@app.post("/reset")
async def reset(data: ResetRequest):
    if data.session_id in user_sessions:
        user_sessions[data.session_id] = StudentProfile()
    return {"message": "Session réinitialisée."}

@app.get("/recommendations/{session_id}")
async def get_recommendations(session_id: str):
    if session_id not in user_sessions:
        raise HTTPException(status_code=401, detail="Session invalide ou expirée.")

    profile = user_sessions[session_id]
    results = recommend_schools(profile.data, SCHOOLS, top_k=5)

    output = []
    for r in results:
        school = r["school"]
        output.append({
            "name":      school.get("School_Name", ""),
            "full_name": school.get("full_name", ""),
            "score":     r["score"],
            "eligible":  r["eligible"],
            "seuil":     r["seuil"],
            "marge":     r["marge"],
            "filieres":  school.get("Filieres", ""),
            "careers":   school.get("Careers", ""),
            "category":  school.get("category", ""),
            "villes":    school.get("Villes", ""),
        })

    return {"recommendations": output, "profile": profile.data}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)