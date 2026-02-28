from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
import io
import json
import base64
import numpy as np
import cv2
from datetime import datetime

# Import facial recognition system
try:
    from facialRecognition.localFaceRec.secureFacialID import FacialSecuritySystem
    security_system = FacialSecuritySystem()
    face_app = security_system.face_app
    authorized_users = security_system.authorized_users
    conn = security_system.conn
    print("✓ FacialSecuritySystem initialized successfully")
except FileNotFoundError as e:
    print(f"⚠ Secrets file not found: {e}")
    print("Running in DEGRADED MODE - facial recognition unavailable")
    face_app = None
    authorized_users = {}
    conn = None
except Exception as e:
    print(f"ERROR initializing FacialSecuritySystem: {e}")
    print("Running in DEGRADED MODE - facial recognition unavailable")
    face_app = None
    authorized_users = {}
    conn = None

# Default constants for face matching
SIMILARITY_THRESHOLD = 0.40  # 40% similarity threshold for face matching

app = FastAPI()

# --- In-memory clock status tracking ---
employee_clock_status = {}  # {employee_name: {"clocked_in": bool, "clock_in_time": datetime, "clock_out_time": datetime}}

# --- Accepted Origins for CORS ---
origins = [
    "http://cgswswk88cg04k4www8g8cgs.76.13.29.239.sslip.io",
    "http://localhost:5173",  # Svelte dev server
    "http://localhost:3000",
    "http://localhost:8000",
    "http://localhost:8001"
]
# --- CORS Middleware Setup ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- UTILITY FUNCTIONS FOR SIMILARITY MATCHING ---
def compute_similarity(emb1, emb2):
    """Compute cosine similarity between two embeddings"""
    try:
        emb1 = np.array(emb1).flatten()
        emb2 = np.array(emb2).flatten()
        
        # Cosine similarity
        dot_product = np.dot(emb1, emb2)
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        similarity = dot_product / (norm1 * norm2)
        return similarity
    except Exception as e:
        print(f"Error computing similarity: {e}")
        return 0.0

# --- HEALTH CHECK ENDPOINTS ---
@app.get("/")
async def root():
    return {"status": "ok", "message": "Facial Recognition Clock-In System Running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

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

def get_face_embedding(frame):
    """Extract face embedding from frame"""
    try:
        if face_app is None:
            return None
        
        faces = face_app.get(frame)
        if len(faces) == 0:
            return None
        
        # Return embedding of the most prominent face
        embedding = faces[0].normed_embedding
        return embedding
    except Exception as e:
        print(f"Error extracting face embedding: {e}")
        return None

def recognize_employee(embedding):
    """Recognize employee from embedding"""
    if not embedding or len(authorized_users) == 0:
        return None, 0.0, "No registered employees"
    
    best_match_name = None
    best_similarity = 0.0
    
    for name, registered_embedding in authorized_users.items():
        similarity = compute_similarity(registered_embedding, embedding)
        if similarity > best_similarity:
            best_similarity = similarity
            best_match_name = name if similarity >= SIMILARITY_THRESHOLD else None
    
    return best_match_name, best_similarity, "Match found" if best_match_name else "No match above threshold"

def get_employee_info(employee_name):
    """Get employee information"""
    try:
        if employee_name in authorized_users:
            return {
                "name": employee_name,
                "registered": True,
                "status": "Active"
            }
        return None
    except Exception as e:
        print(f"Error getting employee info: {e}")
        return None

def toggle_clock_status(employee_name):
    """Toggle clock in/out status for employee"""
    current_time = datetime.now()
    
    if employee_name not in employee_clock_status:
        employee_clock_status[employee_name] = {
            "clocked_in": False,
            "clock_in_time": None,
            "clock_out_time": None
        }
    
    status = employee_clock_status[employee_name]
    
    if status["clocked_in"]:
        # Clock out
        status["clocked_in"] = False
        status["clock_out_time"] = current_time.isoformat()
        action = "clock_out"
        message = f"{employee_name} clocked OUT"
    else:
        # Clock in
        status["clocked_in"] = True
        status["clock_in_time"] = current_time.isoformat()
        status["clock_out_time"] = None
        action = "clock_in"
        message = f"{employee_name} clocked IN"
    
    return {
        "action": action,
        "message": message,
        "clocked_in": status["clocked_in"],
        "timestamp": current_time.isoformat(),
        "status_data": status
    }

# --- HTTP ENDPOINTS ---

@app.get("/api/employees")
async def get_employees():
    """Get all registered employees"""
    try:
        employees = []
        
        for name in authorized_users.keys():
            emp_info = get_employee_info(name)
            clock_status = employee_clock_status.get(name, {
                "clocked_in": False,
                "clock_in_time": None,
                "clock_out_time": None
            })
            
            employees.append({
                "name": name,
                "registered": True,
                "clocked_in": clock_status.get("clocked_in", False),
                "clock_in_time": clock_status.get("clock_in_time"),
                "clock_out_time": clock_status.get("clock_out_time"),
                "info": emp_info
            })
        
        return {
            "status": "ok",
            "total_employees": len(employees),
            "employees": employees
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "employees": []
        }

@app.get("/api/employees/{employee_name}/status")
async def get_employee_status(employee_name: str):
    """Get specific employee clock status"""
    if employee_name not in authorized_users:
        return {
            "status": "not_found",
            "message": f"Employee {employee_name} not registered"
        }
    
    clock_status = employee_clock_status.get(employee_name, {
        "clocked_in": False,
        "clock_in_time": None,
        "clock_out_time": None
    })
    
    emp_info = get_employee_info(employee_name)
    
    return {
        "status": "ok",
        "name": employee_name,
        "clocked_in": clock_status.get("clocked_in", False),
        "clock_in_time": clock_status.get("clock_in_time"),
        "clock_out_time": clock_status.get("clock_out_time"),
        "info": emp_info
    }

# --- FACIAL RECOGNITION ENDPOINT ---

@app.post("/api/verify-face")
async def verify_face(data: dict):
    """Verify face and clock in/out employee"""
    try:
        if "image_base64" not in data:
            return {
                "status": "error",
                "message": "No image provided",
                "success": False
            }
        
        # Decode image
        frame = decode_base64_image(data["image_base64"])
        if frame is None:
            return {
                "status": "error",
                "message": "Failed to decode image",
                "success": False
            }
        
        # Extract face embedding
        embedding = get_face_embedding(frame)
        if embedding is None:
            return {
                "status": "error",
                "message": "No face detected in image",
                "success": False,
                "face_count": 0
            }
        
        # Recognize employee
        employee_name, similarity, recognition_msg = recognize_employee(embedding)
        
        if not employee_name:
            return {
                "status": "unauthorized",
                "message": "Face not recognized. Not an authorized employee.",
                "success": False,
                "similarity": float(similarity),
                "threshold": SIMILARITY_THRESHOLD
            }
        
        # Toggle clock status
        clock_result = toggle_clock_status(employee_name)
        emp_info = get_employee_info(employee_name)
        
        return {
            "status": "ok",
            "success": True,
            "employee": {
                "name": employee_name,
                "info": emp_info
            },
            "clock": {
                "action": clock_result["action"],
                "message": clock_result["message"],
                "clocked_in": clock_result["clocked_in"],
                "timestamp": clock_result["timestamp"]
            },
            "recognition": {
                "similarity": float(similarity),
                "threshold": SIMILARITY_THRESHOLD,
                "message": recognition_msg
            }
        }
    
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "success": False
        }

# --- WEBSOCKET ENDPOINT ---

@app.websocket("/ws/stream")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("WebSocket connection accepted")

    try:
        while True:
            data = await websocket.receive_text()

            # --- HANDLE COMMANDS ---
            if data.startswith("{"):
                try:
                    command_data = json.loads(data)
                    
                    if command_data.get("action") == "get_employees":
                        await websocket.send_json({
                            "type": "employees_list",
                            "employees": list(authorized_users.keys()),
                            "count": len(authorized_users)
                        })
                    
                    elif command_data.get("action") == "get_status":
                        await websocket.send_json({
                            "type": "status_update",
                            "clock_status": employee_clock_status
                        })
                    
                    elif command_data.get("action") == "clear":
                        if conn:
                            try:
                                with conn.cursor() as cursor:
                                    cursor.execute("DELETE FROM users")
                                conn.commit()
                            except Exception as e:
                                print(f"Error clearing database: {e}")
                        authorized_users.clear()
                        employee_clock_status.clear()
                        await websocket.send_json({
                            "type": "command_response",
                            "action": "clear",
                            "message": "Database and clock status CLEARED."
                        })
                        print("Database CLEARED.")
                
                except json.JSONDecodeError:
                    pass
                continue

            # --- PROCESS IMAGE DATA ---
            print("Processing face verification from WebSocket")
            
            # Decode base64 image
            frame = decode_base64_image(data)
            if frame is None:
                await websocket.send_json({
                    "type": "error",
                    "message": "Failed to decode image"
                })
                continue
            
            # Extract embedding
            embedding = get_face_embedding(frame)
            if embedding is None:
                await websocket.send_json({
                    "type": "error",
                    "message": "No face detected in frame",
                    "success": False
                })
                continue
            
            # Recognize employee
            employee_name, similarity, msg = recognize_employee(embedding)
            
            if not employee_name:
                await websocket.send_json({
                    "type": "recognition_failed",
                    "message": "Face not recognized",
                    "success": False,
                    "similarity": float(similarity),
                    "threshold": SIMILARITY_THRESHOLD
                })
                continue
            
            # Clock in/out
            clock_result = toggle_clock_status(employee_name)
            emp_info = get_employee_info(employee_name)
            
            await websocket.send_json({
                "type": "clock_success",
                "success": True,
                "employee": {
                    "name": employee_name,
                    "info": emp_info
                },
                "clock": clock_result,
                "similarity": float(similarity)
            })
            
            print(f"✓ {clock_result['message']}")
                
    except WebSocketDisconnect:
        print("WebSocket connection closed")