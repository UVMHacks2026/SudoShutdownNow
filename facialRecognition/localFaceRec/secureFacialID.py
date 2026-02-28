import cv2
import numpy as np
from insightface.app import FaceAnalysis
import json
import os
import psycopg2
import pickle
from cryptography.fernet import Fernet
from ultralytics import YOLO

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
            user=os.environ.get('USER', 'postgres'), # Uses current macOS user by default
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
        print("Please ensure PostgreSQL is running and the 'facial_recognition' database exists.")
        exit(1)

def save_user(conn, name, embedding):
    # Serialize and encrypt the embedding
    serialized_embedding = pickle.dumps(embedding)
    encrypted_embedding = cipher_suite.encrypt(serialized_embedding)
    try:
        c = conn.cursor()
        # PostgreSQL uses ON CONFLICT instead of INSERT OR REPLACE
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
        conn.rollback() # Important in postgres
        return False

def load_users(conn):
    c = conn.cursor()
    c.execute("SELECT name, embedding FROM users")
    users = {}
    for row in c.fetchall():
        name = row[0]
        # psycopg2 returns a memoryview for BYTEA, need to convert to bytes
        encrypted_embedding = bytes(row[1]) 
        try:
            decrypted_embedding = cipher_suite.decrypt(encrypted_embedding)
            embedding = pickle.loads(decrypted_embedding)
            users[name] = embedding
        except Exception as e:
            print(f"Error decrypting user {name}: {e}")
    return users

conn = init_db()
authorized_users = load_users(conn)
print(f"Loaded {len(authorized_users)} authorized users from database.")


# --- 3. INFRASTRUCTURE SETUP ---
def compute_similarity(embedding1, embedding2):
    return np.dot(embedding1, embedding2) / (np.linalg.norm(embedding1) * np.linalg.norm(embedding2))

print("Loading InsightFace model...")
face_app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
face_app.prepare(ctx_id=0, det_size=(640, 640))

print("Loading YOLOv8n Body Tracking model...")
body_model = YOLO("yolov8n.pt") # Will download a tiny 6MB model on first run

cap = cv2.VideoCapture(0)

print("\n--- INSTRUCTIONS ---")
print("1. Look straight into the camera.")
print("2. Press 'r' to REGISTER your face as a new Authorized User.")
print("3. Press 'c' to CLEAR the database.")
print("4. Press 'q' to QUIT at any time.")
print("--------------------\n")

# State tracking for the fallback system
# If we saw an authorized user recently, and lose their face, we start tracking bodies.
last_known_authorized_centers = {} # name -> (x,y)
body_tracking_active_for = None 

while True:
    ret, frame = cap.read()
    if not ret:
        break
        
    display_frame = frame.copy()
    
    # 1. Run YOLO Body Detection
    body_results = body_model(frame, classes=[0], verbose=False) # class 0 is person
    bodies = []
    if len(body_results) > 0:
        bodies = body_results[0].boxes.xyxy.cpu().numpy().astype(int)
        
    # 2. Run Facial Detection
    faces = face_app.get(frame)
    
    currently_seen_authorized = []

    # Process all faces
    for face in faces:
        face_bbox = face.bbox.astype(int)
        face_center = (int((face_bbox[0] + face_bbox[2])/2), int((face_bbox[1] + face_bbox[3])/2))
        
        best_match_name = None
        best_sim = 0.0
        
        # Compare against DB
        for name, auth_emb in authorized_users.items():
            sim = compute_similarity(auth_emb, face.normed_embedding)
            if sim > 0.40 and sim > best_sim:
                best_sim = sim
                best_match_name = name
                
        if best_match_name:
            currently_seen_authorized.append(best_match_name)
            last_known_authorized_centers[best_match_name] = face_center
            
            color = (0, 255, 0) # Green 
            label = f"AUTH: {best_match_name} ({best_sim:.2f})"
            # Draw Face Box
            cv2.rectangle(display_frame, (face_bbox[0], face_bbox[1]), (face_bbox[2], face_bbox[3]), color, 2)
            cv2.putText(display_frame, label, (face_bbox[0], face_bbox[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            
            # Since we clearly see their face, we map them directly to a body 
            for body_bbox in bodies:
                # Is face center inside body bbox?
                if (body_bbox[0] < face_center[0] < body_bbox[2] and 
                    body_bbox[1] < face_center[1] < body_bbox[3]):
                    cv2.rectangle(display_frame, (body_bbox[0], body_bbox[1]), (body_bbox[2], body_bbox[3]), color, 1)
                    cv2.putText(display_frame, f"BODY: {best_match_name}", (body_bbox[0], body_bbox[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        
        else:
            # Unrecognized Face
            cv2.rectangle(display_frame, (face_bbox[0], face_bbox[1]), (face_bbox[2], face_bbox[3]), (0, 0, 255), 2)
            cv2.putText(display_frame, "DENIED", (face_bbox[0], face_bbox[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)


    # 3. Fallback Body Tracking Logic
    # If we have registered users, but NO authorized faces are currently visible...
    if len(authorized_users) > 0 and len(currently_seen_authorized) == 0:
        
        cv2.putText(display_frame, "FACE LOST: FALLBACK TRACKING ACTIVE", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
        
        # We try to find bodies that might belong to the last known authorized users
        for body_bbox in bodies:
            body_center = (int((body_bbox[0] + body_bbox[2])/2), int((body_bbox[1] + body_bbox[3])/2))
            
            # Very naive heuristic: If a body is near where we last saw an authorized face, assume it's them.
            # In a real system, you'd use DeepSORT or ByteTrack for temporal ID tracking across frames.
            assumed_name = None
            closest_dist = float('inf')
            
            for name, last_face_center in last_known_authorized_centers.items():
                dist = np.sqrt((body_center[0] - last_face_center[0])**2 + (body_center[1] - last_face_center[1])**2)
                # If body center is reasonably close to where face was (e.g., within 300 pixels)
                if dist < 300 and dist < closest_dist:
                    closest_dist = dist
                    assumed_name = name
            
            if assumed_name:
                color = (0, 165, 255) # Orange for fallback tracking
                cv2.rectangle(display_frame, (body_bbox[0], body_bbox[1]), (body_bbox[2], body_bbox[3]), color, 2)
                cv2.putText(display_frame, f"TRACKING: {assumed_name} (Body)", (body_bbox[0], body_bbox[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                # Update last known center to the body center so we keep tracking them
                last_known_authorized_centers[assumed_name] = body_center

    else:
        cv2.putText(display_frame, f"SECURE System Active (Users: {len(authorized_users)})", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)


    cv2.imshow("Advanced Secure ID & Tracking", display_frame)
    
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord('c'):
        # Clear the database
        conn.cursor().execute("DELETE FROM users")
        conn.commit()
        authorized_users.clear()
        last_known_authorized_centers.clear()
        print("\nDatabase CLEARED.")
    elif key == ord('r'):
        if len(faces) == 1:
            name = f"User_{len(authorized_users) + 1}"
            embedding = faces[0].normed_embedding
            if save_user(conn, name, embedding):
                authorized_users[name] = embedding
                print(f"\nSuccessfully registered {name} safely to the DB!")
        else:
            print(f"\n[Error] Cannot register. Found {len(faces)} faces in frame, need exactly 1.")

cap.release()
conn.close()
cv2.destroyAllWindows()
