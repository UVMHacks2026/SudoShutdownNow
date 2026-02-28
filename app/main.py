from fastapi import FastAPI
from app.api.routers.users import router as users_router
from app.db import Base, engine

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="User API",
    description="FastAPI app for managing users with PostgreSQL",
    version="0.1.0"
)

# Include routers
app.include_router(users_router)


@app.get("/")
def read_root():
    """Root endpoint."""
    return {"message": "Welcome to User API"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
