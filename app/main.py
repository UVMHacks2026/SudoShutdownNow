from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from app.api.routers.users import router as users_router
from app.api.routers.employees import router as employees_router
from app.db import Base, engine
from contextlib import asynccontextmanager
import json

from facialRecognition.localFaceRec.secureFacialID import FacialSecuritySystem
from sqlalchemy import text

def bootstrap_tables() -> None:
    """
    Ensure SQLAlchemy's app_users table can coexist with facial embedding storage.
    If a legacy facial table named users exists, migrate it to facial_embeddings.
    """
    print("Checking for legacy tables...")
    with engine.begin() as conn:
        # Check if 'users' table exists first
        table_exists = conn.execute(
            text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'users')")
        ).scalar()
        
        if not table_exists:
            return

        columns = conn.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'users'"
            )
        ).fetchall()
        column_names = {row[0] for row in columns}
        
        # Legacy table had 'name' and 'embedding', and definitely NOT 'email'
        is_legacy_facial_table = "name" in column_names and "embedding" in column_names and "email" not in column_names

        if is_legacy_facial_table:
            print("Migrating legacy facial table 'users' to 'facial_embeddings'...")
            conn.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS facial_embeddings ("
                    "id SERIAL PRIMARY KEY, "
                    "name TEXT UNIQUE, "
                    "embedding BYTEA)"
                )
            )
            conn.execute(
                text(
                    "INSERT INTO facial_embeddings (name, embedding) "
                    "SELECT name, embedding FROM users "
                    "ON CONFLICT (name) DO NOTHING"
                )
            )
            conn.execute(text("DROP TABLE users"))
            print("Migration complete.")

from app.core.config import get_settings

def get_facial_system(app: FastAPI) -> FacialSecuritySystem:
    """Lazy-initialize the facial recognition system."""
    if not hasattr(app.state, "facial_system") or app.state.facial_system is None:
        print("Initializing FacialSecuritySystem (Lazy)...")
        settings = get_settings()
        app.state.facial_system = FacialSecuritySystem(
            database_url=settings.DATABASE_URL,
            fernet_key=settings.FERNET_KEY
        )
    return app.state.facial_system

# Run migration before creating other tables
bootstrap_tables()
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Lazy-init facial system in endpoint dependency so startup is fast/reliable.
    app.state.facial_system = None
    yield
    if app.state.facial_system and app.state.facial_system.conn:
        app.state.facial_system.conn.close()

app = FastAPI(
    title="Employee & User API",
    description="Consolidated API for managing employees with Facial Recognition and PostgreSQL",
    version="0.2.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Svelte default
        "http://localhost:5174",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://0.0.0.0:5173",
        "http://0.0.0.0:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(users_router)
app.include_router(employees_router)

@app.websocket("/ws/stream")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("WebSocket connected tracking")
    
    # Lazy-init if needed
    facial_system = get_facial_system(websocket.app)
    
    try:
        while True:
            data = await websocket.receive_text()
            
            # Check if data is JSON (for actions like get_status/get_employees)
            try:
                msg = json.loads(data)
                action = msg.get("action")
                if action == "get_status":
                    await websocket.send_json({
                        "type": "status",
                        "status": "SECURE",
                        "users_loaded": len(facial_system.authorized_users)
                    })
                    continue
                elif action == "get_employees":
                    await websocket.send_json({
                        "type": "employees",
                        "employees": [{"name": n} for n in facial_system.authorized_users.keys()]
                    })
                    continue
            except:
                # Not JSON, assume it's a base64 image
                pass
            
            # Process frame
            if data.startswith("data:image"):
                result = facial_system.process_frame(data)
                
                # Format response for test_ui.html
                if result.get("is_employee_present"):
                    await websocket.send_json({
                        "type": "clock_success",
                        "employee": {"name": result["employee_name"]},
                        "clock": {"action": "verify"},
                        "confidence": result["confidence"]
                    })
                elif "error" in result:
                    await websocket.send_json({
                        "type": "error",
                        "message": result["error"]
                    })
                else:
                    await websocket.send_json({
                        "type": "recognition_failed",
                        "faces_detected": result.get("faces_detected", 0),
                        "similarity": 0.0 # Placeholder
                    })
    except WebSocketDisconnect:
        print("WebSocket disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")


@app.get("/")
def read_root():
    """Root endpoint."""
    return {"message": "Welcome to Employee & User API"}

@app.get("/health", tags=["system"])
def health():
    """System health check and status."""
    # We trigger lazy init here too so user knows it's working
    facial_system = get_facial_system(app)
    return {
        "status": "ok", 
        "users_loaded": len(facial_system.authorized_users)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
