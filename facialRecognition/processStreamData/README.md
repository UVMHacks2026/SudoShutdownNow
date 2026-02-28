# Employee Clock-In System

A real-time facial recognition system for employee clock-in/clock-out verification. Uses InsightFace for facial recognition, FastAPI for REST/WebSocket endpoints, and PostgreSQL for employee data storage.

## System Overview

The system captures employee faces via webcam, performs facial recognition against a database of registered employees, and automatically toggles their clock-in/clock-out status, returning confirmation messages with employee information and timestamps.

```
Employee Camera (Webcam)
       ↓
Svelte Frontend (FacialRecognitionComponent)
       ↓ (WebSocket base64 frames)
FastAPI Server (sveltTo.py)
       ↓
InsightFace (512-dim embedding extraction)
       ↓
Face Recognition & Clock Status Management
       ↓ (REST/WebSocket responses)
Svelte UI (displays clock confirmation + employee info)
```

## Files

- **sveltTo.py** - FastAPI server with REST API and WebSocket endpoints
- **FacialRecognitionComponent.svelte** - Svelte component for camera capture and real-time facial recognition UI
- **test_client.py** - Python client for testing WebSocket functionality
- **secureFacialID.py** - Core facial recognition module (imported from parent directories)
- **README.md** - This documentation

## Setup & Running

### 1. Prerequisites

- Python 3.10+ with pip/venv
- PostgreSQL database (remote or local)
- Modern web browser with WebRTC support
- Webcam

### 2. Start the FastAPI Server

**From project root directory:**

```bash
cd /Users/wenaf/Hackathon26/SudoShutdownNow
source .venv/bin/activate

# Run on port 8000 with hot-reload
python -m uvicorn facialRecognition.processStreamData.sveltTo:app --host 0.0.0.0 --port 8000 --reload

# Or run on port 8001
python -m uvicorn facialRecognition.processStreamData.sveltTo:app --host 0.0.0.0 --port 8001
```

**Output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

The API will be accessible at:
- **Local:** `http://localhost:8000`
- **Domain:** `http://cgswswk88cg04k4www8g8cgs.76.13.29.239.sslip.io:8000`
- **WebSocket:** `ws://localhost:8000/ws/stream`

### 3. Integrate Svelte Frontend

**Option A: Use as standalone component**

```bash
cp FacialRecognitionComponent.svelte /your/svelte/app/src/routes/+page.svelte
```

**Option B: Import as component in existing page**

```svelte
<script>
  import FacialRecognition from '../path/to/FacialRecognitionComponent.svelte';
</script>

<FacialRecognition />
```

### 4. Test the System

**Using Python test client:**

```bash
python facialRecognition/processStreamData/test_client.py
```

Commands:
- `q` - Quit
- `space` - Send current frame
- `r` - Register new employee (for setup)
- `c` - Clear database (clear all data)

**Using curl (verify face endpoint):**

```bash
# First, capture a base64 image (or use an existing one)
curl -X POST http://localhost:8000/api/verify-face \
  -H "Content-Type: application/json" \
  -d '{"image_base64": "data:image/jpeg;base64,/9j/4AAQSkZJRg..."}'
```

**Using curl (list employees):**

```bash
curl http://localhost:8000/api/employees
```

## API Endpoints

### REST/HTTP Endpoints

**Health Check:**
```
GET /
GET /health
```

**Verify Face & Clock In/Out:**
```
POST /api/verify-face
Content-Type: application/json

Request:
{
  "image_base64": "data:image/jpeg;base64,/9j/4AAQSkZJRg..."
}

Response (Success):
{
  "status": "ok",
  "success": true,
  "employee": {
    "name": "User_1",
    "info": {
      "name": "User_1",
      "id": 1,
      "created_at": "2025-01-15T10:00:00",
      "updated_at": "2025-02-28T14:30:00"
    }
  },
  "clock": {
    "action": "clock_in",  // or "clock_out"
    "message": "User_1 clocked IN",
    "clocked_in": true,
    "timestamp": "2025-02-28T14:30:00.123456"
  },
  "recognition": {
    "similarity": 0.87,
    "threshold": 0.40,
    "message": "Match found"
  }
}

Response (Unauthorized):
{
  "status": "unauthorized",
  "message": "Face not recognized. Not an authorized employee.",
  "success": false,
  "similarity": 0.32,
  "threshold": 0.40
}
```

**List All Employees:**
```
GET /api/employees

Response:
{
  "status": "ok",
  "employees": ["User_1", "User_2", "User_3"],
  "count": 3,
  "clock_status": {
    "User_1": {
      "clocked_in": true,
      "clock_in_time": "2025-02-28T08:00:00",
      "clock_out_time": null
    }
  }
}
```

**Get Employee Clock Status:**
```
GET /api/employees/{employee_name}/status

Response:
{
  "status": "ok",
  "name": "User_1",
  "clocked_in": true,
  "clock_in_time": "2025-02-28T08:00:00",
  "clock_out_time": null,
  "info": { ... }
}
```

### WebSocket Endpoint

**URL:** `ws://localhost:8000/ws/stream`

**Features:**
- Receives base64 image frames for continuous facial recognition
- Processes frames and returns clock confirmations
- Supports management commands (get_employees, get_status, clear)

## WebSocket Protocol

### Sending Data to Server

**Continuous Face Streaming (automatic from Svelte):**
```
Base64 JPEG image: data:image/jpeg;base64,/9j/4AAQSkZJRg...
```

**Get All Employees:**
```json
{"action": "get_employees"}
```

**Get Clock Status:**
```json
{"action": "get_status"}
```

**Clear Database & Clock Data:**
```json
{"action": "clear"}
```

### Receiving Responses from Server

**Clock Verification Success:**
```json
{
  "type": "clock_success",
  "success": true,
  "employee": {
    "name": "User_1",
    "info": {
      "name": "User_1",
      "id": 1,
      "created_at": "2025-01-15T10:00:00",
      "updated_at": "2025-02-28T14:30:00"
    }
  },
  "clock": {
    "action": "clock_in",
    "message": "User_1 clocked IN",
    "clocked_in": true,
    "timestamp": "2025-02-28T14:30:00.123456",
    "status_data": { ... }
  },
  "similarity": 0.87
}
```

**Face Not Recognized:**
```json
{
  "type": "recognition_failed",
  "message": "Face not recognized",
  "success": false,
  "similarity": 0.35,
  "threshold": 0.40
}
```

**Clock Status Update:**
```json
{
  "type": "status_update",
  "clock_status": {
    "User_1": {
      "clocked_in": true,
      "clock_in_time": "2025-02-28T08:00:00",
      "clock_out_time": null
    },
    "User_2": {
      "clocked_in": false,
      "clock_in_time": "2025-02-28T08:15:00",
      "clock_out_time": "2025-02-28T17:00:00"
    }
  }
}
```

**Employees List:**
```json
{
  "type": "employees_list",
  "employees": ["User_1", "User_2", "User_3"],
  "count": 3
}
```

**Error Response:**
```json
{
  "type": "error",
  "message": "No face detected in frame",
  "success": false
}
```

## Features

✅ Real-time facial recognition with InsightFace (buffalo_l model)  
✅ Automatic clock-in/clock-out status toggling  
✅ Employee verification with 0.40 similarity threshold  
✅ PostgreSQL database integration for employee data  
✅ WebSocket and REST API endpoints  
✅ Employee info retrieval (name, ID, timestamps)  
✅ Clock status tracking with timestamps  
✅ CORS enabled for cross-domain requests  
✅ Graceful error handling and fallback modes  
✅ Real-time Svelte frontend with camera integration  
✅ Docker containerization for easy deployment  

## Configuration

### Database Connection

Edit `facialRecognition/localFaceRec/secureFacialID.py`:

```python
# PostgreSQL Connection
DATABASE_URL = "postgresql://user:password@host:5432/database_name"
```

### Server Settings

Edit `sveltTo.py` to customize:

```python
# CORS Origins - Add your domain
origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://yourdomain.com"
]

# Face Matching Threshold (0.0-1.0, higher = stricter matching)
SIMILARITY_THRESHOLD = 0.40  # From secureFacialID.py

# API Port
# Change port in uvicorn command: --port 8001
```

### Face Recognition Model

The system uses **InsightFace buffalo_l model** which provides:
- 512-dimensional embeddings
- Fast inference (~50-100ms per frame)
- High accuracy for diverse face types
- Pre-trained on large-scale datasets

To use different model, edit `secureFacialID.py`:

```python
FACE_MODEL = 'buffalo_l'  # buffalo_l, buffalo_s, glintr100, etc.
```

## Troubleshooting

### WebSocket Connection Issues

**Error: "WebSocket connection refused"**
- Ensure FastAPI server is running: `uvicorn sveltTo:app --port 8000`
- Check port 8000 is accessible (firewall rules)
- Verify CORS origins in sveltTo.py include your domain
- Browser console shows full error details

**Error: "Failed to decode image"**
- Ensure browser is sending valid base64 JPEG images
- Check FacialRecognitionComponent is capturing frames properly
- Verify WebSocket is in OPEN state before sending

### Face Recognition Issues

**Error: "No face detected in frame"**
- Ensure good lighting on employee's face
- Position face directly toward camera (frontal)
- Check camera resolution is at least 640x480
- Verify face is not covered (mask, sunglasses, etc.)

**Issue: "Face not recognized (unauthorized)"**
- Employee face not registered in database
- Face similarity below 0.40 threshold (too different from registration)
- Test with API endpoint: `GET /api/employees` to see registered users
- Re-register employee if necessary using test_client.py

**Issue: Low face matching accuracy**
- Improve lighting conditions
- Use consistent background
- Ensure consistent face positioning during registration and verification
- Increase captured frames during registration

### Database Errors

**Error: "Could not connect to database"**
- Verify PostgreSQL is running and accessible
- Check DATABASE_URL in secureFacialID.py
- Verify credentials: `psql -h host -U user -d dbname`
- System will run in degraded mode if DB unavailable (uses in-memory only)

**Error: "Table 'users' does not exist"**
- Database schema is auto-created on first connection
- If manual setup needed: see `init_db()` in secureFacialID.py
- Clear and re-initialize: `python -c "from secureFacialID import init_db; init_db()"`

### Performance Issues

**Slow Face Recognition (~2+ seconds per frame)**
- Reduce image resolution in FacialRecognitionComponent.svelte
- Change camera quality: `canvas.width = 480; canvas.height = 360;`
- Enable GPU: Set `GPU_ENABLED=true` in docker-compose or secureFacialID

**High Memory Usage**
- Reduce frame sending frequency: change 500ms to 1000ms in Svelte component
- Limit number of concurrent connections
- Monitor InsightFace model initialization

## Dependencies

For Python backend:
```bash
pip install -r requirements.txt
```

For JavaScript/Svelte:
- Standard Svelte components (no extra deps needed)
- WebSocket API (browser built-in)

## Docker Deployment

### Build Docker Image
```bash
cd /Users/wenaf/Hackathon26/SudoShutdownNow/facialRecognition/processStreamData
docker build -t sudoshutdown-api .
```

### Run with Docker
```bash
docker run -p 8000:8000 sudoshutdown-api
```

### Run with Docker Compose
```bash
cd facialRecognition/processStreamData
docker-compose up -d
```

The API will be available at: `http://localhost:8000`

### Environment Variables
Edit `docker-compose.yml` to configure:
- `DATABASE_URL` - PostgreSQL connection string
- `FACE_MODEL` - Face recognition model (default: buffalo_l)
- `GPU_ENABLED` - Enable GPU acceleration (true/false)
- `SIMILARITY_THRESHOLD` - Face matching threshold (default: 0.40)

## Files

- **Dockerfile** - Container image definition
- **docker-compose.yml** - Docker Compose configuration
- **requirements.txt** - Python dependencies
- **.dockerignore** - Files to exclude from Docker build
