import os
import json
import time
import cv2
from google import genai
from PIL import Image

# 1. Load the Gemini API Key
secrets_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'secrets.json')
with open(secrets_path, 'r') as f:
    secrets = json.load(f)

# Initialize the Gemini client
client = genai.Client(api_key=secrets.get("GEMINI_API_KEY"))

# 2. Define the System Instructions/Prompt
# This prompt will be sent with every frame. We want it to be concise and focused on our goal.
SYSTEM_PROMPT = """
You are acting as a real-time facial analysis system. 
Analyze the face in this image frame and describe:
1. The primary emotion or expression you detect.
2. The general age range (e.g., young adult, middle-aged).
3. Any notable accessories (glasses, hats) or facial hair.
Be extremely concise. Give your answer as a bulleted list.
Do not attempt to identify who the person is.
"""

# 3. Setup OpenCV Webcam Capture
# 0 usually refers to the default built-in webcam.
cap = cv2.VideoCapture(0)

print("Starting Realtime Facial Recognition feed. Press 'q' to quit.")

# We don't want to spam the Gemini API continuously (you will hit rate limits fast).
# We'll set a delay (in seconds) between API calls, while keeping the video feed smooth.
API_CALL_INTERVAL = 5.0  # Analyze a frame every 5 seconds
last_api_call_time = 0
last_analysis_result = "Analyzing..."

while True:
    # Capture frame-by-frame
    ret, frame = cap.read()

    # If the frame was not grabbed successfully, break the loop
    if not ret:
        print("Failed to grab frame from webcam")
        break

    # Get the current time
    current_time = time.time()

    # --- API GATING LOGIC ---
    # Only send a frame to Gemini every API_CALL_INTERVAL seconds
    if (current_time - last_api_call_time) > API_CALL_INTERVAL:
        last_api_call_time = current_time
        
        # OpenCV captures in BGR format, but PIL and Gemini expect RGB format.
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Convert the OpenCV frame (NumPy array) into a PIL Image object
        pil_image = Image.fromarray(rgb_frame)
        
        try:
            print("Sending frame to Gemini for analysis...")
            # Send the frame and prompt to the Gemini API
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[pil_image, SYSTEM_PROMPT]
            )
            # Store the result to paint onto the video feed
            last_analysis_result = response.text.replace('*', '').strip()
            print("\n--- New Analysis ---")
            print(last_analysis_result)
        
        except Exception as e:
            print(f"Error calling Gemini API: {e}")
            last_analysis_result = "API Error. Check console."


    # --- VIDEO OVERLAY LOGIC ---
    # Draw instructions on the video feed
    cv2.putText(frame, "Press 'q' to quit", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    
    # Draw the latest Gemini analysis on the video feed.
    # Because the analysis is usually multiple lines, we need to split it and draw line by line.
    y0, dy = 60, 25
    for i, line in enumerate(last_analysis_result.split('\n')):
        if line.strip(): # Skip empty lines
            y = y0 + i*dy
            # Draw black text with a thin white outline for readability against any background
            cv2.putText(frame, line, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 4) # Outline
            cv2.putText(frame, line, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2) # Text

    # Display the resulting frame in a window
    cv2.imshow("Realtime Facial Analysis (Gemini API)", frame)

    # Wait for 1 ms and check if the 'q' key was pressed to exit
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# When everything is done, release the capture object and close the window
cap.release()
cv2.destroyAllWindows()
