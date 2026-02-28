# File to allow a user to create their account

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/users/{email}")
async def get_user(email: str):
    # URL to fetch a user's profile
    if email in users_db:
        return {"status": "success", "user": users_db[email]}
    else:
        # If the user isn't in our fake database, return a 404 error
        raise HTTPException(status_code=404, detail="User not found")
    