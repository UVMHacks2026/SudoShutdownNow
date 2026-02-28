"""
Standalone test for get_face_embedding with base64 JPG input.
Bypasses the Postgres DB init so we can test locally without a running DB.
"""
import base64
import cv2
import numpy as np

# --- Manually bootstrap only the face app (no DB needed) ---
import secureFacialID as sfid
from unittest.mock import patch, MagicMock

# Patch the DB + load so import doesnt fail on a later re-test
sfid.conn = MagicMock()    # Prevent DB calls from crashing
sfid.authorized_users = {} # Start empty

from insightface.app import FaceAnalysis

print("Loading InsightFace model for test...")
sfid.face_app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
sfid.face_app.prepare(ctx_id=-1, det_size=(640, 640))

# --- Encode the test image as a base64 JPG string ---
image = cv2.imread("../../test_image.png")
_, buffer = cv2.imencode(".jpg", image)
jpg_b64 = base64.b64encode(buffer).decode("utf-8")
b64_string = f"data:image/jpeg;base64,{jpg_b64}"

print("Testing get_face_embedding with base64 JPG string...")
embedding = sfid.get_face_embedding(b64_string)

if embedding is not None:
    print(f"✅ SUCCESS: Embedding extracted, shape={embedding.shape}, dtype={embedding.dtype}")
    print(f"   First 5 values: {embedding[:5]}")
else:
    print("❌ FAILED: No embedding returned (no face found or decode error)")

# Also verify that a plain np.ndarray still works (backwards compat)
print("\nTesting get_face_embedding with raw np.ndarray (backwards compat)...")
embedding2 = sfid.get_face_embedding(image)
if embedding2 is not None:
    print(f"✅ SUCCESS: Embedding extracted from raw frame, shape={embedding2.shape}")
    sim = sfid.compute_similarity(embedding, embedding2)
    print(f"   Cosine similarity between both runs (should be ~1.0): {sim:.4f}")
else:
    print("❌ FAILED: No embedding returned from raw frame")
