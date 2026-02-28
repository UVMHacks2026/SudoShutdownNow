from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
import io

# Need to update to active facial recognition code, this is test for now
import facialRecTest

app = FastAPI()

# ---
origins = [
    "http://cgswswk88cg04k4www8g8cgs.76.13.29.239.sslip.io/",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.websocket("/ws/stream")
async def websocket_endpoint(websocket):
    await websocket.accept()
    print("WebSocket connection accepted")
    
    register_next_face = False

    try:
        while True:
            data = await websocket.receive_text()
            print("Received string from WebSocket")
            
            # Parse the incoming data as an image
            if "," in data:
                base_64_data = data.split(",")[1]
            else:
                base_64_data = data

    except Exception as e:
        print(f"WebSocket connection error: {e}")