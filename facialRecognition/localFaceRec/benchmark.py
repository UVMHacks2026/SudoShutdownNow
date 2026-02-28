import cv2
import numpy as np
from insightface.app import FaceAnalysis
import time
from ultralytics import YOLO

def benchmark():
    print("--- Performance Benchmarking: Secure Facial ID ---")
    
    # 1. Load Models & Measure Loading Time
    start_time = time.time()
    print("\n[1/4] Loading InsightFace ('buffalo_l')...")
    face_app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
    face_app.prepare(ctx_id=0, det_size=(640, 640))
    insightface_load_time = time.time() - start_time
    print(f"✅ InsightFace loaded in {insightface_load_time:.2f} seconds.")

    start_time = time.time()
    print("\n[2/4] Loading YOLOv8n (Body Tracking)...")
    body_model = YOLO("yolov8n.pt")
    yolo_load_time = time.time() - start_time
    print(f"✅ YOLOv8n loaded in {yolo_load_time:.2f} seconds.")

    # 2. Prepare Dummy Data
    print("\n[3/4] Generating simulated webcam frames (640x480)...")
    # Instead of relying on a physical webcam which has hardware FPS limits (e.g., 30 fps),
    # we generate random noise frames to test pure computation speed.
    dummy_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    
    # Warmup runs (JIT compilation, etc.)
    print("Warming up models...")
    for _ in range(3):
        face_app.get(dummy_frame)
        body_model(dummy_frame, verbose=False)

    # 3. Benchmark Inference Loops
    iterations = 50
    print(f"\n[4/4] Running inference benchmark ({iterations} iterations)...")
    
    # Benchmark YOLO
    yolo_times = []
    for _ in range(iterations):
        t0 = time.time()
        body_model(dummy_frame, classes=[0], verbose=False)
        yolo_times.append(time.time() - t0)
        
    avg_yolo = np.mean(yolo_times) * 1000 # convert to ms
    
    # Benchmark InsightFace
    insight_times = []
    for _ in range(iterations):
        t0 = time.time()
        face_app.get(dummy_frame)
        insight_times.append(time.time() - t0)
        
    avg_insight = np.mean(insight_times) * 1000 # convert to ms

    # 4. Print Report
    print("\n" + "="*40)
    print("      PERFORMANCE TEST RESULTS")
    print("="*40)
    print(f"Model Loading Latency:")
    print(f"  - InsightFace:    {insightface_load_time:.2f} s")
    print(f"  - YOLOv8n:        {yolo_load_time:.2f} s")
    print(f"\nInference Latency (Per Frame):")
    print(f"  - YOLOv8n (Body): {avg_yolo:.2f} ms")
    print(f"  - InsightFace:    {avg_insight:.2f} ms")
    
    total_pipeline_ms = avg_yolo + avg_insight
    theoretical_fps = 1000.0 / total_pipeline_ms

    print(f"\nTotal Pipeline Bottleneck: {total_pipeline_ms:.2f} ms per frame")
    print(f"Theoretical Max Throughput: {theoretical_fps:.2f} FPS (without drawing to screen)")
    print("="*40)

if __name__ == "__main__":
    benchmark()
