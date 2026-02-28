import cv2
import numpy as np
from insightface.app import FaceAnalysis

# Initialize InsightFace. 
# It will download the ~330MB 'buffalo_l' model on the first run.
print("Loading InsightFace model (this may take a minute on first run to download weights)...")
app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
app.prepare(ctx_id=0, det_size=(640, 640))

cap = cv2.VideoCapture(0)

# We will store the mathematical embedding (a 512-d vector) of the authorized user here
authorized_embedding = None

def compute_similarity(embedding1, embedding2):
    # Compute Cosine Similarity between two embeddings to see how close they are
    return np.dot(embedding1, embedding2) / (np.linalg.norm(embedding1) * np.linalg.norm(embedding2))

print("\n--- INSTRUCTIONS ---")
print("Starting Secure Facial ID feed.")
print("1. Look straight into the camera.")
print("2. Press 'r' to REGISTER your face as Authorized.")
print("3. Press 'q' to QUIT at any time.")
print("--------------------\n")

while True:
    ret, frame = cap.read()
    if not ret:
        break
        
    # Analyze the frame for faces (returns bounding boxes, landmarks, and embeddings for all faces)
    faces = app.get(frame)
    display_frame = frame.copy()
    
    # Draw instructions and status on the overlay
    if authorized_embedding is None:
        cv2.putText(display_frame, "Status: WAITING FOR REGISTRATION", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        cv2.putText(display_frame, "Press 'r' to register the person in frame.", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    else:
        cv2.putText(display_frame, "Status: SECURE ID ACTIVE", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    # Process every face found in the frame
    for face in faces:
        bbox = face.bbox.astype(int)
        color = (0, 255, 255) # Yellow default for unregistered
        label = "Unknown"
        
        # If we have an authorized user, compare them
        if authorized_embedding is not None:
            # Get the embedding for the current face
            current_embedding = face.normed_embedding
            
            # Compare with our authorized embedding
            sim = compute_similarity(authorized_embedding, current_embedding)
            
            # InsightFace buffalo_l is very strict. A threshold > 0.40 is generally a very safe match.
            if sim > 0.40:
                color = (0, 255, 0) # Green for Match
                label = f"AUTHORIZED | Sim: {sim:.2f}"
            else:
                color = (0, 0, 255) # Red for Denied
                label = f"DENIED | Sim: {sim:.2f}"
                
        # Draw bounding box and label
        cv2.rectangle(display_frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), color, 2)
        cv2.putText(display_frame, label, (bbox[0], bbox[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    cv2.imshow("InsightFace Secure ID", display_frame)
    
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord('r'):
        if len(faces) == 1:
            authorized_embedding = faces[0].normed_embedding
            print("\nSuccessfully registered ONE authorized face!")
            print("Now checking live feed for matches...")
        else:
            print(f"\n[Error] Cannot register. Found {len(faces)} faces in frame, but need exactly 1.")

cap.release()
cv2.destroyAllWindows()
