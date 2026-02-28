import cv2
import numpy as np
from insightface.app import FaceAnalysis
import json
import os
import psycopg2
import pickle
import base64
from cryptography.fernet import Fernet
from ultralytics import YOLO
import time
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

# --- 1. CONFIGURATION & SECRETS ---
secrets_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'gemeniFacialAnalysis', 'secrets.json')

try:
    with open(secrets_path, 'r') as f:
        secrets = json.load(f)
    fernet_key = secrets.get("FERNET_KEY")
    if not fernet_key:
        raise ValueError("FERNET_KEY not found in secrets.json")
    cipher_suite = Fernet(fernet_key.encode('utf-8'))
except Exception as e:
    print(f"CRITICAL ERROR loading secrets: {e}")
    print("Please run generate_key.py first to create your Fernet key.")
    exit(1)

# --- 2. DATABASE SETUP (PostgreSQL) ---
def init_db():
    try:
        conn = psycopg2.connect(
            dbname="facial_recognition",
            user=os.environ.get('USER', 'postgres'),
            host="localhost",
            port="5432"
        )
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users
                     (id SERIAL PRIMARY KEY, name TEXT UNIQUE, embedding BYTEA)''')
        conn.commit()
        return conn
    except Exception as e:
        print(f"CRITICAL ERROR connecting to PostgreSQL: {e}")
        exit(1)

def save_user(conn, name, embedding):
    serialized_embedding = pickle.dumps(embedding)
    encrypted_embedding = cipher_suite.encrypt(serialized_embedding)
    try:
        c = conn.cursor()
        c.execute("""
            INSERT INTO users (name, embedding) 
            VALUES (%s, %s)
            ON CONFLICT (name) 
            DO UPDATE SET embedding = EXCLUDED.embedding
        """, (name, psycopg2.Binary(encrypted_embedding)))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error saving user: {e}")
        conn.rollback()
        return False

def load_users(conn):
    c = conn.cursor()
    c.execute("SELECT name, embedding FROM users")
    users = {}
    for row in c.fetchall():
        name = row[0]
        encrypted_embedding = bytes(row[1]) 
        try:
            decrypted_embedding = cipher_suite.decrypt(encrypted_embedding)
            embedding = pickle.loads(decrypted_embedding)
            users[name] = embedding
        except Exception as e:
            print(f"Error decrypting user {name}: {e}")
    return users


# --- 3. INFRASTRUCTURE SETUP ---
def compute_similarity(embedding1, embedding2):
    return np.dot(embedding1, embedding2) / (np.linalg.norm(embedding1) * np.linalg.norm(embedding2))

print("Loading InsightFace model (Memory Optimized)...")
face_app = FaceAnalysis(name='buffalo_l', allowed_modules=['detection', 'recognition'], providers=['CPUExecutionProvider'])
face_app.prepare(ctx_id=0, det_size=(640, 640))

print("Loading YOLOv8n Body Tracking model...")
body_model = YOLO("yolov8n.pt") 

conn = init_db()
authorized_users = load_users(conn)
print(f"Loaded {len(authorized_users)} authorized users from database.")

# State tracking for fallback system (global state for the server)
last_known_authorized_centers = {} # name -> (x,y)

# --- 4. FASTAPI APP ---
app = FastAPI(title="SudoShutdownNow Secure Facial ID API")

class FrameRequest(BaseModel):
    image_base64: str

def decode_base64_image(base64_str: str):
    if "," in base64_str:
        base64_str = base64_str.split(",")[1]
    try:
        img_data = base64.b64decode(base64_str)
        np_arr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Failed to decode image")
        return img
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid base64 image data: {str(e)}")


@app.post("/analyze")
async def analyze_frame(request: FrameRequest):
    global last_known_authorized_centers
    
    frame = decode_base64_image(request.image_base64)
    response_data = {"faces": [], "bodies": [], "system_status": "SECURE"}
    
    # 1. Run YOLO Body Detection
    body_results = body_model(frame, classes=[0], verbose=False)
    bodies = []
    if len(body_results) > 0:
        bodies = body_results[0].boxes.xyxy.cpu().numpy().astype(int)
        
    # 2. Run Facial Detection
    faces = face_app.get(frame)
    currently_seen_authorized = []

    # Process all faces
    for face in faces:
        face_bbox = face.bbox.astype(int).tolist()
        face_center = (int((face_bbox[0] + face_bbox[2])/2), int((face_bbox[1] + face_bbox[3])/2))
        
        best_match_name = None
        best_sim = 0.0
        
        # Compare against DB
        for name, auth_emb in authorized_users.items():
            sim = compute_similarity(auth_emb, face.normed_embedding)
            if sim > 0.40 and sim > best_sim:
                best_sim = float(sim)
                best_match_name = name
                
        if best_match_name:
            currently_seen_authorized.append(best_match_name)
            last_known_authorized_centers[best_match_name] = face_center
            
            response_data["faces"].append({
                "status": "AUTH",
                "name": best_match_name,
                "confidence": best_sim,
                "bbox": face_bbox
            })
            
            # Since we clearly see their face, we map them directly to a body 
            for body_bbox in bodies:
                if (body_bbox[0] < face_center[0] < body_bbox[2] and 
                    body_bbox[1] < face_center[1] < body_bbox[3]):
                    response_data["bodies"].append({
                        "status": "BODY",
                        "name": best_match_name,
                        "bbox": body_bbox.tolist()
                    })
        else:
            response_data["faces"].append({
                "status": "DENIED",
                "name": "Unknown",
                "bbox": face_bbox
            })

    # 3. Fallback Body Tracking Logic
    if len(authorized_users) > 0 and len(currently_seen_authorized) == 0:
        response_data["system_status"] = "FALLBACK_TRACKING"
        
        for body_bbox in bodies:
            body_center = (int((body_bbox[0] + body_bbox[2])/2), int((body_bbox[1] + body_bbox[3])/2))
            
            assumed_name = None
            closest_dist = float('inf')
            
            for name, last_face_center in last_known_authorized_centers.items():
                dist = np.sqrt((body_center[0] - last_face_center[0])**2 + (body_center[1] - last_face_center[1])**2)
                if dist < 300 and dist < closest_dist:
                    closest_dist = dist
                    assumed_name = name
            
            if assumed_name:
                response_data["bodies"].append({
                    "status": "TRACKING",
                    "name": assumed_name,
                    "bbox": body_bbox.tolist()
                })
                # Update last known center
                last_known_authorized_centers[assumed_name] = body_center

    response_data["registered_users_count"] = len(authorized_users)
    return response_data

@app.post("/register")
async def register_user(request: FrameRequest):
    frame = decode_base64_image(request.image_base64)
    faces = face_app.get(frame)
    if len(faces) != 1:
        raise HTTPException(status_code=400, detail=f"Cannot register. Found {len(faces)} faces in frame, need exactly 1.")
    
    name = f"User_{len(authorized_users) + 1}"
    embedding = faces[0].normed_embedding
    if save_user(conn, name, embedding):
        authorized_users[name] = embedding
        return {"status": "success", "message": f"Successfully registered {name} safely to the DB!"}
    else:
        raise HTTPException(status_code=500, detail="Database write failure.")

@app.post("/clear_db")
async def clear_database():
    try:
        conn.cursor().execute("DELETE FROM users")
        conn.commit()
        authorized_users.clear()
        last_known_authorized_centers.clear()
        return {"status": "success", "message": "Database cleared."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
