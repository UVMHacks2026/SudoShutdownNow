# Facial Recognition Stream Processing

This folder contains the FastAPI server and Svelte frontend components for real-time facial recognition via WebSocket.

## Files

- **sveltTo.py** - FastAPI server with WebSocket endpoint for facial recognition
- **FacialRecognitionComponent.svelte** - Svelte component for the frontend (camera + facial recognition UI)
- **test_client.py** - Python test client for testing the WebSocket connection
- **README.md** - This file

## Architecture

```
Frontend (Svelte App)
       ↓ (WebSocket)
FastAPI Server (sveltTo.py)
       ↓
Facial Recognition (InsightFace)
       ↓
PostgreSQL Database
```

## Setup & Running

### 1. Start the FastAPI Server

Make the API accessible from any network interface:

```bash
cd /Users/wenaf/Hackathon26/SudoShutdownNow
./.venv/bin/uvicorn facialRecognition.processStreamData.sveltTo:app --host 0.0.0.0 --port 8000 --reload
```

**OR** to access from your domain:

```bash
./.venv/bin/uvicorn facialRecognition.processStreamData.sveltTo:app --host 0.0.0.0 --port 8000
```

The API will be accessible at:
- Local: `http://localhost:8000`
- Domain: `http://cgswswk88cg04k4www8g8cgs.76.13.29.239.sslip.io:8000`

### 2. Integrate Svelte Component

Copy `FacialRecognitionComponent.svelte` into your Svelte app:

```bash
cp FacialRecognitionComponent.svelte /your/svelte/app/src/routes/+page.svelte
```

Or import it as a component in your existing app:

```svelte
<script>
  import FacialRecognition from '../path/to/FacialRecognitionComponent.svelte';
</script>

<FacialRecognition />
```

### 3. Test the Connection (Optional)

Use the Python test client:

```bash
./.venv/bin/python facialRecognition/processStreamData/test_client.py
```

## API Endpoints

### HTTP Endpoints

- `GET /` - Health check / API status
- `GET /health` - Detailed health status

### WebSocket Endpoint

- `ws://localhost:8000/ws/stream` - Accepts base64 image frames

## WebSocket Protocol

### Sending Data

**Image Frame (Auto-streaming):**
```
data:image/jpeg;base64,/9j/4AAQSkZJRg...
```

**Register Command:**
```json
{"action": "register"}
```

**Clear Database:**
```json
{"action": "clear"}
```

### Receiving Data

**Face Detection Response:**
```json
{
  "type": "face_detection",
  "status": "success",
  "face_count": 1,
  "faces": [
    {
      "bbox": [100, 50, 200, 150],
      "embedding": [...512 floats...],
      "matched_name": "User_1",
      "similarity": 0.85,
      "authorized": true
    }
  ]
}
```

**Registration Success:**
```json
{
  "type": "registration_success",
  "name": "User_1",
  "message": "Successfully registered User_1"
}
```

**Error Response:**
```json
{
  "type": "error",
  "message": "Failed to decode image"
}
```

## Features

✅ Real-time facial detection  
✅ Face registration  
✅ Similarity matching  
✅ Database storage  
✅ CORS enabled  
✅ WebSocket streaming  

## Configuration

Edit `sveltTo.py` to modify:

- **CORS Origins** - Add/remove allowed domains
- **WebSocket Port** - Change from 8000
- **Similarity Threshold** - Adjust face matching sensitivity

## Troubleshooting

**WebSocket Connection Refused:**
- Ensure FastAPI server is running
- Check that port 8000 is not blocked
- Verify CORS origins include your domain

**Face Not Detected:**
- Ensure good lighting
- Position face directly toward camera
- Check that InsightFace model loaded successfully

**Database Connection Error:**
- Verify DATABASE_URL in `secureFacialID.py`
- Ensure PostgreSQL is running and accessible

## Dependencies

For Python backend:
```bash
pip install fastapi uvicorn opencv-python insightface psycopg2-binary cryptography
```

For JavaScript/Svelte:
- Standard Svelte components (no extra deps needed)
- WebSocket API (browser built-in)

## License

See root `LICENSE` file
