from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
import io
import json
import base64
import numpy as np
import cv2

# Import facial recognition system
from facialRecognition.localFaceRec.secureFacialID import (
    init_db, load_users, save_user, compute_similarity, 
    face_app, authorized_users, last_known_authorized_centers, conn,
    match_face, delete_user, get_all_users, SIMILARITY_THRESHOLD,
    FACE_MODEL, GPU_ENABLED
)

app = FastAPI()

# --- Accepted Origins for CORS ---
origins = [
    "http://cgswswk88cg04k4www8g8cgs.76.13.29.239.sslip.io",
    "http://localhost:5173",  # Svelte dev server
    "http://localhost:3000",
    "http://localhost:8000"
]
# --- CORS Middleware Setup ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- HEALTH CHECK ENDPOINT ---
@app.get("/")
async def root():
    return {"status": "ok", "message": "Facial Recognition API is running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

# --- SYSTEM STATUS ENDPOINTS ---
@app.get("/api/system/status")
async def system_status():
    """Get system configuration and status"""
    return {
        "status": "ok",
        "database_connected": conn is not None,
        "face_model_loaded": face_app is not None,
        "model_name": FACE_MODEL,
        "gpu_enabled": GPU_ENABLED,
        "similarity_threshold": SIMILARITY_THRESHOLD,
        "registered_users_count": len(authorized_users)
    }

@app.get("/api/system/stats")
async def system_stats():
    """Get system statistics"""
    try:
        all_users = get_all_users() if conn else {}
        return {
            "status": "ok",
            "total_registered_users": len(authorized_users),
            "users_in_memory": list(authorized_users.keys()),
            "users_in_database": list(all_users.keys()) if all_users else [],
            "threshold": SIMILARITY_THRESHOLD
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "total_registered_users": len(authorized_users),
            "users_in_memory": list(authorized_users.keys())
        }

# --- USER MANAGEMENT ENDPOINTS ---
@app.get("/api/users")
async def get_users():
    """Get all registered users"""
    try:
        all_users = get_all_users() if conn else {}
        return {
            "status": "ok",
            "count": len(authorized_users),
            "users": all_users if all_users else {name: {} for name in authorized_users.keys()}
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "users": {name: {} for name in authorized_users.keys()}
        }

@app.get("/api/users/{user_name}")
async def get_user(user_name: str):
    """Get specific user information"""
    if user_name in authorized_users:
        return {
            "status": "ok",
            "name": user_name,
            "registered": True,
            "embedding_shape": [512],
            "threshold": SIMILARITY_THRESHOLD
        }
    return {
        "status": "not_found",
        "message": f"User {user_name} not registered"
    }

@app.delete("/api/users/{user_name}")
async def remove_user(user_name: str):
    """Delete a registered user"""
    if user_name not in authorized_users:
        return {
            "status": "error",
            "message": f"User {user_name} not found"
        }
    
    success = delete_user(user_name)
    return {
        "status": "ok" if success else "error",
        "message": f"User {user_name} deleted successfully" if success else f"Failed to delete {user_name}",
        "remaining_users": len(authorized_users)
    }

# --- FACE MATCHING ENDPOINT ---
@app.post("/api/match")
async def match_face_endpoint(embedding: dict):
    """Match a face embedding against registered users"""
    try:
        if "embedding" not in embedding:
            return {
                "status": "error",
                "message": "No embedding provided"
            }
        
        emb_array = np.array(embedding["embedding"], dtype=np.float32)
        matched_name, similarity = match_face(emb_array, SIMILARITY_THRESHOLD)
        
        return {
            "status": "ok",
            "matched_name": matched_name,
            "similarity": float(similarity),
            "threshold": SIMILARITY_THRESHOLD,
            "authorized": matched_name is not None
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

# --- UTILITY FUNCTIONS ---
def decode_base64_image(base64_string):
    """Decode base64 string to OpenCV image"""
    try:
        if "," in base64_string:
            base64_string = base64_string.split(",")[1]
        
        image_data = base64.b64decode(base64_string)
        image = Image.open(io.BytesIO(image_data))
        frame = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        return frame
    except Exception as e:
        print(f"Error decoding image: {e}")
        return None

def process_face_frame(frame, register_mode=False):
    """Process frame and return facial recognition results"""
    try:
        faces = face_app.get(frame)
        results = []
        
        for face in faces:
            face_bbox = face.bbox.astype(int)
            embedding = face.normed_embedding
            
            best_match_name = None
            best_sim = 0.0
            
            # Compare against authorized users
            for name, auth_emb in authorized_users.items():
                sim = compute_similarity(auth_emb, embedding)
                if sim > 0.40 and sim > best_sim:
                    best_sim = sim
                    best_match_name = name
            
            result = {
                "bbox": face_bbox.tolist(),
                "embedding": embedding.tolist(),
                "matched_name": best_match_name,
                "similarity": float(best_sim) if best_match_name else 0.0,
                "authorized": best_match_name is not None
            }
            results.append(result)
        
        return {
            "status": "success",
            "face_count": len(faces),
            "faces": results
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

# --- INCOMING DATA STREAM ---
@app.websocket("/ws/stream")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("WebSocket connection accepted")
    
    register_next_face = False

    try:
        while True:
            data = await websocket.receive_text()

            # --- HANDLE COMMANDS FROM SVELTE ---
            if data.startswith("{"): 
                try:
                    command_data = json.loads(data)
                    
                    if command_data.get("action") == "register":
                        register_next_face = True
                        await websocket.send_json({
                            "type": "command_response",
                            "action": "register",
                            "message": "Registration armed for next frame."
                        })
                        print("Registration armed for next frame.")
                        
                    elif command_data.get("action") == "clear":
                        if conn:
                            try:
                                with conn.cursor() as cursor:
                                    cursor.execute("DELETE FROM users")
                                conn.commit()
                            except Exception as e:
                                print(f"Error clearing database: {e}")
                        authorized_users.clear()
                        last_known_authorized_centers.clear()
                        await websocket.send_json({
                            "type": "command_response",
                            "action": "clear",
                            "message": "Database CLEARED."
                        })
                        print("Database CLEARED.")
                        
                except json.JSONDecodeError:
                    pass
                continue

            # --- PROCESS IMAGE DATA ---
            print("Processing image from WebSocket")
            
            # Decode base64 image
            frame = decode_base64_image(data)
            if frame is None:
                await websocket.send_json({
                    "type": "error",
                    "message": "Failed to decode image"
                })
                continue
            
            # Process faces in frame
            result = process_face_frame(frame, register_mode=register_next_face)
            
            # Handle registration if armed
            if register_next_face and result["face_count"] == 1:
                face_data = result["faces"][0]
                name = f"User_{len(authorized_users) + 1}"
                embedding = np.array(face_data["embedding"])
                
                if save_user(name, embedding):
                    authorized_users[name] = embedding
                    await websocket.send_json({
                        "type": "registration_success",
                        "name": name,
                        "message": f"Successfully registered {name}"
                    })
                    print(f"Registered {name}")
                else:
                    await websocket.send_json({
                        "type": "registration_error",
                        "message": "Failed to save user"
                    })
                
                register_next_face = False
            else:
                # Send facial recognition results back to Svelte
                result["type"] = "face_detection"
                await websocket.send_json(result)
                
    except WebSocketDisconnect:
        print("WebSocket connection closed")