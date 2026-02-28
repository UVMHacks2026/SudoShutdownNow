"""
Facial Recognition API
Wraps FacialSecuritySystem with two HTTP endpoints.

Endpoints:
  POST /process  - Check if an authorized employee is present in the frame
  POST /register - Register a new employee face

Run with:
  uvicorn api:app --host 0.0.0.0 --port 8000
"""
import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager
try:
    from .secureFacialID import FacialSecuritySystem
except ImportError:
    from secureFacialID import FacialSecuritySystem

# Load environment variables from .env file
load_dotenv()

# --- Shared system instance ---
system: FacialSecuritySystem = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global system
    print("Initializing FacialSecuritySystem (Standalone Mode)...")
    
    database_url = os.getenv("DATABASE_URL")
    fernet_key = os.getenv("FERNET_KEY")
    
    system = FacialSecuritySystem(
        database_url=database_url,
        fernet_key=fernet_key
    )
    print("Ready.")
    yield
    if system and system.conn:
        system.conn.close()

app = FastAPI(title="Facial Recognition API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Request models ---
class FrameRequest(BaseModel):
    image: str  # data:image/jpeg;base64,...

class RegisterRequest(BaseModel):
    image: str  # data:image/jpeg;base64,...
    name: str


# --- Endpoints ---
@app.post("/process")
def process_frame(req: FrameRequest):
    """
    Given a base64 JPG string, check if an authorized employee is in the frame.
    Returns presence, name, system status, and face count.
    """
    if not req.image:
        raise HTTPException(status_code=400, detail="image field is required")
    result = system.process_frame(req.image)
    if "error" in result:
        raise HTTPException(status_code=422, detail=result["error"])
    return result


@app.post("/register")
def register_user(req: RegisterRequest):
    """
    Given a base64 JPG string and an employee name, register the face in the DB.
    Returns the new employee_id on success.
    """
    if not req.image or not req.name:
        raise HTTPException(status_code=400, detail="image and name fields are required")
    result = system.register_user(req.image, req.name)
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error", "Registration failed"))
    return result


@app.get("/health")
def health():
    return {"status": "ok", "users_loaded": len(system.authorized_users)}
