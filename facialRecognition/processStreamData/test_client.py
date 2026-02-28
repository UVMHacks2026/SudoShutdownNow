#!/usr/bin/env python3
"""
WebSocket test client for Facial Recognition API
Tests the /ws/stream endpoint with real webcam footage
"""

import asyncio
import websockets
import json
import base64
import cv2
import numpy as np
from datetime import datetime

# Configuration
WS_URL = "ws://localhost:8000/ws/stream"
USE_WEBCAM = True  # Set to False to use a test image

async def send_frame(websocket, frame):
    """Encode frame to base64 and send via WebSocket"""
    _, buffer = cv2.imencode('.jpg', frame)
    jpg_as_text = base64.b64encode(buffer).decode('utf-8')
    
    # Send as data URI format
    data_uri = f"data:image/jpeg;base64,{jpg_as_text}"
    await websocket.send(data_uri)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Frame sent ({len(jpg_as_text)} bytes)")

async def send_command(websocket, action):
    """Send a command to the server"""
    command = json.dumps({"action": action})
    await websocket.send(command)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Command sent: {action}")

async def receive_messages(websocket):
    """Receive and process messages from WebSocket"""
    try:
        async for message in websocket:
            data = json.loads(message)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Response:", json.dumps(data, indent=2))
    except websockets.exceptions.ConnectionClosed:
        print("WebSocket connection closed")

async def test_with_webcam():
    """Test using live webcam feed"""
    print("=== Testing with Webcam ===")
    print(f"Connecting to {WS_URL}...")
    
    async with websockets.connect(WS_URL) as websocket:
        print("✓ Connected to WebSocket!\n")
        
        # Start receiving messages in background
        receive_task = asyncio.create_task(receive_messages(websocket))
        
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("✗ Could not open webcam")
            return
        
        print("Webcam opened. Press:")
        print("  'q' - Quit")
        print("  'r' - Register next face")
        print("  'c' - Clear database")
        print("  'space' - Send current frame\n")
        
        register_mode = False
        frame_count = 0
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Display frame
                display_frame = frame.copy()
                if register_mode:
                    cv2.putText(display_frame, "REGISTER MODE - Press SPACE to capture", 
                               (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                cv2.imshow('Facial Recognition Tester', display_frame)
                
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    print("\nQuitting...")
                    break
                elif key == ord('r'):
                    register_mode = True
                    print("\n[ACTION] Register mode activated. Press SPACE to register face.")
                    await send_command(websocket, "register")
                elif key == ord('c'):
                    print("\n[ACTION] Clearing database...")
                    await send_command(websocket, "clear")
                elif key == ord(' '):  # Space
                    frame_count += 1
                    print(f"\n[FRAME {frame_count}] Sending frame from webcam...")
                    await send_frame(websocket, frame)
                    if register_mode:
                        register_mode = False
        
        except KeyboardInterrupt:
            print("\nInterrupted by user")
        finally:
            cap.release()
            cv2.destroyAllWindows()
            receive_task.cancel()

async def test_with_dummy_image():
    """Test using a dummy/generated image"""
    print("=== Testing with Dummy Image ===")
    print(f"Connecting to {WS_URL}...")
    
    async with websockets.connect(WS_URL) as websocket:
        print("✓ Connected to WebSocket!\n")
        
        # Start receiving messages in background
        receive_task = asyncio.create_task(receive_messages(websocket))
        
        try:
            # Create dummy image (640x480 with some color)
            frame = np.ones((480, 640, 3), dtype=np.uint8) * 100
            
            # Add some text
            cv2.putText(frame, "Test Frame", (200, 240), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            
            print("1. Sending test frame...")
            await send_frame(websocket, frame)
            
            await asyncio.sleep(1)
            
            print("\n2. Testing register command...")
            await send_command(websocket, "register")
            
            await asyncio.sleep(1)
            
            print("\n3. Sending another frame (should register)...")
            await send_frame(websocket, frame)
            
            await asyncio.sleep(2)
        
        except KeyboardInterrupt:
            print("\nInterrupted by user")
        finally:
            receive_task.cancel()

async def main():
    """Main entry point"""
    print("╔════════════════════════════════════════════════╗")
    print("║   Facial Recognition WebSocket Test Client    ║")
    print("╚════════════════════════════════════════════════╝\n")
    
    # Check if webcam is available
    cap = cv2.VideoCapture(0)
    webcam_available = cap.isOpened()
    cap.release()
    
    if USE_WEBCAM and webcam_available:
        await test_with_webcam()
    else:
        if USE_WEBCAM:
            print("⚠ Webcam not available, using dummy image instead\n")
        await test_with_dummy_image()
    
    print("\n✓ Test complete!")

if __name__ == "__main__":
    asyncio.run(main())
