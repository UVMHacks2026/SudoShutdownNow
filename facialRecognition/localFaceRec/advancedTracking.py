import cv2
import numpy as np
from insightface.app import FaceAnalysis
import json
import os
import sqlite3
import pickle
from cryptography.fernet import Fernet
from ultralytics import YOLO
import base64

class FacialSecuritySystem:
    def __init__(self):
        # --- 1. CONFIGURATION & SECRETS ---
        self.secrets_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'gemeniFacialAnalysis', 'secrets.json')
        self.db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'facial_data.db')
        
        try:
            with open(self.secrets_path, 'r') as f:
                secrets = json.load(f)
            fernet_key = secrets.get("FERNET_KEY")
            if not fernet_key:
                raise ValueError("FERNET_KEY not found in secrets.json")
            self.cipher_suite = Fernet(fernet_key.encode('utf-8'))
        except Exception as e:
            print(f"CRITICAL ERROR loading secrets: {e}")
            print("Please run generate_key.py first to create your Fernet key.")
            raise e

        # --- 2. DATABASE SETUP ---
        self.conn = self.init_db()
        self.authorized_users = self.load_users()
        print(f"Loaded {len(self.authorized_users)} authorized users from database.")

        # --- 3. INFRASTRUCTURE SETUP ---
        print("Loading InsightFace model...")
        self.face_app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
        self.face_app.prepare(ctx_id=0, det_size=(640, 640))

        print("Loading YOLOv8n Body Tracking model...")
        self.body_model = YOLO("yolov8n.pt")
        
        self.last_known_authorized_centers = {} # name -> (x,y)
        self.body_tracking_active_for = None

    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, embedding BLOB)''')
        conn.commit()
        return conn

    def save_user(self, name, embedding):
        serialized_embedding = pickle.dumps(embedding)
        encrypted_embedding = self.cipher_suite.encrypt(serialized_embedding)
        try:
            c = self.conn.cursor()
            c.execute("INSERT OR REPLACE INTO users (name, embedding) VALUES (?, ?)", (name, encrypted_embedding))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error saving user: {e}")
            return False

    def load_users(self):
        c = self.conn.cursor()
        c.execute("SELECT name, embedding FROM users")
        users = {}
        for row in c.fetchall():
            name, encrypted_embedding = row
            try:
                decrypted_embedding = self.cipher_suite.decrypt(encrypted_embedding)
                embedding = pickle.loads(decrypted_embedding)
                users[name] = embedding
            except Exception as e:
                print(f"Error decrypting user {name}: {e}")
        return users

    def compute_similarity(self, embedding1, embedding2):
        return np.dot(embedding1, embedding2) / (np.linalg.norm(embedding1) * np.linalg.norm(embedding2))

    def process_image(self, b64_image_string, isFirstTimeSetup=False, setup_name=None):
        """
        b64_image_string: e.g., 'data:image/jpeg;base64,...'
        isFirstTimeSetup: bool indicating whether to add a new user.
        setup_name: required if isFirstTimeSetup is True, the name of the new employee.
        """
        # Parse base64 string
        if "," in b64_image_string:
            b64_data = b64_image_string.split(",")[1]
        else:
            b64_data = b64_image_string

        try:
            image_data = base64.b64decode(b64_data)
        except Exception:
            return {"error": "Invalid base64 encoding"}

        np_arr = np.frombuffer(image_data, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if frame is None:
            return {"error": "Could not decode image"}

        faces = self.face_app.get(frame)
        
        # 1. First-Time Setup
        if isFirstTimeSetup:
            if not setup_name:
                return {"error": "setup_name is required for First-Time Setup"}
            if len(faces) == 1:
                embedding = faces[0].normed_embedding
                if self.save_user(setup_name, embedding):
                    self.authorized_users[setup_name] = embedding
                    
                    c = self.conn.cursor()
                    c.execute("SELECT id FROM users WHERE name=?", (setup_name,))
                    user_id = c.fetchone()[0]
                    
                    return {
                        "status": "SUCCESS",
                        "employee_id": user_id,
                        "name": setup_name,
                        "message": f"Successfully registered {setup_name}."
                    }
                else:
                    return {"error": "Failed to save user to DB"}
            else:
                return {"error": f"Cannot register. Found {len(faces)} faces in frame, need exactly 1."}
        
        # 2. Standard Processing
        body_results = self.body_model(frame, classes=[0], verbose=False)
        bodies = []
        if len(body_results) > 0:
            bodies = body_results[0].boxes.xyxy.cpu().numpy().astype(int)

        currently_seen_authorized = []
        best_match_name_overall = None
        best_sim_overall = 0.0

        for face in faces:
            face_bbox = face.bbox.astype(int)
            face_center = (int((face_bbox[0] + face_bbox[2])/2), int((face_bbox[1] + face_bbox[3])/2))
            
            best_match_name = None
            best_sim = 0.0
            
            for name, auth_emb in self.authorized_users.items():
                sim = self.compute_similarity(auth_emb, face.normed_embedding)
                if sim > 0.40 and sim > best_sim:
                    best_sim = sim
                    best_match_name = name
                    
            if best_match_name:
                currently_seen_authorized.append(best_match_name)
                self.last_known_authorized_centers[best_match_name] = face_center
                if best_sim > best_sim_overall:
                    best_sim_overall = best_sim
                    best_match_name_overall = best_match_name

        if len(currently_seen_authorized) > 0:
            return {
                "present": True,
                "name": best_match_name_overall,
                "status": "SECURE"
            }
            
        # 3. Fallback Tracking Logic
        if len(self.authorized_users) > 0 and len(currently_seen_authorized) == 0:
            for body_bbox in bodies:
                body_center = (int((body_bbox[0] + body_bbox[2])/2), int((body_bbox[1] + body_bbox[3])/2))
                assumed_name = None
                closest_dist = float('inf')
                
                for name, last_face_center in self.last_known_authorized_centers.items():
                    dist = np.sqrt((body_center[0] - last_face_center[0])**2 + (body_center[1] - last_face_center[1])**2)
                    if dist < 300 and dist < closest_dist:
                        closest_dist = dist
                        assumed_name = name
                
                if assumed_name:
                    self.last_known_authorized_centers[assumed_name] = body_center
                    return {
                        "present": True,
                        "name": assumed_name,
                        "status": "FALLBACK_TRACKING"
                    }

        return {
            "present": False,
            "name": None,
            "status": "UNRECOGNIZED"
        }

if __name__ == "__main__":
    system = FacialSecuritySystem()
    print("FacialSecuritySystem module loaded successfully.")
