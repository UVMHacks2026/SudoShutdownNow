from fastapi import FastAPI
from app.api.routers.users import router as users_router
from app.api.routers.employees import router as employees_router
from app.db import Base, engine
from contextlib import asynccontextmanager
from facialRecognition.localFaceRec.secureFacialID import FacialSecuritySystem

# Create tables
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize the facial recognition system once
    print("Initializing FacialSecuritySystem...")
    app.state.facial_system = FacialSecuritySystem()
    print("Ready.")
    yield
    # Cleanup database connection if needed
    if app.state.facial_system and app.state.facial_system.conn:
        app.state.facial_system.conn.close()

app = FastAPI(
    title="Employee & User API",
    description="Consolidated API for managing employees with Facial Recognition and PostgreSQL",
    version="0.2.0",
    lifespan=lifespan
)

# Include routers
app.include_router(users_router)
app.include_router(employees_router)


@app.get("/")
def read_root():
    """Root endpoint."""
    return {"message": "Welcome to Employee & User API"}

@app.get("/health", tags=["system"])
def health():
    """System health check and status."""
    return {
        "status": "ok", 
        "users_loaded": len(app.state.facial_system.authorized_users) if hasattr(app.state, 'facial_system') else 0
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
