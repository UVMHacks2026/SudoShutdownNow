# Use official Python runtime as base image
FROM python:3.14-slim

# Set working directory in container
WORKDIR /app

# Install system dependencies required for OpenCV, InsightFace, and face recognition
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libglib2.0-0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire application
COPY ../../ .

# Create directory for insightface models (will be downloaded on first run)
RUN mkdir -p /root/.insightface

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Run the FastAPI application
CMD ["uvicorn", "facialRecognition.processStreamData.sveltTo:app", "--host", "0.0.0.0", "--port", "8000"]
