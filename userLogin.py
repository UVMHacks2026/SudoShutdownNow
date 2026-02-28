from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google.oauth2 import id_token
from google.auth.transport import requests

app = FastAPI()

# Put your frontend's local URL here, or "*" to let anyone connect for the demo.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Change this to ["http://localhost:5173"] if "*" causes issues
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GOOGLE_CLIENT_ID = "YOUR_CLIENT_ID_HERE"

class TokenRequest(BaseModel):
    token: str

# --- THE MOCK DATABASE ---
# This dictionary acts as your database for the next 8 hours.
# If the server restarts, this wipes clean.
users_db = {}

# --- 1. THE AUTHENTICATION & CREATION ENDPOINT ---
@app.post("/api/auth/google")
async def verify_google_token(request: TokenRequest):
    try:
        # Verify token with Google
        idinfo = id_token.verify_oauth2_token(
            request.token, 
            requests.Request(), 
            GOOGLE_CLIENT_ID
        )
        user_email = idinfo.get('email')
        # first name is given name, last name is family name
        f_name = idinfo.get('given_name')
        l_name = idinfo.get('family_name')
        
        # Check if user exists in our fake database
        if user_email not in users_db:
            # If they don't exist, create them!
            users_db[user_email] = {
                "email": user_email,
                "first_name": f_name,
                "last_name": l_name,
                "picture": idinfo.get('picture'),
                "role": "manager" # Assign a default role
            }
            is_new = True
        else:
            is_new = False
        
        # Return the user data to SvelteKit
        return {
            "status": "success",
            "message": "User authenticated",
            "is_new_user": is_new,
            "user": users_db[user_email]
        }

    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid Google Token")

@app.get("/api/users/{email}")
async def get_user(email: str):
    # The frontend guy can hit this URL to fetch a user's profile anytime
    if email in users_db:
        return {"status": "success", "user": users_db[email]}
    else:
        # If the user isn't in our fake database, return a 404 error
        raise HTTPException(status_code=404, detail="User not found")
    