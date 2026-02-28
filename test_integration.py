import cv2
import base64
import time
import json
from facialRecognition.localFaceRec.secureFacialID import FacialSecuritySystem

def capture_base64_frame(cap):
    ret, frame = cap.read()
    if not ret:
        raise RuntimeError("Failed to read from webcam")
    _, buffer = cv2.imencode('.jpg', frame)
    return base64.b64encode(buffer).decode('utf-8')

def main():
    print("--------------------------------------------------")
    print("1. Initializing FacialSecuritySystem as an Import...")
    security = FacialSecuritySystem()
    
    print("\n[Optional] Clearing Database for a clean test...")
    security.conn.cursor().execute("DELETE FROM users")
    security.conn.commit()
    security.authorized_users.clear()
    
    print("\n2. Activating Webcam...")
    cap = cv2.VideoCapture(0)
    time.sleep(2) # brief pause to let camera sensor adjust to light
    
    print("\n--- TEST A: Normal processing on an UNKNOWN user ---")
    b64_img = capture_base64_frame(cap)
    result_a = security.process_frame(b64_img)
    print("Result ->", json.dumps(result_a, indent=4))
    
    print("\n--- TEST B: First Time Setup (Registration) ---")
    print("Simulating First Time Setup pipeline. Please look into the camera...")
    time.sleep(1)
    b64_img = capture_base64_frame(cap)
    new_name = "Will_Real_Test"
    print(f"Registering base64 stream as '{new_name}'...")
    result_b = security.register_user(b64_img, new_name)
    print("Result ->", json.dumps(result_b, indent=4))
    
    print("\n--- TEST C: Normal processing AFTER registration ---")
    print("Simulating Standard Access pipeline...")
    b64_img = capture_base64_frame(cap)
    result_c = security.process_frame(b64_img)
    print("Result ->", json.dumps(result_c, indent=4))
    
    cap.release()
    print("\nTests complete!")
    print("--------------------------------------------------")

if __name__ == "__main__":
    main()
