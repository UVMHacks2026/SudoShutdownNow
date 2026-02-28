import cv2
import requests
import base64
import time
import json

API_URL_ANALYZE = "http://localhost:8000/analyze"
API_URL_REGISTER = "http://localhost:8000/register"
API_URL_CLEAR = "http://localhost:8000/clear_db"

def main():
    print("Starting Camera Client...")
    print("Connecting to API at: http://localhost:8000")
    print("Press 'q' to quit, 'r' to register face, 'c' to clear db.")
    
    cap = cv2.VideoCapture(0)
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame")
            break
            
        display_frame = frame.copy()
        
        # 1. Encode frame strictly as a JPG buffer, then to Base64
        _, buffer = cv2.imencode('.jpg', frame)
        jpg_as_text = base64.b64encode(buffer).decode('utf-8')
        payload = {"image_base64": jpg_as_text}
        
        key = cv2.waitKey(1) & 0xFF
        try:
            # Handle user commands
            if key == ord('q'):
                break
            elif key == ord('c'):
                resp = requests.post(API_URL_CLEAR)
                print("\nDB CLEARED:", resp.json())
                continue
            elif key == ord('r'):
                resp = requests.post(API_URL_REGISTER, json=payload)
                print("\nREGISTER RESPONSE:", resp.json())
                continue

            # 2. Main Analytics Loop
            start_time = time.time()
            response = requests.post(API_URL_ANALYZE, json=payload)
            latency = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                data = response.json()
                
                # --- Drawing the API Response on the local video feed ---
                cv2.putText(display_frame, f"API Latency: {latency:.1f}ms", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
                cv2.putText(display_frame, f"Status: {data.get('system_status')} ({data.get('registered_users_count', 0)} users)", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                
                # Draw Authentic Faces
                for face in data.get('faces', []):
                    bbox = face['bbox']
                    status = face['status']
                    if status == "AUTH":
                        color = (0, 255, 0) # Green
                        label = f"AUTH: {face['name']} ({face.get('confidence', 0):.2f})"
                    else:
                        color = (0, 0, 255) # Red
                        label = "DENIED"
                        
                    cv2.rectangle(display_frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), color, 2)
                    cv2.putText(display_frame, label, (bbox[0], bbox[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                
                # Draw Tracked Bodies
                for body in data.get('bodies', []):
                    bbox = body['bbox']
                    status = body['status']
                    if status == "TRACKING":
                        color = (0, 165, 255) # Orange
                        label = f"TRACKING: {body['name']}"
                    else:
                        color = (0, 255, 0) # Green
                        label = f"BODY: {body['name']}"
                    
                    cv2.rectangle(display_frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), color, 1)
                    cv2.putText(display_frame, label, (bbox[0], bbox[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
                    
            else:
                print(f"API Error {response.status_code}")

        except requests.exceptions.ConnectionError:
            cv2.putText(display_frame, "OFFLINE: Waiting for FastAPI server...", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            time.sleep(1) # prevent terminal spam
            
        cv2.imshow("Camera Streaming Client", display_frame)

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
