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

# DATABASE FOR USERS
# Fake user for testing
users_db = {
    "manager@burlingtonbuilds.com": {
        "email": "employee@burlingtonbuilds.com",
        "first_name": "Jane",
        "last_name": "Doe",
        "picture": "https://ui-avatars.com/api/?name=Jane+Doe", # Generates a fake profile pic
        "role": "employee"
    }
}

@app.get("/api/users/{email}")
async def get_user(email: str):
    # URL to fetch a user's profile
    if email in users_db:
        return {"status": "success", "user": users_db[email]}
    else:
        # If the user isn't in our fake database, return a 404 error
        raise HTTPException(status_code=404, detail="User not found")
    