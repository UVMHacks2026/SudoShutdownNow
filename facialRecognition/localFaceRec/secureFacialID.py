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

class FacialSecuritySystem:
    def __init__(self):
        # --- 1. CONFIGURATION & SECRETS ---
        secrets_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'gemeniFacialAnalysis', 'secrets.json')
        
        try:
            with open(secrets_path, 'r') as f:
                secrets = json.load(f)
            self.fernet_key = secrets.get("FERNET_KEY")
            if not self.fernet_key:
                raise ValueError("FERNET_KEY not found in secrets.json")
            self.cipher_suite = Fernet(self.fernet_key.encode('utf-8'))
        except Exception as e:
            raise RuntimeError(f"CRITICAL ERROR loading secrets: {e}\nPlease run generate_key.py first to create your Fernet key.")

        # --- 2. DATABASE SETUP ---
        self.conn = self._init_db()
        self.authorized_users = self._load_users()
        print(f"[SecuritySystem] Loaded {len(self.authorized_users)} authorized users from database.")

        # --- 3. INFRASTRUCTURE SETUP ---
        print("[SecuritySystem] Loading InsightFace model (Memory Optimized)...")
        self.face_app = FaceAnalysis(name='buffalo_l', allowed_modules=['detection', 'recognition'], providers=['CPUExecutionProvider'])
        self.face_app.prepare(ctx_id=0, det_size=(640, 640))

        print("[SecuritySystem] Loading YOLOv8n Body Tracking model...")
        self.body_model = YOLO("yolov8n.pt") 
        
        # State tracking for fallback system
        self.last_known_authorized_centers = {} # name -> (x,y)
        
    def _init_db(self):
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
            raise RuntimeError(f"CRITICAL ERROR connecting to PostgreSQL: {e}")

    def _save_user(self, name, embedding):
        serialized_embedding = pickle.dumps(embedding)
        encrypted_embedding = self.cipher_suite.encrypt(serialized_embedding)
        try:
            c = self.conn.cursor()
            c.execute("""
                INSERT INTO users (name, embedding) 
                VALUES (%s, %s)
                RETURNING id
            """, (name, psycopg2.Binary(encrypted_embedding)))
            new_id = c.fetchone()[0]
            self.conn.commit()
            return new_id
        except Exception as e:
            print(f"Error saving user: {e}")
            self.conn.rollback()
            return None

    def _load_users(self):
        c = self.conn.cursor()
        c.execute("SELECT name, embedding FROM users")
        users = {}
        for row in c.fetchall():
            name = row[0]
            encrypted_embedding = bytes(row[1]) 
            try:
                decrypted_embedding = self.cipher_suite.decrypt(encrypted_embedding)
                embedding = pickle.loads(decrypted_embedding)
                users[name] = embedding
            except Exception as e:
                print(f"Error decrypting user {name}: {e}")
        return users

    def _compute_similarity(self, embedding1, embedding2):
        return np.dot(embedding1, embedding2) / (np.linalg.norm(embedding1) * np.linalg.norm(embedding2))

    def _decode_base64_image(self, base64_str: str):
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
            raise ValueError(f"Invalid base64 image data: {str(e)}")


    # ==========================================
    # PUBLIC EXPORTED FUNCTIONS
    # ==========================================

    def register_user(self, base64_img: str, name: str) -> dict:
        """
        Takes a base64 JPG and a name, and registers the face as a new authorized employee.
        """
        try:
            frame = self._decode_base64_image(base64_img)
        except ValueError as e:
            return {"success": False, "error": str(e)}
            
        faces = self.face_app.get(frame)
        if len(faces) != 1:
            return {"success": False, "error": f"Found {len(faces)} faces in frame, need exactly 1."}
        
        embedding = faces[0].normed_embedding
        
        # Check if they already exist so we don't duplicate
        for existing_name, auth_emb in self.authorized_users.items():
            sim = self._compute_similarity(auth_emb, embedding)
            if sim > 0.40:
                return {"success": False, "error": f"Face already registered as {existing_name}"}

        new_id = self._save_user(name, embedding)
        if new_id:
            self.authorized_users[name] = embedding
            return {"success": True, "employee_id": new_id, "name": name}
        else:
            return {"success": False, "error": "Database write failure. Name may already exist."}

    def process_frame(self, base64_img: str) -> dict:
        """
        Takes a base64 JPG, searches for authorized employees, and handles fallback body tracking.
        Returns whether an employee is present, and their name/id if so.
        """
        try:
            frame = self._decode_base64_image(base64_img)
        except ValueError as e:
            return {"error": str(e)}
            
        response_data = {
            "is_employee_present": False,
            "employee_name": None,
            "system_status": "SECURE",
            "faces_detected": 0
        }
        
        # 1. Run YOLO Body Detection
        body_results = self.body_model(frame, classes=[0], verbose=False)
        bodies = []
        if len(body_results) > 0:
            bodies = body_results[0].boxes.xyxy.cpu().numpy().astype(int)
            
        # 2. Run Facial Detection
        faces = self.face_app.get(frame)
        response_data["faces_detected"] = len(faces)
        currently_seen_authorized = []

        # Process all faces
        for face in faces:
            face_bbox = face.bbox.astype(int).tolist()
            face_center = (int((face_bbox[0] + face_bbox[2])/2), int((face_bbox[1] + face_bbox[3])/2))
            
            best_match_name = None
            best_sim = 0.0
            
            # Compare against DB
            for name, auth_emb in self.authorized_users.items():
                sim = self._compute_similarity(auth_emb, face.normed_embedding)
                if sim > 0.40 and sim > best_sim:
                    best_sim = float(sim)
                    best_match_name = name
                    
            if best_match_name:
                currently_seen_authorized.append(best_match_name)
                self.last_known_authorized_centers[best_match_name] = face_center
                
                # We found an employee!
                response_data["is_employee_present"] = True
                response_data["employee_name"] = best_match_name
                response_data["confidence"] = best_sim

        # 3. Fallback Body Tracking Logic
        # If no face is seen, check if their body is still in the frame
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
                    # We assume the employee is still present based on body location
                    self.last_known_authorized_centers[assumed_name] = body_center
                    response_data["is_employee_present"] = True
                    response_data["employee_name"] = assumed_name
                    response_data["system_status"] = "FALLBACK_TRACKING"
                    break # Track one employee for now

        return response_data