FROM python:3.11-slim

# System deps for OpenCV + InsightFace + psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libgl1 \
    libgomp1 \
    g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY facialRecognition/ ./facialRecognition/

# Pre-download InsightFace model so it's baked into the image
RUN python -c "from insightface.app import FaceAnalysis; app = FaceAnalysis(name='buffalo_l', allowed_modules=['detection','recognition'], providers=['CPUExecutionProvider']); app.prepare(ctx_id=-1, det_size=(640,640))"

EXPOSE 8000

# Environment variables (set at runtime via Coolify)
ENV DATABASE_URL=""
ENV FERNET_KEY=""
ENV SIMILARITY_THRESHOLD=0.40
ENV FACE_MODEL=buffalo_l
ENV GPU_ENABLED=false

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
